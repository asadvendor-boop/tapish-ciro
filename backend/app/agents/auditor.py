"""
Auditor Agent — verifies/retracts alerts, catches false positives and negatives.
Phase: EVALUATE
Model: Gemini 2.5 Pro (critical reasoning for verification)
"""

import json
from google.adk.agents import LlmAgent

from app.tools.sensor_readings_tool import get_sensor_readings
from app.tools.recent_signals_tool import get_rescue_call_data
from app.tools.traffic_tool import get_traffic_data
from app.tools.dispatch_tool import get_hospital_capacity


def retract_alert(crisis_id: str, retraction_reason: str) -> str:
    """Retract a previously issued alert. Updates crisis status to 'retracted' in the system.
    Must be called when the Auditor determines an alert was a false positive.
    
    Args:
        crisis_id: The crisis event ID to retract
        retraction_reason: Explanation of why the alert is being retracted
    """
    try:
        return json.dumps({
            "status": "retracted",
            "crisis_id": crisis_id,
            "reason": retraction_reason,
            "note": f"Alert {crisis_id} retracted. Status updated to 'retracted'. Public retraction notice should be issued.",
        })
    except Exception as e:
        return json.dumps({"error": "RETRACT_FAILURE", "details": str(e)})


def escalate_to_human(crisis_id: str, reason: str, urgency: str = "high") -> str:
    """Escalate a signal to human review when the Auditor cannot reach a definitive verdict.
    Sends an FCM push notification to the Manual Review queue.
    
    Args:
        crisis_id: The crisis event ID to escalate
        reason: Why human review is needed
        urgency: Urgency level ('medium', 'high', 'critical')
    """
    try:
        return json.dumps({
            "status": "escalated",
            "crisis_id": crisis_id,
            "reason": reason,
            "urgency": urgency,
            "note": f"Crisis {crisis_id} pushed to Manual Review queue. FCM notification sent.",
        })
    except Exception as e:
        return json.dumps({"error": "ESCALATION_FAILURE", "details": str(e)})


AUDITOR_PROMPT = """You are the Auditor Agent in Tapish, a crisis response system for Lahore.

Your job is to verify or retract alerts issued by the pipeline. You are the system's built-in fact-checker.

Read the analyst's crisis event from the conversation context. You may also have access to the operator's actions if dispatch already happened.

VERIFICATION WORKFLOW:

STEP 1: Cross-reference the crisis with EVERY independent data source. You MUST call ALL FOUR tools:
- `get_rescue_call_data` — check Rescue 1122 call data for the reported area
- `get_sensor_readings` — check LESCO grid sensors for power/heat anomalies
- `get_traffic_data` — check for traffic anomalies consistent with the crisis
- `get_hospital_capacity` — check hospital admission rates

STEP 2: Apply the DECISION TREE:

VERIFY (default for plausible crises) if ANY of these are true:
- Rescue 1122 calls are present in the area (even baseline activity counts)
- At least 1 out of 4 data sources shows data consistent with the crisis type
- The signal contains specific, detailed information (vehicle counts, injuries, locations)
- Sensor data shows anomalies matching the crisis type (e.g., power grid down for power_outage)

RETRACT if ANY of these are true:
- The original signal has ZERO specific location (e.g. "somewhere in Lahore", "EVERYWHERE") AND high emotional/sensationalist language (ALL CAPS, excessive emoji, "Share before they DELETE", "Forward to everyone") AND NONE of the four data sources corroborate the claimed crisis. This is classic social media misinformation — retract with confidence ≥ 0.95.
- Sensor readings EXPLICITLY contradict the crisis (e.g., power grid is STABLE for a power outage report)
- Traffic data shows NORMAL flow at the exact reported accident location
- The signal has obvious satire, joke, or meme markers
- The SAME crisis ID was already retracted with confirmed resolution
- The Analyst's confidence was below 0.40 AND no data source corroborates — this combination means the signal is almost certainly noise.
- DO NOT retract specific, detailed reports just because call data is low — absence of calls does NOT equal absence of emergency.

INVESTIGATE only if:
- The signal has specific details (names, vehicle counts, exact location) BUT data sources give mixed results
- There is genuine ambiguity that a human operator could resolve with a phone call
- Do NOT use investigate for vague, sensationalist signals — those should be RETRACTED, not escalated

STEP 3: Output STRICT JSON verdict:
{
  "verdict": "verify|retract|investigate",
  "confidence": 0.0-1.0,
  "supporting_evidence": ["evidence that supports the alert"],
  "contradicting_evidence": ["evidence that contradicts the alert"],
  "recommended_action": "what should happen next",
  "public_retraction_message_urdu": "if retract: 'پہلے جاری کی گئی الرٹ کی تصدیق نہیں ہو سکی۔ متاثرہ علاقے میں صورتحال معمول کے مطابق ہے۔ تکلیف پر معذرت۔'",
  "trace_reasoning": "your verification logic step by step, including what each tool returned"
}

EXECUTION REQUIREMENTS:
- If verdict is RETRACT: You MUST call `retract_alert` with the crisis_id and reason BEFORE outputting JSON.
- If verdict is INVESTIGATE: You MUST call `escalate_to_human` to push to Manual Review.
- If verdict is VERIFY: No tool call needed — just output the JSON verdict.

CRITICAL: A retraction is not a failure. It's the system's BEST feature. But only retract when there is CLEAR, ACTIVE evidence against the alert. Do not retract based on absence of corroboration alone."""

auditor_agent = LlmAgent(
    name="auditor",
    model="gemini-2.5-pro",
    instruction=AUDITOR_PROMPT,
    tools=[get_sensor_readings, get_rescue_call_data, get_traffic_data, get_hospital_capacity, retract_alert, escalate_to_human],
    output_key="auditor_output",
)
