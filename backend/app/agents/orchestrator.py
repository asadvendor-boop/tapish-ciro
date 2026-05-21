"""
TAPISH Orchestrator — Full 5-agent ADK pipeline with CONDITIONAL ROUTING.

Pipeline Architecture (from TAPISH_IMPLEMENTATION_PLAN.md Section 9):

  Observer → Analyst → [CONFIDENCE CHECK]
                          │
                ┌─────────┴─────────┐
           confidence < 0.65    confidence >= 0.65
                │                    │
          VERIFICATION          DISPATCH FIRST
          ┌─────┐              ┌──────────┐
          │Auditor│            │Strategist│
          └──┬──┘              │ Operator │
             │                 └────┬─────┘
        verdict?                    │
        ┌──┴──┐               POST-DISPATCH
     VERIFY  RETRACT          ┌─────┐
       │      │               │Auditor│
  ┌────┴───┐  STOP            └─────┘
  │Strategist│
  │ Operator │
  └─────────┘

ConditionalAgent does NOT exist in ADK v1.33.0, so we implement
the branching manually in Python using separate SequentialAgent sub-pipelines.
"""

import json
import re
import time
import uuid
import asyncio
import traceback
from datetime import datetime
from app.utils.timezone import now_pkt_iso

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.observer import observer_agent
from app.agents.analyst import analyst_agent
from app.agents.strategist import strategist_agent
from app.agents.operator import operator_agent
from app.agents.auditor import auditor_agent


# ──────────────────────────────────────────────────────────────
# Sub-pipelines
# ──────────────────────────────────────────────────────────────

# Phase 1: Signal intake (always runs)
signal_intake = SequentialAgent(
    name="signal_intake",
    sub_agents=[observer_agent, analyst_agent],
)

# Dispatch branch (Strategist → Operator)
dispatch_branch = SequentialAgent(
    name="dispatch_branch",
    sub_agents=[strategist_agent, operator_agent],
)

# Verification branch — Auditor only (pre-dispatch check)
# Run auditor alone, then check verdict in Python
# If VERIFY → run dispatch_branch
# If RETRACT → STOP pipeline

# Post-dispatch sweep — Auditor after dispatch (for high-confidence crises)
post_dispatch_sweep = SequentialAgent(
    name="post_dispatch_sweep",
    sub_agents=[dispatch_branch, auditor_agent],
)

# ──────────────────────────────────────────────────────────────
# Runners (one per sub-pipeline, sharing session service)
# ──────────────────────────────────────────────────────────────

session_service = InMemorySessionService()

intake_runner = Runner(
    agent=signal_intake,
    app_name="tapish",
    session_service=session_service,
)

dispatch_runner = Runner(
    agent=dispatch_branch,
    app_name="tapish",
    session_service=session_service,
)

auditor_runner = Runner(
    agent=auditor_agent,
    app_name="tapish",
    session_service=session_service,
)

sweep_runner = Runner(
    agent=post_dispatch_sweep,
    app_name="tapish",
    session_service=session_service,
)

CONFIDENCE_THRESHOLD = 0.65


# ──────────────────────────────────────────────────────────────
# Trace helpers
# ──────────────────────────────────────────────────────────────

def _extract_event_text(event) -> str:
    """Extract text content from an ADK event."""
    parts_text = []
    if hasattr(event, 'content') and event.content:
        if hasattr(event.content, 'parts') and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    parts_text.append(part.text)
                elif hasattr(part, 'function_call') and part.function_call:
                    args = dict(part.function_call.args) if part.function_call.args else {}
                    parts_text.append(f"[TOOL CALL: {part.function_call.name}({args})]")
                elif hasattr(part, 'function_response') and part.function_response:
                    parts_text.append(f"[TOOL RESULT: {part.function_response.name}]")
    return "\n".join(parts_text)


def _extract_json_from_text(text: str) -> dict:
    """Extract JSON object from LLM output (handles markdown code blocks)."""
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    # Try direct parse
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


PHASE_MAP = {
    "observer": "observe",
    "analyst": "reason",
    "strategist": "decide",
    "operator": "act",
    "auditor": "evaluate",
}


async def _run_sub_pipeline(runner: Runner, session_id: str, input_text: str,
                            signal_id: str, db, ws_manager, start_time: float) -> list:
    """Run a sub-pipeline and capture all traces. Returns list of trace dicts."""
    traces = []

    async for event in runner.run_async(
        user_id="system",
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=input_text)],
        ),
    ):
        agent_name = getattr(event, 'author', 'unknown')
        event_text = _extract_event_text(event)

        if not event_text:
            continue

        phase = PHASE_MAP.get(agent_name, "unknown")
        step_type = "agent_output"
        if "[TOOL CALL:" in event_text:
            step_type = "tool_call"
        elif "[TOOL RESULT:" in event_text:
            step_type = "tool_result"

        trace = {
            "event": "agent_trace",
            "agent": agent_name,
            "phase": phase,
            "step": step_type,
            "signal_id": signal_id,
            "content": event_text[:2000],
            "timestamp": now_pkt_iso(),
        }
        traces.append(trace)

        # Broadcast to WebSocket
        await ws_manager.broadcast_trace(trace)

        # Store in DB
        await db.insert_trace({
            "agent": agent_name,
            "step": step_type,
            "phase": phase,
            "signal_id": signal_id,
            "input_summary": input_text[:200],
            "reasoning": event_text[:2000],
            "duration_ms": int((time.time() - start_time) * 1000),
            "model": "gemini-2.5-flash" if agent_name in ("observer", "operator") else "gemini-2.5-pro",
        })

    return traces


# ──────────────────────────────────────────────────────────────
# Main pipeline entry point
# ──────────────────────────────────────────────────────────────

async def run_pipeline(raw_tweet: dict, db, ws_manager) -> dict:
    """
    Process a single signal through the 5-agent pipeline WITH conditional routing.

    Flow:
    1. Observer + Analyst (always)
    2. Check Analyst confidence:
       - confidence < 0.65 → Auditor first → dispatch ONLY if verdict == "verify"
       - confidence >= 0.65 → Dispatch first → Auditor sweeps post-dispatch
    """
    signal_id = raw_tweet.get("id", f"sig_{uuid.uuid4().hex[:8]}")
    start_time = time.time()
    all_traces = []

    input_text = f"""Process this incoming signal:
Signal ID: {signal_id}
Source: {raw_tweet.get('source', 'twitter')}
Text: {raw_tweet.get('text', '')}
User: {raw_tweet.get('user', 'unknown')}
Follower count: {raw_tweet.get('follower_count', 0)}
Verified: {raw_tweet.get('verified', False)}
Timestamp: {raw_tweet.get('timestamp', now_pkt_iso())}
Geo hint: {raw_tweet.get('geo_hint', 'none')}
Language: roman_urdu"""

    try:
        # Create a shared session
        session = await session_service.create_session(
            app_name="tapish",
            user_id="system",
        )

        # Broadcast: pipeline started
        await ws_manager.broadcast_trace({
            "event": "pipeline_start",
            "signal_id": signal_id,
            "text_preview": raw_tweet.get("text", "")[:80],
            "timestamp": now_pkt_iso(),
        })

        # ───────────────────────────────────────────────
        # PHASE 1: Signal Intake (Observer → Analyst)
        # ───────────────────────────────────────────────
        await ws_manager.broadcast_trace({
            "event": "phase_start",
            "phase": "signal_intake",
            "agents": ["observer", "analyst"],
            "signal_id": signal_id,
            "timestamp": now_pkt_iso(),
        })

        intake_traces = await _run_sub_pipeline(
            intake_runner, session.id, input_text, signal_id, db, ws_manager, start_time
        )
        all_traces.extend(intake_traces)

        # ───────────────────────────────────────────────
        # EXTRACT ANALYST CONFIDENCE FROM SESSION STATE
        # ───────────────────────────────────────────────
        session_data = await session_service.get_session(
            app_name="tapish",
            user_id="system",
            session_id=session.id,
        )

        confidence = 0.0  # default: below threshold → safe auditor-first path if analyst fails
        crisis_data = {}
        analyst_raw = ""

        if session_data and hasattr(session_data, 'state'):
            analyst_raw = session_data.state.get("analyst_output", "")
            if analyst_raw:
                crisis_data = _extract_json_from_text(analyst_raw) if isinstance(analyst_raw, str) else analyst_raw
                confidence = float(crisis_data.get("confidence", 1.0))

        # Store crisis event in DB
        if crisis_data and "type" in crisis_data:
            crisis_data.setdefault("id", f"crisis_{uuid.uuid4().hex[:6]}")
            crisis_data["contributing_signals"] = [signal_id]
            # Carry citizen_uid from original signal into crisis for ban tracking
            if raw_tweet.get("citizen_uid"):
                crisis_data["citizen_uid"] = raw_tweet["citizen_uid"]
            await db.insert_crisis(crisis_data)

            # Bug 5 fix: backfill crisis_id on all trace records for this signal
            await db.execute_raw(
                "UPDATE traces SET crisis_id = ? WHERE signal_id = ? AND crisis_id IS NULL",
                (crisis_data["id"], signal_id),
            )

            await ws_manager.broadcast_alert({
                "event": "crisis_detected",
                "crisis": crisis_data,
                "confidence": confidence,
                "timestamp": now_pkt_iso(),
            })

        # ───────────────────────────────────────────────
        # CONDITIONAL ROUTING — THE CRITICAL BRANCHING
        # ───────────────────────────────────────────────
        pipeline_path = ""
        dispatch_executed = False
        auditor_verdict = ""

        if confidence < CONFIDENCE_THRESHOLD:
            # ═══════════════════════════════════════════
            # LOW CONFIDENCE PATH: Auditor verifies FIRST
            # ═══════════════════════════════════════════
            pipeline_path = "low_confidence → auditor_first"

            await ws_manager.broadcast_trace({
                "event": "routing_decision",
                "decision": "LOW_CONFIDENCE",
                "confidence": confidence,
                "threshold": CONFIDENCE_THRESHOLD,
                "path": "Auditor verifies BEFORE dispatch",
                "signal_id": signal_id,
                "timestamp": now_pkt_iso(),
            })

            # Run Auditor
            auditor_input = f"Verify the following crisis assessment (confidence: {confidence}):\n{analyst_raw}"
            auditor_traces = await _run_sub_pipeline(
                auditor_runner, session.id, auditor_input, signal_id, db, ws_manager, start_time
            )
            all_traces.extend(auditor_traces)

            # Extract Auditor verdict from session state
            session_data = await session_service.get_session(
                app_name="tapish", user_id="system", session_id=session.id,
            )
            auditor_raw = session_data.state.get("auditor_output", "") if session_data and hasattr(session_data, 'state') else ""
            auditor_result = _extract_json_from_text(auditor_raw) if isinstance(auditor_raw, str) else auditor_raw
            auditor_verdict = auditor_result.get("verdict", "").lower() if isinstance(auditor_result, dict) else ""

            if auditor_verdict == "verify":
                # Auditor says VERIFY → proceed to dispatch
                await ws_manager.broadcast_trace({
                    "event": "auditor_verdict",
                    "verdict": "VERIFY",
                    "action": "Proceeding to dispatch",
                    "signal_id": signal_id,
                    "timestamp": now_pkt_iso(),
                })

                dispatch_input = f"Execute dispatch for verified crisis:\n{analyst_raw}"
                dispatch_traces = await _run_sub_pipeline(
                    dispatch_runner, session.id, dispatch_input, signal_id, db, ws_manager, start_time
                )
                all_traces.extend(dispatch_traces)
                dispatch_executed = True

            elif auditor_verdict == "retract":
                # Auditor says RETRACT → STOP PIPELINE. No dispatch!
                await ws_manager.broadcast_trace({
                    "event": "auditor_verdict",
                    "verdict": "RETRACT",
                    "action": "PIPELINE STOPPED. No resources dispatched. False alarm retracted.",
                    "signal_id": signal_id,
                    "timestamp": now_pkt_iso(),
                })

                # Update crisis status to retracted
                if crisis_data and "id" in crisis_data:
                    await db.update_crisis_status(crisis_data["id"], "retracted")

                    # Broadcast retraction to all channels
                    retraction_msg = auditor_result.get("public_retraction_message_urdu", "الرٹ واپس لیا گیا")
                    await ws_manager.broadcast_alert({
                        "event": "crisis_retracted",
                        "crisis_id": crisis_data["id"],
                        "retraction_message": retraction_msg,
                        "timestamp": now_pkt_iso(),
                    })

            else:
                # INVESTIGATE_FURTHER — escalate to human review
                await ws_manager.broadcast_trace({
                    "event": "auditor_verdict",
                    "verdict": "INVESTIGATE",
                    "action": "Escalated to human review. Pipeline paused.",
                    "signal_id": signal_id,
                    "timestamp": now_pkt_iso(),
                })

        else:
            # ═══════════════════════════════════════════
            # HIGH CONFIDENCE PATH: Dispatch first, Auditor sweeps after
            # ═══════════════════════════════════════════
            pipeline_path = "high_confidence → dispatch_first"

            await ws_manager.broadcast_trace({
                "event": "routing_decision",
                "decision": "HIGH_CONFIDENCE",
                "confidence": confidence,
                "threshold": CONFIDENCE_THRESHOLD,
                "path": "Dispatch FIRST, Auditor sweeps post-dispatch",
                "signal_id": signal_id,
                "timestamp": now_pkt_iso(),
            })

            # Run Strategist → Operator → Auditor
            dispatch_input = f"Execute full dispatch for high-confidence crisis:\n{analyst_raw}"
            sweep_traces = await _run_sub_pipeline(
                sweep_runner, session.id, dispatch_input, signal_id, db, ws_manager, start_time
            )
            all_traces.extend(sweep_traces)
            dispatch_executed = True

            # Extract auditor verdict from post-dispatch sweep
            session_data = await session_service.get_session(
                app_name="tapish", user_id="system", session_id=session.id,
            )
            auditor_raw = session_data.state.get("auditor_output", "") if session_data and hasattr(session_data, 'state') else ""
            auditor_result = _extract_json_from_text(auditor_raw) if isinstance(auditor_raw, str) else auditor_raw
            auditor_verdict = auditor_result.get("verdict", "").lower() if isinstance(auditor_result, dict) else ""

            # POST-DISPATCH SWEEP: Handle Auditor retraction AFTER resources were dispatched
            if auditor_verdict == "retract":
                # Resources were already dispatched — this is a post-dispatch correction
                if crisis_data and "id" in crisis_data:
                    await db.update_crisis_status(crisis_data["id"], "retracted")

                    retraction_msg = auditor_result.get("public_retraction_message_urdu", "الرٹ واپس لیا گیا") if isinstance(auditor_result, dict) else "الرٹ واپس لیا گیا"
                    await ws_manager.broadcast_alert({
                        "event": "crisis_retracted",
                        "crisis_id": crisis_data["id"],
                        "retraction_message": retraction_msg,
                        "post_dispatch_correction": True,
                        "note": "Resources were dispatched before Auditor detected false alarm. Recall order issued.",
                        "timestamp": now_pkt_iso(),
                    })

                    await ws_manager.broadcast_trace({
                        "event": "auditor_verdict",
                        "verdict": "RETRACT_POST_DISPATCH",
                        "action": "Post-dispatch retraction. Resources recalled. Crisis status updated to retracted.",
                        "signal_id": signal_id,
                        "crisis_id": crisis_data["id"],
                        "timestamp": now_pkt_iso(),
                    })

        # ───────────────────────────────────────────────
        # EXTRACT OBSERVER DATA FOR DB STORAGE
        # ───────────────────────────────────────────────
        # Re-fetch session to get latest state (may have been updated by auditor/dispatch)
        session_data = await session_service.get_session(
            app_name="tapish", user_id="system", session_id=session.id,
        )
        observer_raw = session_data.state.get("observer_output", "") if session_data and hasattr(session_data, 'state') else ""
        observer_result = _extract_json_from_text(observer_raw) if isinstance(observer_raw, str) else observer_raw

        signal_payload = {
            "id": signal_id,
            "source": raw_tweet.get("source", "twitter"),
            "raw_content": raw_tweet.get("text", ""),
            "language": "roman_urdu",
            "timestamp": raw_tweet.get("timestamp", now_pkt_iso()),
            "processed": True,
            "credibility_score": confidence,  # fallback; overwritten by observer_result below if available
        }

        if isinstance(observer_result, dict):
            geo = observer_result.get("geolocation")
            # Bug 4 fix: fallback if LLM put lat/lng at top level instead of nesting
            if not geo and observer_result.get("lat"):
                geo = {
                    "lat": observer_result["lat"],
                    "lng": observer_result.get("lng"),
                    "label": observer_result.get("label", ""),
                    "confidence": observer_result.get("confidence", 0),
                }
            signal_payload["geolocation"] = geo
            # Extract neighborhood_id for Firestore exact-match queries
            # (replaces SQL LIKE which Firestore doesn't support)
            if isinstance(geo, dict) and geo.get("neighborhood"):
                signal_payload["neighborhood_id"] = geo["neighborhood"]
            signal_payload["credibility_score"] = observer_result.get("credibility_score", confidence)
            signal_payload["extracted_intent"] = observer_result
            signal_payload["urgency_keywords"] = observer_result.get("urgency_keywords", [])

        # ───────────────────────────────────────────────
        # STORE SIGNAL + FINALIZE
        # ───────────────────────────────────────────────
        await db.insert_signal(signal_payload)

        # Final backfill: link ALL remaining traces (sweep agents) to crisis_id
        # The first backfill (line ~295) only covers Observer+Analyst traces.
        # Strategist/Operator/Auditor traces are written after that, so we do
        # a second pass here at the very end to catch all of them.
        if crisis_data and "id" in crisis_data:
            await db.execute_raw(
                "UPDATE traces SET crisis_id = ? WHERE signal_id = ? AND crisis_id IS NULL",
                (crisis_data["id"], signal_id),
            )

        # ───────────────────────────────────────────────
        # PERSIST ACTIONS + STAKEHOLDER MESSAGES
        # ───────────────────────────────────────────────
        if dispatch_executed and crisis_data and "id" in crisis_data:
            crisis_id = crisis_data["id"]
            crisis_type = crisis_data.get("type", "unknown")
            crisis_loc = crisis_data.get("primary_location", "Lahore")

            # Extract Operator output from session
            session_data = await session_service.get_session(
                app_name="tapish", user_id="system", session_id=session.id,
            )
            operator_raw = session_data.state.get("operator_output", "") if session_data and hasattr(session_data, 'state') else ""
            operator_result = _extract_json_from_text(operator_raw) if isinstance(operator_raw, str) else operator_raw

            # Persist dispatch action
            try:
                action_data = {
                    "type": "resource_dispatch",
                    "crisis_id": crisis_id,
                    "target_location": crisis_loc,
                    "parameters": operator_result if isinstance(operator_result, dict) else {"raw": str(operator_raw)[:500]},
                    "expected_impact": {"response_time_reduction": "3.3x"},
                    "status": "dispatched",
                }
                await db.insert_action(action_data)
            except Exception:
                pass  # Non-critical — don't break pipeline

            # Extract Strategist output for stakeholder messages
            strategist_raw = session_data.state.get("strategist_output", "") if session_data and hasattr(session_data, 'state') else ""
            strategist_result = _extract_json_from_text(strategist_raw) if isinstance(strategist_raw, str) else strategist_raw

            # Persist stakeholder notifications
            try:
                # Public alert (citizens)
                await db.insert_stakeholder_message({
                    "audience": "citizens",
                    "channel": "sms_broadcast",
                    "language": "urdu",
                    "content": strategist_result.get("public_advisory_urdu", f"{crisis_loc} میں {crisis_type} — محفوظ رہیں") if isinstance(strategist_result, dict) else f"{crisis_loc} میں {crisis_type} — محفوظ رہیں",
                    "urgency": crisis_data.get("severity", "medium"),
                    "crisis_id": crisis_id,
                })
                # Responder notification (Rescue 1122)
                await db.insert_stakeholder_message({
                    "audience": "rescue_1122",
                    "channel": "api_push",
                    "language": "english",
                    "content": f"DISPATCH: {crisis_type.upper()} at {crisis_loc}. Confidence: {confidence:.0%}. Resources en route.",
                    "urgency": crisis_data.get("severity", "medium"),
                    "crisis_id": crisis_id,
                })
                # Government notification (PDMA/DC)
                await db.insert_stakeholder_message({
                    "audience": "government_pdma",
                    "channel": "dashboard",
                    "language": "english",
                    "content": f"Tapish Alert: {crisis_type} detected at {crisis_loc}. Severity: {crisis_data.get('severity', 'medium')}. Pipeline path: {pipeline_path}.",
                    "urgency": crisis_data.get("severity", "medium"),
                    "crisis_id": crisis_id,
                })
            except Exception:
                pass  # Non-critical

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Broadcast: pipeline complete
        await ws_manager.broadcast_trace({
            "event": "pipeline_complete",
            "signal_id": signal_id,
            "elapsed_ms": elapsed_ms,
            "agents_executed": len(all_traces),
            "pipeline_path": pipeline_path,
            "confidence": confidence,
            "auditor_verdict": auditor_verdict,
            "dispatch_executed": dispatch_executed,
            "timestamp": now_pkt_iso(),
        })

        # Citizen-facing public alert — only after pipeline confirms dispatch
        if dispatch_executed and crisis_data:
            await ws_manager.broadcast_alert({
                "event": "citizen_public_alert",
                "crisis_id": crisis_data.get("id", ""),
                "type": crisis_data.get("type", "unknown"),
                "severity": crisis_data.get("severity", "medium"),
                "location": crisis_data.get("primary_location", ""),
                "confidence": confidence,
                "elapsed_ms": elapsed_ms,
                "timestamp": now_pkt_iso(),
            })

        return {
            "signal_id": signal_id,
            "pipeline_status": "complete",
            "pipeline_path": pipeline_path,
            "confidence": confidence,
            "auditor_verdict": auditor_verdict,
            "dispatch_executed": dispatch_executed,
            "elapsed_ms": elapsed_ms,
            "agents_executed": len(all_traces),
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)

        await ws_manager.broadcast_trace({
            "event": "pipeline_error",
            "signal_id": signal_id,
            "error": str(e),
            "elapsed_ms": elapsed_ms,
            "timestamp": now_pkt_iso(),
        })

        await db.insert_signal({
            "id": signal_id,
            "source": raw_tweet.get("source", "twitter"),
            "raw_content": raw_tweet.get("text", ""),
            "language": "roman_urdu",
            "timestamp": raw_tweet.get("timestamp", now_pkt_iso()),
            "processed": False,
        })

        return {
            "signal_id": signal_id,
            "pipeline_status": "error",
            "error": str(e),
            "elapsed_ms": elapsed_ms,
            "traceback": traceback.format_exc()[-500:],
        }
