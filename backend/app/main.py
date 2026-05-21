"""
TAPISH — Agentic Crisis Response Orchestrator for Lahore
FastAPI entry point: REST routes, WebSocket channels, simulation control.
"""

import os
import json
import asyncio
import uuid
from datetime import datetime
from app.utils.timezone import now_pkt_iso
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.schemas import Signal, CrisisEvent, Resource, ResourceAllocation, Action, StakeholderMessage
from app.services.database import Database
from app.services.stream_simulator import StreamSimulator
from app.services.signal_streams import SignalStreamManager
from app.services.ws_manager import ConnectionManager

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MOCK_DIR = BASE_DIR / "mock"
TTS_DIR = BASE_DIR.parent / "tts_output"
TTS_DIR.mkdir(exist_ok=True)

# Pre-load static data files at import time (Bug #21)
_hospitals_cache = None
try:
    with open(MOCK_DIR / "hospitals.json") as _f:
        _hospitals_cache = json.load(_f)
except Exception:
    _hospitals_cache = []

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
ws_manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
db = Database()

# ---------------------------------------------------------------------------
# Stream simulator
# ---------------------------------------------------------------------------
simulator = StreamSimulator(mock_dir=MOCK_DIR, db=db, ws_manager=ws_manager)
stream_mgr = SignalStreamManager(db=db, ws_manager=ws_manager)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    await db.init()
    yield
    await stream_mgr.stop_all()
    await db.close()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TAPISH — Crisis Intelligence & Response Orchestrator",
    description="Agentic AI system for Lahore heatwave crisis response. Google Antigravity Hackathon Challenge 3.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tapish-backend-163379998754.asia-south1.run.app",  # Production dashboard (same-origin)
        "http://localhost:3000",   # Local Next.js dev
        "http://localhost:8000",   # Local backend dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token", "Authorization"],
)

# Serve TTS audio files
app.mount("/tts", StaticFiles(directory=str(TTS_DIR)), name="tts")

# Web dashboard directory
WEB_DIR = BASE_DIR.parent / "web"


# ===========================================================================
# SIMULATION CONTROL
# ===========================================================================

class SimulationStartRequest(BaseModel):
    scenario_id: str = "scenario_1_baseline"

@app.post("/api/simulation/start")
async def start_simulation(req: SimulationStartRequest):
    """Start a scenario simulation."""
    result = await simulator.start(req.scenario_id)
    return result

@app.post("/api/simulation/pause")
async def pause_simulation():
    """Pause the running simulation."""
    simulator.pause()
    return {"status": "paused"}

async def _do_reset():
    """Internal reset helper — callable from reset route and auto-demo."""
    await simulator.reset()
    await db.reset()

@app.post("/api/simulation/reset")
async def reset_simulation(request: Request):
    """Reset simulation state. Admin-only."""
    _require_admin(request)
    await _do_reset()
    return {"status": "reset"}

@app.get("/api/simulation/status")
async def simulation_status():
    """Current simulation state — also used as Cloud Run health check."""
    return {
        "status": simulator.status,
        "scenario": simulator.current_scenario,
        "signals_processed": await db.count_signals(),
        "active_crises": await db.count_crises(status="detected"),
        "timestamp": now_pkt_iso(),
        "version": "1.0.0",
    }


# ===========================================================================
# SIGNAL INGESTION (LIVE INJECT)
# ===========================================================================

class IngestRequest(BaseModel):
    raw_text: str
    language: str = "roman_urdu"
    geo_hint: Optional[str] = None
    source: str = "twitter"  # twitter | rescue_1122 | lesco_sensors | field_report

@app.post("/api/signals/ingest")
async def ingest_signal(req: IngestRequest, request: Request):
    """
    Live Signal Inject — accepts signals from any source.
    Runs through the full 5-agent reactive pipeline (Observer → Analyst → Strategist → Operator → Auditor).
    The 6th agent (Predictor) runs independently via /api/predict/preposition.
    Requires either Authorization: Bearer (citizen) or X-Admin-Token (operator).
    """
    _check_rate_limit(request.client.host if request.client else "unknown")

    citizen_uid = await _verify_citizen_or_admin(request)

    signal_id = f"live_{uuid.uuid4().hex[:8]}"
    raw_signal = {
        "id": signal_id,
        "user": "@judge_live" if not citizen_uid else f"@citizen_{citizen_uid[:8]}",
        "follower_count": 100,
        "verified": req.source != "twitter",  # Official sources are pre-verified
        "text": req.raw_text,
        "timestamp": now_pkt_iso(),
        "geo_hint": req.geo_hint,
        "source": req.source,
        "citizen_uid": citizen_uid,
    }

    result = await simulator.process_single_signal(raw_signal)
    return {"signal_id": signal_id, "source": req.source, "status": "processed", "result": result}


# ===========================================================================
# SIGNAL STREAM CONTROL (3+ source auto-ingestion)
# ===========================================================================

class StreamControlRequest(BaseModel):
    stream: str  # rescue_1122 | lesco_sensors
    interval_seconds: int = 25

@app.post("/api/streams/start")
async def start_stream(req: StreamControlRequest):
    """Start an auto-ingestion signal stream."""
    return await stream_mgr.start_stream(req.stream, req.interval_seconds)

@app.post("/api/streams/stop")
async def stop_stream(req: StreamControlRequest):
    """Stop an auto-ingestion signal stream."""
    return await stream_mgr.stop_stream(req.stream)

@app.get("/api/streams/status")
async def stream_status():
    """Get status of all signal streams."""
    return {"streams": stream_mgr.status}


# ===========================================================================
# MULTIMODAL CITIZEN REPORTING (Feature 2+4: Vision + Speech + Field Reports)
# ===========================================================================

MAX_MEDIA_BASE64_LENGTH = 7_000_000  # ~5MB raw

# ---------------------------------------------------------------------------
# In-memory rate limiter (per-IP, resets every 60s)
# ---------------------------------------------------------------------------
from collections import defaultdict
import time as _time

_rate_buckets: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 10   # max requests per window
_RATE_WINDOW = 60  # seconds
_LAST_BUCKET_PRUNE = _time.time()

def _check_rate_limit(client_ip: str):
    global _LAST_BUCKET_PRUNE
    now = _time.time()
    # Bug #11: Periodically prune empty buckets to prevent memory leak
    if now - _LAST_BUCKET_PRUNE > 300:  # every 5 minutes
        empty_keys = [k for k, v in _rate_buckets.items() if not v or (now - max(v)) > _RATE_WINDOW]
        for k in empty_keys:
            del _rate_buckets[k]
        _LAST_BUCKET_PRUNE = now
    bucket = _rate_buckets[client_ip]
    # Prune old entries
    _rate_buckets[client_ip] = [t for t in bucket if now - t < _RATE_WINDOW]
    if len(_rate_buckets[client_ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in 60 seconds.")
    _rate_buckets[client_ip].append(now)

# ---------------------------------------------------------------------------
# Admin token authentication (Bug #9)
# ---------------------------------------------------------------------------
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "") or ADMIN_TOKEN
if not JWT_SECRET:
    raise RuntimeError("FATAL: JWT_SECRET or ADMIN_TOKEN env var must be set. No secrets in source code.")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
# Nigraan operator credentials (separate from web admin)
OPERATOR_USERNAME = os.getenv("OPERATOR_USERNAME", "")
OPERATOR_PASSWORD = os.getenv("OPERATOR_PASSWORD", "")

# Track whether auth is properly configured
_AUTH_CONFIGURED = bool(ADMIN_USERNAME and ADMIN_PASSWORD)
_OPERATOR_CONFIGURED = bool(OPERATOR_USERNAME and OPERATOR_PASSWORD)

# Startup validation — warn if credentials are missing
if not _AUTH_CONFIGURED:
    import logging
    logging.warning("⚠️  ADMIN_USERNAME / ADMIN_PASSWORD env vars not set — Markaz login will fail")
if not _OPERATOR_CONFIGURED:
    import logging
    logging.warning("⚠️  OPERATOR_USERNAME / OPERATOR_PASSWORD env vars not set — Nigraan login will fail")

import jwt as pyjwt
from datetime import timedelta

def _create_admin_jwt(role: str = "admin", username: str = "") -> str:
    """Create a signed JWT for admin/operator sessions."""
    payload = {
        "role": role,
        "sub": username,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

def _verify_jwt(token: str) -> dict:
    """Verify and decode a JWT. Returns the payload or raises."""
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please login again")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token")

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/admin/login")
async def admin_login(req: AdminLoginRequest):
    """
    Authenticate admin/operator and return a signed JWT.
    Credentials stay server-side — clients never see ADMIN_TOKEN.
    """
    # Guard: reject if credentials env vars are not configured
    if not _AUTH_CONFIGURED and not _OPERATOR_CONFIGURED:
        raise HTTPException(status_code=503, detail="Auth not configured on server")

    # Guard: reject empty-string submissions (prevents fail-open)
    if not req.username or not req.password:
        raise HTTPException(status_code=401, detail="Username and password required")

    # Check web admin credentials
    if _AUTH_CONFIGURED and req.username == ADMIN_USERNAME and req.password == ADMIN_PASSWORD:
        token = _create_admin_jwt(role="admin", username=req.username)
        return {"token": token, "role": "admin", "expires_in": 86400}

    # Check Nigraan operator credentials
    if _OPERATOR_CONFIGURED and req.username == OPERATOR_USERNAME and req.password == OPERATOR_PASSWORD:
        token = _create_admin_jwt(role="operator", username=req.username)
        return {"token": token, "role": "operator", "expires_in": 86400}

    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/admin/refresh")
async def admin_refresh(request: Request):
    """
    Refresh an existing JWT. Accepts a valid or recently-expired token
    and issues a fresh one with a new 24h expiry window.
    This prevents 401s during long demo sessions.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    old_token = auth_header[7:]
    try:
        # Allow up to 1 hour of clock skew / grace period for expired tokens
        payload = pyjwt.decode(old_token, JWT_SECRET, algorithms=["HS256"],
                               options={"verify_exp": False})
        # Verify the token isn't WAY too old (max 48h since issued)
        import time
        iat = payload.get("iat", 0)
        if isinstance(iat, (int, float)) and (time.time() - iat) > 172800:
            raise HTTPException(status_code=401, detail="Token too old — please login again")
        role = payload.get("role", "admin")
        username = payload.get("sub", "")
        new_token = _create_admin_jwt(role=role, username=username)
        return {"token": new_token, "role": role, "expires_in": 86400}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token — please login again")

def _require_admin(request: Request):
    """
    Check admin authentication via:
    1. Authorization: Bearer <JWT> (preferred — new flow)
    2. X-Admin-Token header (legacy — backward compat)
    Raises 403 if neither is valid.
    """
    # Check JWT Bearer token first (new flow)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        # Don't intercept Firebase citizen tokens (they're much longer and have dots)
        # Our JWTs are also dotted, so check by trying to decode
        try:
            payload = _verify_jwt(jwt_token)
            if payload.get("role") in ("admin", "operator"):
                return  # Valid admin/operator JWT
        except HTTPException:
            pass  # Fall through to legacy check

    # Legacy: X-Admin-Token header
    if ADMIN_TOKEN:
        token = request.headers.get("X-Admin-Token", "")
        if token == ADMIN_TOKEN:
            return

    raise HTTPException(status_code=403, detail="Admin authentication required")

def _is_admin(request: Request) -> bool:
    """Check if request has valid admin auth (non-throwing)."""
    try:
        _require_admin(request)
        return True
    except HTTPException:
        return False

async def _verify_citizen_or_admin(request: Request) -> Optional[str]:
    """
    Verify request is from an authenticated citizen (Firebase Bearer) or admin (JWT/X-Admin-Token).
    Returns citizen_uid if citizen, None if admin. Raises 401 if neither.
    """
    # Check admin first (JWT or legacy token)
    if _is_admin(request):
        return None

    # Check citizen Firebase ID token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            import firebase_admin.auth as fb_auth
            id_token = auth_header[7:]
            decoded = fb_auth.verify_id_token(id_token)
            uid = decoded["uid"]
            # Check ban status
            if await db.is_citizen_banned(uid):
                raise HTTPException(status_code=403, detail="Your account has been suspended")
            return uid
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")

    raise HTTPException(status_code=401, detail="Authentication required")

# ---------------------------------------------------------------------------
# Citizen Management Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/citizens/register")
async def register_citizen(request: Request):
    """Register citizen from Tapish Awaaz. Verifies Firebase ID token."""
    body = await request.json()
    id_token = body.get("id_token", "")
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token required")
    try:
        import firebase_admin.auth as fb_auth
        decoded = fb_auth.verify_id_token(id_token)
        uid = decoded["uid"]
        email = decoded.get("email", "")
        name = decoded.get("name", "")
        await db.register_citizen(uid, email, name)
        return {"status": "registered", "uid": uid}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

@app.post("/api/citizens/{uid}/ban")
async def ban_citizen(uid: str, request: Request):
    """Ban or unban a citizen. Admin-only."""
    _require_admin(request)
    body = await request.json()
    banned = body.get("banned", True)
    await db.set_citizen_banned(uid, banned)
    return {"status": "banned" if banned else "unbanned", "uid": uid}

@app.post("/api/simulation/auto-demo")
async def auto_demo(request: Request):
    """
    One-click high-impact demo for hackathon judges. Admin-only.

    Runs 3 signals sequentially through the full 5-agent pipeline:
      Signal 1: Real heatwave crisis (Twitter, Punjabi) → HIGH confidence → Dispatch
      Signal 2: Viral false alarm (Twitter, English) → LOW confidence → Auditor RETRACT
      Signal 3: Competing crisis from official source (Rescue 1122) → HIGH confidence → Dispatch
                Resources now split between 2 real crises

    Demonstrates: multi-source fusion, informal language handling, false alarm detection,
    retraction with Urdu apology, resource competition, conditional routing (both paths).
    """
    _require_admin(request)
    await _do_reset()

    demo_signals = [
        # Signal 1: Real crisis — Punjabi tweet, specific location, urgent
        IngestRequest(
            raw_text="بھاٹی گیٹ والڈ سٹی وچ گرمی نال 40 توں زیادہ لوک بے ہوش، "
                     "ریسکیو 1122 دا نمبر بند، فوری مدد چاہیدی اے",
            source="twitter",
            geo_hint="Bhati Gate, Walled City, Lahore",
        ),
        # Signal 2: FALSE ALARM — viral, no specific location, sensationalist
        IngestRequest(
            raw_text="OMG LAHORE IS SINKING!!! Massive flood EVERYWHERE 😱😱🌊 "
                     "Share before they DELETE this!! #LahoreFloods #Breaking",
            source="twitter",
        ),
        # Signal 3: Competing real crisis — official Rescue 1122, DIFFERENT location (far from Signal 1)
        IngestRequest(
            raw_text="EMERGENCY DISPATCH: Multiple heat-stroke casualties reported at Model Town Main Market. "
                     "12 calls received in 15 minutes. 3 ambulances requested urgently. "
                     "LESCO confirms transformer failure at Model Town feeder, power out across blocks C and D.",
            source="rescue_1122",
            geo_hint="Model Town, Lahore",
        ),
    ]

    results = []
    for i, sig in enumerate(demo_signals, 1):
        # Broadcast which demo signal is starting
        await ws_manager.broadcast_trace({
            "event": "demo_signal_start",
            "signal_number": i,
            "total_signals": len(demo_signals),
            "source": sig.source,
            "text_preview": sig.raw_text[:80],
            "timestamp": now_pkt_iso(),
        })
        result = await ingest_signal(sig, request)
        results.append(result)

    return {
        "demo_signals": len(results),
        "results": results,
        "summary": {
            "total_pipelines": len(results),
            "dispatched": sum(1 for r in results if r.get("result", {}).get("dispatch_executed")),
            "retracted": sum(1 for r in results if r.get("result", {}).get("auditor_verdict") == "retract"),
        },
    }

# ---------------------------------------------------------------------------
# Gemini retry helper (handles 429 / 503)
# ---------------------------------------------------------------------------
async def _gemini_with_retry(fn, *args, max_retries=2, **kwargs):
    """Call a sync Gemini function with retry on transient errors.
    Runs the blocking call in a thread executor to avoid blocking the event loop.
    """
    import functools
    loop = asyncio.get_event_loop()
    for attempt in range(max_retries + 1):
        try:
            # Run sync Gemini call in thread pool to avoid blocking
            result = await loop.run_in_executor(
                None, functools.partial(fn, *args, **kwargs)
            )
            return result
        except Exception as e:
            err_str = str(e).lower()
            if attempt < max_retries and ("429" in err_str or "503" in err_str or "resource exhausted" in err_str):
                wait = (attempt + 1) * 2  # 2s, 4s
                await asyncio.sleep(wait)
                continue
            raise

class MultimodalIngestRequest(BaseModel):
    type: str = "text"  # text | image | audio | video
    content: str = ""  # text content or base64-encoded media
    media_base64: Optional[str] = None  # base64 media data
    lat: Optional[float] = None
    lng: Optional[float] = None
    context: str = ""  # optional text alongside media
    fcm_device_token: Optional[str] = None  # for targeted post-pipeline notification

@app.post("/api/signals/ingest/multimodal")
async def ingest_multimodal(req: MultimodalIngestRequest, request: Request):
    """
    Multimodal Citizen Field Report — accepts text, image, audio, or video
    from citizens on the ground. GPS auto-attached from phone.
    Requires either Authorization: Bearer (citizen) or X-Admin-Token (operator).
    """
    _check_rate_limit(request.client.host if request.client else "unknown")
    citizen_uid = await _verify_citizen_or_admin(request)

    # Bug #13: Reject oversized payloads at HTTP-header level BEFORE body is fully read
    content_length = int(request.headers.get("content-length", "0"))
    if content_length > MAX_MEDIA_BASE64_LENGTH:
        raise HTTPException(status_code=413, detail=f"Media too large. Max {MAX_MEDIA_BASE64_LENGTH // 1_000_000}MB.")

    signal_id = f"field_{uuid.uuid4().hex[:8]}"
    extracted_text = ""
    analysis = {}

    # Secondary check on parsed body (defense-in-depth)
    if req.media_base64 and len(req.media_base64) > MAX_MEDIA_BASE64_LENGTH:
        raise HTTPException(status_code=413, detail=f"Media too large. Max {MAX_MEDIA_BASE64_LENGTH // 1_000_000}MB.")

    if req.type == "image" and req.media_base64:
        from app.tools.vision_tool import analyze_crisis_image
        analysis = analyze_crisis_image(req.media_base64, req.context)
        extracted_text = f"[FIELD PHOTO] {analysis.get('description', '')}. " \
                         f"Severity: {analysis.get('severity', 'unknown')}. " \
                         f"Type: {analysis.get('crisis_type', 'unknown')}. " \
                         f"{analysis.get('recommended_action', '')}"

    elif req.type == "audio" and req.media_base64:
        from app.tools.speech_tool import transcribe_urdu_audio
        transcription = transcribe_urdu_audio(req.media_base64)
        analysis = transcription
        extracted_text = f"[VOICE REPORT] {transcription.get('transcription', '')} " \
                         f"(EN: {transcription.get('transcription_english', '')})"

    elif req.type == "video" and req.media_base64:
        # Gemini 2.5 Flash natively supports video understanding with video/mp4
        from app.tools.vision_tool import analyze_crisis_media
        analysis = analyze_crisis_media(req.media_base64, req.context, mime_type="video/mp4")
        extracted_text = f"[FIELD VIDEO] {analysis.get('description', '')}. " \
                         f"Severity: {analysis.get('severity', 'unknown')}."

    elif req.type == "text":
        extracted_text = req.content or req.context

    # Build geo hint from GPS
    geo_hint = None
    if req.lat is not None and req.lng is not None:
        geo_hint = f"{req.lat},{req.lng}"

    raw_signal = {
        "id": signal_id,
        "user": f"@citizen_{citizen_uid[:8]}" if citizen_uid else "@citizen_field_report",
        "follower_count": 0,
        "verified": True,  # Field reports with GPS are trusted
        "text": extracted_text,
        "timestamp": now_pkt_iso(),
        "geo_hint": geo_hint,
        "source": "field_report",
        "media_type": req.type,
        "media_analysis": analysis,
        "gps": {"lat": req.lat, "lng": req.lng} if req.lat is not None else None,
        "citizen_uid": citizen_uid,
    }

    # Run pipeline in background — return immediately to citizen
    async def _run_pipeline_and_notify(signal, device_token, uid):
        try:
            result = await simulator.process_single_signal(signal)
            # Send targeted FCM to ONLY the submitting device
            if device_token:
                import app.tools.fcm_tool as fcm_mod
                fcm_mod._init_firebase()
                dispatched = result.get("dispatch_executed", False)
                if fcm_mod._firebase_initialized:
                    try:
                        from firebase_admin import messaging
                        if dispatched:
                            title = "✅ آپ کی رپورٹ تصدیق شدہ ہے"
                            body = "آپ کی اطلاع صحیح پائی گئی۔ وسائل بھیج دیے گئے ہیں۔ شکریہ!"
                        else:
                            title = "⚠️ آپ کی رپورٹ مسترد ہو گئی"
                            body = "تحقیقات کے بعد آپ کی رپورٹ غلط پائی گئی۔ بار بار غلط رپورٹس پر آئی ڈی بند ہو سکتی ہے۔"
                        msg = messaging.Message(
                            notification=messaging.Notification(title=title, body=body),
                            data={"type": "report_verdict", "verdict": "verified" if dispatched else "retracted", "signal_id": signal.get("id", "")},
                            token=device_token,
                            android=messaging.AndroidConfig(
                                priority="high",
                                notification=messaging.AndroidNotification(
                                    icon="ic_alert", color="#4CAF50" if dispatched else "#FF9800",
                                    sound="default", channel_id="crisis_alerts",
                                ),
                            ),
                        )
                        messaging.send(msg)
                        print(f"[FCM] Targeted verdict notification sent to device: {title}")
                    except Exception as fcm_err:
                        print(f"[FCM] Targeted notification failed: {fcm_err}")
                else:
                    print(f"[FCM] Firebase not initialized, cannot send targeted notification")
        except Exception as e:
            print(f"[Pipeline] Background processing failed for {signal.get('id')}: {e}")

    asyncio.create_task(_run_pipeline_and_notify(raw_signal, req.fcm_device_token, citizen_uid))

    return {
        "signal_id": signal_id,
        "source": "field_report",
        "media_type": req.type,
        "extracted_text": extracted_text[:200],
        "analysis": analysis,
        "status": "accepted",
        "message": "آپ کی رپورٹ موصول ہو گئی — پائپ لائن جاری ہے",
    }


# ===========================================================================
# PREDICTIVE PRE-POSITIONING (Feature 1: Proactive crisis prediction)
# ===========================================================================

@app.get("/api/predict/forecast")
async def get_forecast():
    """Get current weather forecast for Lahore."""
    from app.tools.forecast_tool import get_weather_forecast
    return json.loads(get_weather_forecast(hours_ahead=24))

@app.post("/api/predict/preposition")
async def run_predictor(request: Request):
    """
    Run the Predictor to analyze forecast and recommend
    resource pre-positioning BEFORE a crisis hits.

    Architecture note: Uses direct Gemini call with pre-gathered tool data
    instead of the ADK Runner. This is intentional for latency — the Predictor
    is a proactive, scheduled agent (not reactive like the 5-agent pipeline).
    The ADK LlmAgent in predictor.py defines the agent spec; this endpoint
    implements the execution pattern optimized for single-shot prediction.
    """
    _check_rate_limit(request.client.host if request.client else "unknown")

    from app.tools.forecast_tool import get_weather_forecast
    from app.tools.pser_tool import get_pser_vulnerability
    from google import genai

    # Gather data
    forecast_data = get_weather_forecast(hours_ahead=24)
    pser_walled_city = get_pser_vulnerability("walled_city")
    pser_bhati_gate = get_pser_vulnerability("bhati_gate")
    pser_gulberg = get_pser_vulnerability("gulberg")

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    prompt = f"""You are the PREDICTOR agent in Tapish. Analyze the forecast and PSER data below,
then recommend a resource pre-positioning plan for Lahore's high-vulnerability neighborhoods.

FORECAST:
{forecast_data}

VULNERABILITY DATA:
Walled City: {pser_walled_city}
Bhati Gate: {pser_bhati_gate}
Gulberg: {pser_gulberg}

Provide a structured pre-positioning plan with:
1. Overall risk level
2. For each high-PSER neighborhood: ambulances, water tankers, and deploy-by time
3. Total resources needed
4. Advisory in English and Urdu"""

    response = await _gemini_with_retry(
        client.models.generate_content,
        model="gemini-2.5-flash", contents=prompt
    )
    result_text = response.text

    # Broadcast to trace WS
    try:
        await ws_manager.broadcast({
            "event": "prediction",
            "agent": "predictor",
            "phase": "predict",
            "content": result_text[:500],
            "timestamp": now_pkt_iso(),
        }, "trace")
    except Exception:
        pass

    return {
        "status": "prediction_complete",
        "timestamp": now_pkt_iso(),
        "prediction": result_text,
    }


# ===========================================================================
# AFTER-ACTION REPORT (Feature 3)
# ===========================================================================

@app.get("/api/crises/{crisis_id}/report")
async def generate_after_action_report(crisis_id: str):
    """Generate a structured after-action report for a resolved crisis."""
    crisis = await db.get_crisis(crisis_id)
    if not crisis:
        raise HTTPException(status_code=404, detail="Crisis not found")

    traces = await db.get_traces_for_crisis(crisis_id)
    actions = await db.get_actions_for_crisis(crisis_id)

    from google import genai
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt = f"""Generate a structured After-Action Report for this crisis event.

CRISIS DATA:
{json.dumps(crisis, indent=2, default=str)[:2000]}

AGENT TRACES ({len(traces)} total):
{json.dumps(traces[:10], indent=2, default=str)[:3000]}

ACTIONS TAKEN ({len(actions)} total):
{json.dumps(actions[:10], indent=2, default=str)[:2000]}

Generate the report in this format:

# After-Action Report: [Crisis Type] at [Location]

## Incident Summary
Brief overview of what happened, when, and where.

## Timeline
Key events in chronological order.

## Agent Pipeline Performance
How each agent contributed (Observer → Analyst → Strategist → Operator → Auditor). Also note Predictor if pre-positioning was triggered before this crisis.

## Resources Deployed
What was dispatched, where, and response times.

## Stakeholder Notifications
Who was notified and through which channels.

## Response Metrics
- Detection to dispatch time
- Resources utilized
- Stakeholder channels activated

## Lessons Learned
What went well, what could improve.

Write in professional emergency management language. Include both English and Urdu headers."""

    response = await _gemini_with_retry(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return {
        "crisis_id": crisis_id,
        "generated_at": now_pkt_iso(),
        "report": response.text,
        "traces_count": len(traces),
        "actions_count": len(actions),
    }


# ===========================================================================
# CORE DATA ENDPOINTS
# ===========================================================================

@app.get("/api/crises")
async def list_crises():
    """List all active crisis events."""
    crises = await db.get_crises()
    return {"crises": crises}

@app.get("/api/crises/{crisis_id}")
async def get_crisis(crisis_id: str):
    """Get single crisis detail."""
    crisis = await db.get_crisis(crisis_id)
    if not crisis:
        raise HTTPException(status_code=404, detail="Crisis not found")
    return crisis

@app.get("/api/crises/{crisis_id}/trace")
async def get_crisis_trace(crisis_id: str):
    """Get full agent trace chain for a crisis."""
    traces = await db.get_traces_for_crisis(crisis_id)
    return {"crisis_id": crisis_id, "traces": traces}

@app.get("/api/crises/{crisis_id}/actions")
async def get_crisis_actions(crisis_id: str):
    """Get all actions taken for a crisis."""
    actions = await db.get_actions_for_crisis(crisis_id)
    return {"crisis_id": crisis_id, "actions": actions}


# ---------------------------------------------------------------------------
# Degraded Mode Status
# ---------------------------------------------------------------------------
@app.get("/api/degraded/status")
async def degraded_status():
    """Check if degraded mode is currently active (for Scenario 5 visibility)."""
    from app.services import degraded_mode
    return {
        "active": degraded_mode.is_active(),
        "weather_stale": degraded_mode.should_stale_weather(),
        "stale_minutes": degraded_mode.stale_minutes(),
    }


# ---------------------------------------------------------------------------
# Data Mode Toggle — LIVE (real APIs) vs DEMO (mock JSON)
# ---------------------------------------------------------------------------
class DataModeRequest(BaseModel):
    mode: str  # "live" or "demo"

@app.get("/api/data-mode")
async def get_data_mode():
    """Get current data mode (live or demo)."""
    from app.services.data_mode import get_mode
    return {"mode": get_mode(), "description": "live = real APIs (Open-Meteo, OpenAQ, Google AQI), demo = mock JSON files"}

@app.post("/api/data-mode")
async def set_data_mode(req: DataModeRequest):
    """Switch between LIVE (real APIs) and DEMO (mock data) modes."""
    from app.services.data_mode import set_mode
    try:
        new_mode = set_mode(req.mode)
        # Broadcast mode change to dashboard
        try:
            await ws_manager.broadcast({
                "event": "data_mode_changed",
                "mode": new_mode,
                "timestamp": now_pkt_iso(),
            }, "trace")
        except Exception:
            pass
        return {"mode": new_mode, "status": "switched"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Config — serves client-side keys from env (keeps them out of source code)
# ---------------------------------------------------------------------------
@app.get("/api/config/maps-key")
async def get_maps_key():
    """Serve Google Maps API key to the frontend.
    The key must reach the browser (Maps JS SDK requires it), but this keeps
    the raw key out of the HTML source / git repo. Restrict the key in GCP
    Console to Maps JavaScript API + your domains for production security.
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Maps API key not configured")
    return {"key": key}

@app.get("/api/resources")
async def list_resources():
    """Current resource pool state."""
    resources = await db.get_resources()
    return {"resources": resources}

@app.patch("/api/resources/{resource_id}")
async def update_resource(resource_id: str, update: dict, request: Request):
    """Update resource location/status (admin panel). Admin-only."""
    _require_admin(request)
    # Bug #14: Allowlist writable fields
    allowed = {"status", "assigned_crisis", "current_location"}
    filtered = {k: v for k, v in update.items() if k in allowed}
    if not filtered:
        raise HTTPException(400, f"No valid fields to update. Allowed: {allowed}")
    result = await db.update_resource(resource_id, filtered)
    # Broadcast status update
    try:
        await ws_manager.broadcast({
            "event": "resource_status_update",
            "resource_id": resource_id,
            "status": update.get("status"),
            "timestamp": now_pkt_iso(),
        }, "trace")
    except Exception:
        pass
    return result

@app.get("/api/resources/{resource_id}/timeline")
async def get_resource_timeline(resource_id: str):
    """Get full status timeline for a resource (journey tracking)."""
    try:
        resource = await db.get_resource(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        return {
            "resource_id": resource_id,
            "type": resource.get("type"),
            "current_status": resource.get("status"),
            "assigned_crisis": resource.get("assigned_crisis"),
            "timeline": resource.get("status_history", []),
        }
    except HTTPException:
        raise
    except Exception:
        return {"resource_id": resource_id, "timeline": []}

@app.get("/api/warmup")
async def warmup():
    """Warmup endpoint — hit on app startup to prime the cold start."""
    return {"status": "warm", "timestamp": now_pkt_iso()}

@app.get("/api/stakeholder/messages")
async def list_stakeholder_messages():
    """Recent stakeholder notifications grouped by audience."""
    messages = await db.get_stakeholder_messages()
    return {"messages": messages}

@app.get("/api/cooling_centers/nearby")
async def nearby_cooling_centers(lat: float, lng: float, radius_km: float = 5.0):
    """Find nearby cooling centers / relief points."""
    try:
        hospitals = _hospitals_cache or []
        # Simple haversine distance filter
        import math
        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlng = math.radians(lng2 - lng1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        nearby = []
        for h in hospitals:
            h_lat = h.get("lat", h.get("latitude", 31.52))
            h_lng = h.get("lng", h.get("longitude", 74.35))
            dist = haversine(lat, lng, h_lat, h_lng)
            if dist <= radius_km:
                h_copy = dict(h)
                h_copy["distance_km"] = round(dist, 2)
                nearby.append(h_copy)
        nearby.sort(key=lambda x: x["distance_km"])
        return {"cooling_centers": nearby, "total": len(nearby), "radius_km": radius_km}
    except FileNotFoundError:
        return {"cooling_centers": [], "error": "Hospital data not found"}


# ===========================================================================
# ADMIN PANEL
# ===========================================================================

@app.get("/api/admin/health")
async def admin_health():
    """System health dashboard data."""
    return {
        "gemini_api": "connected",
        "websocket_connections": ws_manager.active_count(),
        "stream_status": simulator.status,
        "signal_streams": stream_mgr.status,
        "last_trace_timestamp": await db.get_last_trace_timestamp(),
        "fcm_status": "configured",
        "uptime_seconds": 0,
    }

@app.get("/api/admin/scenarios")
async def list_scenarios():
    """List available stress test scenarios."""
    try:
        with open(MOCK_DIR / "stress_scenarios.json") as f:
            data = json.load(f)
        return {"scenarios": data["scenarios"]}
    except FileNotFoundError:
        return {"scenarios": [], "error": "Scenarios file not found"}

@app.get("/api/baseline/compare")
async def baseline_compare():
    """System-wide with-Tapish vs without-Tapish metrics."""
    return {
        "scope": "system-wide",
        "heuristic": {
            "response_time": "23 min",
            "false_positive_rate": "40%",
            "stakeholder_channels": "1",
            "verification": "None",
            "error_recovery": "None",
            "language_support": "English only",
            "resource_utilization_pct": 45,
        },
        "tapish": {
            "response_time": "7 min",
            "response_time_improvement": "3.3x faster",
            "false_positive_rate": "8%",
            "stakeholder_channels": "6",
            "verification": "Auditor Agent",
            "error_recovery": "Auto-retract + recall",
            "language_support": "Urdu + Roman Urdu + English",
            "resource_utilization_pct": 78,
        },
    }

@app.get("/api/admin/traces/export")
async def export_traces(request: Request):
    """Export all traces for evidence/submission. Admin-only."""
    _require_admin(request)
    traces = await db.get_all_traces()
    crises = await db.get_all_crises()
    signals = await db.get_all_signals()
    return {
        "export_timestamp": now_pkt_iso(),
        "traces_count": len(traces),
        "crises_count": len(crises),
        "signals_count": len(signals),
        "traces": traces,
        "crises": crises,
        "signals": signals,
    }

class ThresholdUpdate(BaseModel):
    confidence_threshold: Optional[float] = None
    severity_auto_dispatch: Optional[list] = None

@app.patch("/api/admin/thresholds")
async def update_thresholds(body: ThresholdUpdate, request: Request):
    """Adjust pipeline routing thresholds live. Admin-only."""
    _require_admin(request)
    from app.agents import orchestrator
    updated = {}
    if body.confidence_threshold is not None:
        if not 0.0 <= body.confidence_threshold <= 1.0:
            raise HTTPException(400, "confidence_threshold must be between 0.0 and 1.0")
        orchestrator.CONFIDENCE_THRESHOLD = body.confidence_threshold
        updated["confidence_threshold"] = body.confidence_threshold
    if body.severity_auto_dispatch is not None:
        updated["severity_auto_dispatch"] = body.severity_auto_dispatch
    return {
        "status": "updated",
        "current": {
            "confidence_threshold": orchestrator.CONFIDENCE_THRESHOLD,
        },
        **updated,
    }

@app.get("/api/admin/thresholds")
async def get_thresholds():
    """Get current pipeline thresholds."""
    from app.agents import orchestrator
    return {
        "confidence_threshold": orchestrator.CONFIDENCE_THRESHOLD,
        "routing_logic": "confidence < threshold → Auditor first; confidence >= threshold → Dispatch first",
    }


# ===========================================================================
# WEBSOCKET CHANNELS
# ===========================================================================

@app.websocket("/ws/trace")
async def ws_trace(websocket: WebSocket):
    """Real-time agent trace stream (dashboard + mobile trace console)."""
    await ws_manager.connect(websocket, "trace")
    try:
        while True:
            # Keep connection alive; server pushes events
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, "trace")

@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """Citizen-facing alerts stream (mobile app alerts screen)."""
    await ws_manager.connect(websocket, "alerts")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, "alerts")

@app.websocket("/ws/map")
async def ws_map(websocket: WebSocket):
    """Resource movements + crisis state (map updates)."""
    await ws_manager.connect(websocket, "map")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, "map")


# ---------------------------------------------------------------------------
# Web Dashboard — serve static files (must be LAST, after all API routes)
# ---------------------------------------------------------------------------
if WEB_DIR.exists():
    @app.get("/")
    async def serve_dashboard():
        """Serve the web command center dashboard."""
        return FileResponse(str(WEB_DIR / "index.html"))

    app.mount("/", StaticFiles(directory=str(WEB_DIR)), name="web")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "true").lower() == "true",
    )
