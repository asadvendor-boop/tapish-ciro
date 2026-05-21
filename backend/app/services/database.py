"""
Firestore database — stores signals, crises, resources, actions, traces, stakeholder messages.
Uses Cloud Firestore (firebase-admin SDK) for persistent, serverless, scale-to-zero storage.
Collections: signals, crises, resources, actions, traces, stakeholder_messages

All sync Firestore calls are wrapped in run_in_executor to avoid blocking the async event loop.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime

from app.utils.timezone import now_pkt_iso
from functools import partial
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter


class Database:
    """Non-blocking Firestore wrapper for TAPISH.
    Uses run_in_executor to prevent sync Firestore SDK from blocking the event loop.
    """

    def __init__(self, db_url: str = None):
        self._db = None

    async def _run(self, fn, *args, **kwargs):
        """Run a synchronous Firestore call in a thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    async def init(self):
        """Initialize Firestore client and seed resources."""
        # firebase_admin may already be initialized by FCM setup in main.py
        if not firebase_admin._apps:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
            if cred_path and Path(cred_path).exists():
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                # Default credentials (Cloud Run has these automatically)
                firebase_admin.initialize_app()

        self._db = firestore.client()
        await self._seed_resources()

    async def close(self):
        """No persistent connection to close with Firestore."""
        pass

    # ===================================================================
    # SEED RESOURCES
    # ===================================================================

    def _seed_resources_sync(self):
        """Seed initial resource data if collection is empty (sync)."""
        resources_ref = self._db.collection("resources")
        existing = resources_ref.limit(1).get()
        if len(existing) > 0:
            return
        resources_path = Path(__file__).resolve().parent.parent / "mock" / "resources.json"
        if not resources_path.exists():
            return
        with open(resources_path) as f:
            resources = json.load(f)
        batch = self._db.batch()
        for r in resources:
            doc_ref = resources_ref.document(r["id"])
            batch.set(doc_ref, {
                "id": r["id"],
                "type": r["type"],
                "operator": r["operator"],
                "current_location": r["current_location"],
                "status": r["status"],
                "capacity": r["capacity"],
                "assigned_crisis": r.get("assigned_crisis"),
            })
        batch.commit()

    async def _seed_resources(self):
        await self._run(self._seed_resources_sync)

    # ===================================================================
    # EXECUTE RAW — compatibility shim
    # ===================================================================

    def _execute_raw_sync(self, sql: str, params=None):
        """Compatibility shim for orchestrator's backfill queries (sync)."""
        if "UPDATE traces SET crisis_id" in sql and params and len(params) == 2:
            crisis_id, signal_id = params
            traces_ref = self._db.collection("traces")
            query = traces_ref.where(filter=FieldFilter("signal_id", "==", signal_id)).where(
                filter=FieldFilter("crisis_id", "==", None)
            )
            docs = query.get()
            if docs:
                batch = self._db.batch()
                for doc in docs:
                    batch.update(doc.reference, {"crisis_id": crisis_id})
                batch.commit()

    async def execute_raw(self, sql: str, params=None):
        await self._run(self._execute_raw_sync, sql, params)

    # ===================================================================
    # SIGNALS
    # ===================================================================

    def _insert_signal_sync(self, signal: dict):
        sig_id = signal.get("id", str(uuid.uuid4()))
        doc_ref = self._db.collection("signals").document(sig_id)
        doc_ref.set({
            "id": sig_id,
            "source": signal.get("source", "twitter"),
            "raw_content": signal.get("raw_content", ""),
            "language": signal.get("language", "n/a"),
            "timestamp": signal.get("timestamp", ""),
            "geolocation": signal.get("geolocation"),
            "neighborhood_id": signal.get("neighborhood_id"),
            "geo_confidence": signal.get("geo_confidence", 0),
            "credibility_score": signal.get("credibility_score", 0),
            "credibility_factors": signal.get("credibility_factors", {}),
            "urgency_keywords": signal.get("urgency_keywords", []),
            "urgency_score": signal.get("urgency_score", 0),
            "extracted_intent": signal.get("extracted_intent", {}),
            "processed": 1 if signal.get("processed") else 0,
            "cluster_id": signal.get("cluster_id"),
            "created_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    async def insert_signal(self, signal: dict):
        await self._run(self._insert_signal_sync, signal)

    def _count_signals_sync(self) -> int:
        coll = self._db.collection("signals")
        result = coll.count().get()
        return result[0][0].value if result else 0

    async def count_signals(self) -> int:
        return await self._run(self._count_signals_sync)

    def _get_recent_signals_sync(self, location: str = None, minutes: int = 30) -> list:
        from datetime import timedelta
        from app.utils.timezone import PKT
        cutoff = datetime.now(PKT) - timedelta(minutes=abs(minutes))
        cutoff_str = cutoff.isoformat()

        signals_ref = self._db.collection("signals")
        query = signals_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50)
        docs = query.get()

        results = []
        location_lower = location.lower() if location else None
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("timestamp", "")
            if ts and ts < cutoff_str:
                continue
            if location_lower:
                raw = (d.get("raw_content") or "").lower()
                geo = str(d.get("geolocation") or "").lower()
                if location_lower not in raw and location_lower not in geo:
                    continue
            results.append(d)
            if len(results) >= 20:
                break
        return results

    async def get_recent_signals(self, location: str = None, minutes: int = 30) -> list:
        return await self._run(self._get_recent_signals_sync, location, minutes)

    # ===================================================================
    # CRISES
    # ===================================================================

    def _insert_crisis_sync(self, crisis: dict):
        crisis_id = crisis["id"]
        doc_ref = self._db.collection("crises").document(crisis_id)
        doc_ref.set({
            "id": crisis_id,
            "type": crisis["type"],
            "primary_location": crisis["primary_location"],
            "affected_radius_km": crisis.get("affected_radius_km", 0),
            "affected_population_est": crisis.get("affected_population_est", 0),
            "severity": crisis.get("severity", "low"),
            "confidence": crisis.get("confidence", 0),
            "predicted_peak_time": crisis.get("predicted_peak_time", ""),
            "expected_duration_hrs": crisis.get("expected_duration_hrs", 0),
            "spread_risk": crisis.get("spread_risk", 0),
            "uncertainty_range": crisis.get("uncertainty_range", {}),
            "contributing_signals": crisis.get("contributing_signals", []),
            "cascade_risks": crisis.get("cascade_risks", []),
            "status": crisis.get("status", "detected"),
            "trace_reasoning": crisis.get("trace_reasoning", ""),
            "citizen_uid": crisis.get("citizen_uid"),
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    async def insert_crisis(self, crisis: dict):
        await self._run(self._insert_crisis_sync, crisis)

    def _get_crises_sync(self, status: str = None) -> list:
        crises_ref = self._db.collection("crises")
        if status:
            query = crises_ref.where(filter=FieldFilter("status", "==", status)).order_by(
                "created_at", direction=firestore.Query.DESCENDING
            )
        else:
            query = crises_ref.order_by("created_at", direction=firestore.Query.DESCENDING)
        docs = query.get()
        return [doc.to_dict() for doc in docs]

    async def get_crises(self, status: str = None) -> list:
        return await self._run(self._get_crises_sync, status)

    def _get_crisis_sync(self, crisis_id: str) -> Optional[dict]:
        doc = self._db.collection("crises").document(crisis_id).get()
        return doc.to_dict() if doc.exists else None

    async def get_crisis(self, crisis_id: str) -> Optional[dict]:
        return await self._run(self._get_crisis_sync, crisis_id)

    def _count_crises_sync(self, status: str = None) -> int:
        crises_ref = self._db.collection("crises")
        if status:
            query = crises_ref.where(filter=FieldFilter("status", "==", status))
        else:
            query = crises_ref
        result = query.count().get()
        return result[0][0].value if result else 0

    async def count_crises(self, status: str = None) -> int:
        return await self._run(self._count_crises_sync, status)

    def _update_crisis_status_sync(self, crisis_id: str, status: str):
        self._db.collection("crises").document(crisis_id).update({
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    async def update_crisis_status(self, crisis_id: str, status: str):
        await self._run(self._update_crisis_status_sync, crisis_id, status)

    # ===================================================================
    # RESOURCES
    # ===================================================================

    def _get_resources_sync(self, status: str = None) -> list:
        resources_ref = self._db.collection("resources")
        if status:
            query = resources_ref.where(filter=FieldFilter("status", "==", status))
        else:
            query = resources_ref
        docs = query.get()
        results = []
        for doc in docs:
            d = doc.to_dict()
            if isinstance(d.get("current_location"), dict):
                d["current_location"] = json.dumps(d["current_location"])
            results.append(d)
        return results

    async def get_resources(self, status: str = None) -> list:
        return await self._run(self._get_resources_sync, status)

    def _get_resource_sync(self, resource_id: str) -> dict:
        doc = self._db.collection("resources").document(resource_id).get()
        if doc.exists:
            d = doc.to_dict()
            d["id"] = doc.id
            return d
        return None

    async def get_resource(self, resource_id: str) -> dict:
        return await self._run(self._get_resource_sync, resource_id)

    def _update_resource_sync(self, resource_id: str, update: dict) -> dict:
        doc_ref = self._db.collection("resources").document(resource_id)
        update_data = {}
        for k, v in update.items():
            if k in ("status", "assigned_crisis", "current_location"):
                update_data[k] = v
        if update_data:
            doc_ref.update(update_data)
            # Track status changes in timeline
            if "status" in update_data:
                from datetime import datetime, timezone, timedelta
                pkt = timezone(timedelta(hours=5))
                doc_ref.update({
                    "status_history": firestore.ArrayUnion([{
                        "status": update_data["status"],
                        "timestamp": datetime.now(pkt).isoformat(),
                    }]),
                })
        return {"resource_id": resource_id, "updated": True}

    async def update_resource(self, resource_id: str, update: dict) -> dict:
        return await self._run(self._update_resource_sync, resource_id, update)

    # ===================================================================
    # ACTIONS
    # ===================================================================

    def _insert_action_sync(self, action: dict):
        action_id = action.get("id", str(uuid.uuid4()))
        doc_ref = self._db.collection("actions").document(action_id)
        doc_ref.set({
            "id": action_id,
            "type": action["type"],
            "crisis_id": action.get("crisis_id", ""),
            "target_location": action.get("target_location"),
            "parameters": action.get("parameters", {}),
            "expected_impact": action.get("expected_impact", {}),
            "resource_cost": action.get("resource_cost", {}),
            "side_effects": action.get("side_effects", []),
            "status": action.get("status", "planned"),
            "created_at": firestore.SERVER_TIMESTAMP,
        })

    async def insert_action(self, action: dict):
        await self._run(self._insert_action_sync, action)

    def _get_actions_for_crisis_sync(self, crisis_id: str) -> list:
        query = self._db.collection("actions").where(
            filter=FieldFilter("crisis_id", "==", crisis_id)
        ).order_by("created_at")
        docs = query.get()
        return [doc.to_dict() for doc in docs]

    async def get_actions_for_crisis(self, crisis_id: str) -> list:
        return await self._run(self._get_actions_for_crisis_sync, crisis_id)

    # ===================================================================
    # TRACES
    # ===================================================================

    def _insert_trace_sync(self, trace: dict):
        self._db.collection("traces").add({
            "agent": trace.get("agent"),
            "step": trace.get("step"),
            "phase": trace.get("phase"),
            "crisis_id": trace.get("crisis_id"),
            "signal_id": trace.get("signal_id"),
            "timestamp": trace.get("timestamp", now_pkt_iso()),
            "workplan": trace.get("workplan"),
            "task": trace.get("task"),
            "input_summary": trace.get("input_summary"),
            "reasoning": trace.get("reasoning"),
            "tool_calls": trace.get("tool_calls", []),
            "decision": trace.get("decision"),
            "output_summary": trace.get("output_summary"),
            "error_recovery": trace.get("error_recovery"),
            "adaptation": trace.get("adaptation"),
            "duration_ms": trace.get("duration_ms", 0),
            "model": trace.get("model"),
            "created_at": firestore.SERVER_TIMESTAMP,
        })

    async def insert_trace(self, trace: dict):
        await self._run(self._insert_trace_sync, trace)

    def _get_traces_for_crisis_sync(self, crisis_id: str) -> list:
        query = self._db.collection("traces").where(
            filter=FieldFilter("crisis_id", "==", crisis_id)
        ).order_by("created_at")
        docs = query.get()
        return [doc.to_dict() for doc in docs]

    async def get_traces_for_crisis(self, crisis_id: str) -> list:
        return await self._run(self._get_traces_for_crisis_sync, crisis_id)

    def _get_last_trace_timestamp_sync(self) -> Optional[str]:
        query = self._db.collection("traces").order_by(
            "created_at", direction=firestore.Query.DESCENDING
        ).limit(1)
        docs = query.get()
        if docs:
            d = docs[0].to_dict()
            return d.get("timestamp")
        return None

    async def get_last_trace_timestamp(self) -> Optional[str]:
        return await self._run(self._get_last_trace_timestamp_sync)

    # ===================================================================
    # STAKEHOLDER MESSAGES
    # ===================================================================

    def _insert_stakeholder_message_sync(self, msg: dict):
        msg_id = msg.get("id", str(uuid.uuid4()))
        doc_ref = self._db.collection("stakeholder_messages").document(msg_id)
        doc_ref.set({
            "id": msg_id,
            "audience": msg["audience"],
            "channel": msg["channel"],
            "language": msg["language"],
            "content": msg["content"],
            "urgency": msg.get("urgency", "info"),
            "crisis_id": msg.get("crisis_id", ""),
            "roman_urdu_transliteration": msg.get("roman_urdu_transliteration"),
            "english_translation": msg.get("english_translation"),
            "tts_audio_url": msg.get("tts_audio_url"),
            "created_at": firestore.SERVER_TIMESTAMP,
        })

    async def insert_stakeholder_message(self, msg: dict):
        await self._run(self._insert_stakeholder_message_sync, msg)

    def _get_stakeholder_messages_sync(self, crisis_id: str = None) -> list:
        msgs_ref = self._db.collection("stakeholder_messages")
        if crisis_id:
            query = msgs_ref.where(filter=FieldFilter("crisis_id", "==", crisis_id)).order_by(
                "created_at", direction=firestore.Query.DESCENDING
            )
        else:
            query = msgs_ref.order_by("created_at", direction=firestore.Query.DESCENDING)
        docs = query.get()
        return [doc.to_dict() for doc in docs]

    async def get_stakeholder_messages(self, crisis_id: str = None) -> list:
        return await self._run(self._get_stakeholder_messages_sync, crisis_id)

    # ===================================================================
    # RESET
    # ===================================================================

    def _reset_sync(self):
        for collection_name in ["signals", "crises", "actions", "traces", "stakeholder_messages"]:
            self._delete_collection(collection_name)
        resources = self._db.collection("resources").get()
        if resources:
            batch = self._db.batch()
            for doc in resources:
                batch.update(doc.reference, {"status": "available", "assigned_crisis": None})
            batch.commit()

    async def reset(self):
        """Clear all data for simulation reset."""
        await self._run(self._reset_sync)

    def _delete_collection(self, name: str, batch_size: int = 100):
        """Delete all documents in a collection."""
        coll_ref = self._db.collection(name)
        while True:
            docs = coll_ref.limit(batch_size).get()
            if not docs:
                break
            batch = self._db.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()

    # ===================================================================
    # EXPORT (for trace evidence)
    # ===================================================================

    def _get_all_collection_sync(self, name: str) -> list:
        docs = self._db.collection(name).get()
        results = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            # Convert Firestore timestamps to strings
            for key, val in d.items():
                if hasattr(val, 'isoformat'):
                    d[key] = val.isoformat()
            results.append(d)
        return results

    async def get_all_traces(self) -> list:
        return await self._run(self._get_all_collection_sync, "traces")

    async def get_all_crises(self) -> list:
        return await self._run(self._get_all_collection_sync, "crises")

    async def get_all_signals(self) -> list:
        return await self._run(self._get_all_collection_sync, "signals")

    # ===================================================================
    # CITIZENS (Tapish Awaaz user management)
    # ===================================================================

    def _register_citizen_sync(self, uid: str, email: str, name: str):
        """Register or update a citizen from Tapish Awaaz."""
        doc_ref = self._db.collection("citizens").document(uid)
        doc_ref.set({
            "uid": uid,
            "email": email,
            "name": name,
            "banned": False,
            "registered_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    async def register_citizen(self, uid: str, email: str, name: str):
        await self._run(self._register_citizen_sync, uid, email, name)

    def _is_citizen_banned_sync(self, uid: str) -> bool:
        doc = self._db.collection("citizens").document(uid).get()
        if doc.exists:
            return doc.to_dict().get("banned", False)
        return False

    async def is_citizen_banned(self, uid: str) -> bool:
        return await self._run(self._is_citizen_banned_sync, uid)

    def _set_citizen_banned_sync(self, uid: str, banned: bool):
        self._db.collection("citizens").document(uid).update({
            "banned": banned,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    async def set_citizen_banned(self, uid: str, banned: bool):
        await self._run(self._set_citizen_banned_sync, uid, banned)

    def _get_citizen_sync(self, uid: str) -> Optional[dict]:
        doc = self._db.collection("citizens").document(uid).get()
        if doc.exists:
            d = doc.to_dict()
            for key, val in d.items():
                if hasattr(val, 'isoformat'):
                    d[key] = val.isoformat()
            return d
        return None

    async def get_citizen(self, uid: str) -> Optional[dict]:
        return await self._run(self._get_citizen_sync, uid)

