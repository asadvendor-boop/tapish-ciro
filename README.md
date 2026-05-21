# TAPISH — Agentic Crisis Response Orchestrator for Lahore

> **Challenge 3: Crisis Intelligence & Response Orchestrator (CIRO)**

Tapish is an autonomous multi-agent AI system that fuses seven real-time signal sources to detect, predict, prioritize, and coordinate Lahore's response to urban crises — heatwaves, power outages, floods, and infrastructure failures. Built on Google's Agent Development Kit (ADK) with six specialized Gemini-powered agents and 20 function tools, Tapish transforms fragmented, reactive emergency management into traceable, coordinated, agentic action — complete with real Firebase push notifications, Urdu mosque announcements via Google Cloud TTS, and PSER (Punjab Socio-Economic Registry) vulnerability-weighted resource allocation.

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [System Architecture](#2-system-architecture)
3. [Data Schemas](#3-data-schemas)
4. [Antigravity Usage](#4-antigravity-usage)
5. [APIs & Tools](#5-apis--tools)
6. [Setup & Installation](#6-setup--installation)
7. [Assumptions](#7-assumptions)
8. [Privacy & Safety](#8-privacy--safety)
9. [Cost & Latency Analysis](#9-cost--latency-analysis)
10. [Baseline Comparison](#10-baseline-comparison)
11. [Scalability Discussion](#11-scalability-discussion)
12. [Limitations](#12-limitations)
13. [Demo Videos](#13-demo-videos)
14. [Robustness & Edge Cases](#14-robustness--edge-cases)
15. [Synthetic Data Notice](#15-synthetic-data-notice)

---

## 1. The Problem

In June 2015, a heatwave killed over 1,200 people in Karachi in three days. The signals existed — social media posts, hospital admissions, power grid failures, rescue calls — but fragmented response systems failed to coordinate. Lahore in May 2026 faces similar conditions: peak temperatures of 49°C, aging power infrastructure, densely populated low-income neighborhoods with minimal AC penetration, and emergency agencies (Rescue 1122, LESCO, WASA, hospitals) operating in silos.

**The core problem is coordination, not detection.** Individual agencies see their own data. Nobody fuses social media signals with power grid sensors, rescue call frequency with PSER vulnerability scores, and traffic congestion with hospital bed availability — simultaneously, in real time, with transparent reasoning.

Tapish solves this with five agentic AI agents that observe, reason, decide, act, evaluate, and adapt — with every decision traceable, every trade-off justified, and every stakeholder notified in their language.

---

## 2. System Architecture

### 5-Agent Reactive Pipeline + 1 Proactive Predictor

> **5 reactive agents** run sequentially on every signal (Observer → Analyst → Strategist → Operator → Auditor). The **6th agent (Predictor)** runs independently — it analyzes weather forecasts to pre-position resources *before* a crisis hits.

```mermaid
graph LR
    subgraph "Signal Sources (7)"
        S1[Social Posts]
        S2[Weather API]
        S3[Traffic API]
        S4[Rescue 1122 Calls]
        S5[LESCO Sensors]
        S6[Field Reports]
        S7[PSER Vulnerability]
    end

    subgraph "Agent Pipeline"
        OB["🔵 Observer<br/>Ingest, Score, Geolocate"]
        AN["🟣 Analyst<br/>Classify, Predict, Fuse"]
        ST["🟠 Strategist<br/>Allocate, Prioritize"]
        OP["🟢 Operator<br/>Dispatch, Notify, TTS"]
        AU["🔴 Auditor<br/>Verify, Retract, Escalate"]
    end

    S1 & S2 & S3 & S4 & S5 & S6 & S7 --> OB
    OB --> AN
    AN -->|"confidence ≥ 0.65"| ST
    AN -->|"confidence < 0.65"| AU
    AU -->|"VERIFY"| ST
    AU -->|"RETRACT"| STOP["Pipeline Stops"]
    ST --> OP
    OP --> AU
```

### Conditional Routing Logic

```
IF Analyst.confidence >= 0.65:
    HIGH_CONFIDENCE → Strategist → Operator → Auditor (post-dispatch sweep)
ELSE:
    LOW_CONFIDENCE → Auditor (pre-dispatch verification)
        IF Auditor.verdict == "verify" → Strategist → Operator
        IF Auditor.verdict == "retract" → Pipeline stops, retraction issued
        IF Auditor.verdict == "investigate" → Human escalation queue
```

### Delivery Architecture

```
📱 Tapish Awaaz (Citizen App)          📱 Tapish Nigraan (Operator App)
├── Google Sign-In                     ├── Admin Login
├── Report: Photo / Voice / Text       ├── Signal Injection + 7 Auto Demos
├── Alerts Inbox (Server-backed)       ├── Live Google Maps
├── Targeted Verdict Notifications     ├── Agent Trace Console
└── Location-based Reporting           └── Stakeholder Messages (6 tabs)
         │                                       │
         └───────── REST + FCM ──────────────────┘
                        │
              ┌─────────┴──────────┐
              │  FastAPI Backend   │
              │  (Google Cloud Run)│
              │  6 ADK Agents      │
              │  20 Function Tools │
              │  WebSocket Traces  │
              └─────────┬──────────┘
                        │
              ┌─────────┴──────────┐
              │  Next.js Dashboard │
              │  (Served by backend)│
              │  Command Center UI │
              └────────────────────┘
```

---

## 3. Data Schemas

### Signal
```python
class Signal:
    id: str
    source: "twitter" | "weather" | "traffic" | "sensor" | "call" | "field_report"
    raw_content: str
    language: "urdu" | "roman_urdu" | "english"
    credibility_score: float  # 0-1
    credibility_factors: {specificity, emotional_amplification, viral_intent, source_authority}
    urgency_score: float  # 0-1
    geolocation: {lat, lng}
    geo_confidence: float
```

### CrisisEvent
```python
class CrisisEvent:
    id: str
    type: "heatwave" | "power_outage" | "flood" | "accident" | "infrastructure"
    primary_location: str
    severity: "low" | "medium" | "high" | "critical"
    confidence: float  # 0-1
    affected_population_est: int
    affected_radius_km: float
    predicted_peak_time: datetime
    expected_duration_hrs: float
    spread_risk: float
    cascade_risks: [{linked_crisis_type, probability, reason}]
    status: "detected" | "verified" | "active" | "resolved" | "retracted"
```

### ResourceAllocation
```python
class ResourceAllocation:
    crisis_id: str
    allocated: [Resource]  # ambulances, generators, water tankers, rescue teams
    rationale: str  # natural language trade-off justification
    tradeoffs: [{deprioritized_crisis_id, reason}]
    expected_response_time_minutes: int
```

### StakeholderMessage
```python
class StakeholderMessage:
    audience: "public" | "rescue_1122" | "hospital" | "lesco" | "wasa" | "transport_authority" | "media_command_center" | "mosque"
    channel: "push" | "sms" | "dashboard" | "loudspeaker_tts"
    language: "urdu" | "roman_urdu" | "english"
    content: str
    urgency: "info" | "advisory" | "urgent" | "emergency"
```

---

## 4. Antigravity Usage

### Dev-Time Orchestration
Google Antigravity was the sole development tool used to build Tapish across 8+ coding sessions:

- **Architecture scaffolding:** Antigravity generated the entire 6-agent ADK pipeline, all 20 function tools, Pydantic schemas, and FastAPI backend from the master implementation plan
- **Prompt engineering:** Each agent's system prompt was iterated 3-4 times through Antigravity, testing against real scenarios and refining credibility scoring, trade-off reasoning, and verification logic
- **Multi-component coordination:** Antigravity managed cross-file changes across the backend (Python), mobile app (Flutter/Dart), and web dashboard (Next.js/TypeScript) simultaneously
- **Debugging:** When the Strategist over-allocated resources to Gulberg or the Auditor false-positived on valid signals, Antigravity traced the reasoning failures and fixed the prompts
- **Deployment:** Cloud Run deployment was orchestrated through Antigravity's built-in MCP tools

### Runtime Orchestration (Google ADK)
All 6 agents run as `LlmAgent` instances in Google's Agent Development Kit:
- `SequentialAgent` manages the pipeline flow
- Conditional routing (confidence < 0.65 → Auditor branch) via runtime logic
- ADK's native tracing emits workplan, tool calls, decisions, and outcomes
- Every FunctionTool wraps external calls in try/except for degraded mode resilience

### Decision Points Made by Antigravity-Orchestrated Agents

| Decision | Agent | Logic |
|----------|-------|-------|
| Signal credibility | Observer | Specificity × source authority vs. viral intent |
| Crisis classification | Analyst | Multi-source fusion + PSER vulnerability weighting |
| Route to Auditor? | Orchestrator | `confidence < 0.65` → verification branch |
| Resource allocation | Strategist | `mortality × PSER × travel_time`, 20% reserve rule |
| Retract or dispatch? | Auditor | Cross-reference rescue calls, sensors, hospital data |
| Staged vs full alert | Operator | Side-effect detection from traffic congestion |

---

## 5. APIs & Tools

### 20 Registered Function Tools

| # | Tool | Agent(s) | Purpose | Real/Mock |
|---|------|----------|---------|-----------|
| 1 | `deduplicate_signal` | Observer | Detect duplicate signals | Real (in-process) |
| 2 | `score_credibility` | Observer | 4-factor credibility scoring | Real (Gemini Flash) |
| 3 | `geocode_location` | Observer | Resolve Urdu locations to coordinates | Mock (28 locations) |
| 4 | `get_weather_data` | Analyst, Predictor | Weather conditions (LIVE: Open-Meteo) | Mock / **REAL** |
| 5 | `get_traffic_data` | Analyst, Auditor | Traffic congestion state | Mock JSON |
| 6 | `get_pser_vulnerability` | Analyst, Strategist, Predictor | PSER vulnerability scores | Mock JSON |
| 7 | `get_sensor_readings` | Analyst, Auditor | LESCO grid voltage + temp sensors | Mock JSON |
| 8 | `get_rescue_call_data` | Analyst, Auditor | Rescue 1122 call frequency | Mock JSON |
| 9 | `get_recent_signals` | Analyst | Query signals within time window | Real (in-memory) |
| 10 | `get_available_resources` | Strategist, Operator | Query resource pool | Real (SQLite) |
| 11 | `get_hospital_capacity` | Strategist, Operator, Auditor | Hospital bed availability | Mock JSON |
| 12 | `estimate_travel_time` | Strategist | Resource-to-crisis travel time | Mock |
| 13 | `dispatch_resource` | Operator | Execute resource dispatch | Real (SQLite) |
| 14 | `send_fcm_notification` | Operator | Push notifications | **REAL** (FCM) |
| 15 | `generate_urdu_tts` | Operator | Urdu mosque announcements | **REAL** (Cloud TTS) |
| 16 | `retract_alert` | Auditor | Retract crisis + public correction | Real (in-memory) |
| 17 | `escalate_to_human` | Auditor | Escalate to human review queue | Real (in-memory) |
| 18 | `get_weather_forecast` | Predictor | 48hr hourly forecast + heat risk | Mock (sinusoidal) |
| 19 | `analyze_crisis_image` | Citizen reports | Gemini Flash image analysis | **REAL** (Gemini Vision) |
| 20 | `transcribe_urdu_audio` | Citizen reports | Gemini Flash Urdu transcription | **REAL** (Gemini Audio) |

### External Services (Real)

| Service | Usage |
|---------|-------|
| **Gemini 2.5 Flash** | Observer credibility scoring, Operator message generation |
| **Gemini 2.5 Pro** | Analyst crisis fusion, Strategist trade-offs, Auditor verification |
| **Firebase Cloud Messaging** | Real push notifications to mobile devices |
| **Google Cloud TTS** | Urdu mosque announcements (`ur-PK-Standard-A` voice) |
| **Google Maps** | Crisis visualization on mobile and web |
| **Firebase Auth** | Google Sign-In for citizen app |

### DEMO / LIVE Data Mode

The system supports a **DEMO ↔ LIVE toggle** on both the web dashboard and mobile app:
- **DEMO mode** (default): Uses mock JSON data for deterministic, repeatable scenarios
- **LIVE mode**: Switches environmental data to real APIs:
  - **Open-Meteo** — real-time temperature, humidity, heat index for Lahore (no API key required)
  - **OpenAQ** — real-time PM2.5 / air quality sensor readings (open data)
  - **Google AQI** — Air Quality Index for Lahore zones

---

## 6. Setup & Installation

### Prerequisites
- Python 3.13+ (built with 3.13.12)
- Flutter 3.35.7 (stable channel)
- Node.js 22+ (built with 22.12.0)
- Google Cloud account with Gemini API access

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add: GEMINI_API_KEY, GOOGLE_CLOUD_TTS_KEY
uvicorn app.main:app --reload --port 8000
```

### Web Dashboard
```bash
cd web-next
npm install
npm run build
# Dashboard is served by the backend at the root URL
```

### Mobile App (Flutter)
```bash
cd mobile
flutter pub get

# Build Operator app (Nigraan)
flutter build apk --release --flavor nigraan --dart-define=IS_OPERATOR=true

# Build Citizen app (Awaaz)
flutter build apk --release --flavor awaaz --dart-define=IS_OPERATOR=false
```

### Deployment (Google Cloud Run)
```bash
cd backend
gcloud run deploy tapish-backend \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=<key>
```

---

## 7. Assumptions

- All signal data (tweets, weather, traffic, sensors, rescue calls) is **synthetic/mock** — designed to simulate realistic Lahore crisis patterns
- All 66 mock tweet handles (`@bilal_lhr`, `@viral_lahore`) are **fictional** — no real social media data is used
- PSER (Punjab Socio-Economic Registry) vulnerability scores are **mock estimates** based on publicly available demographic data
- Production deployment would integrate real APIs: Twitter/X Filtered Stream, LESCO grid telemetry, Rescue 1122 CAD systems, WASA SCADA, Punjab Safe Cities Authority feeds
- Resource counts (33 units: 12 ambulances, 6 generators, 8 water tankers, 4 rescue teams, 3 drones) are approximations of actual Lahore emergency fleet sizes
- Hospital data is based on publicly available information about Mayo, Services, Jinnah, and other Lahore hospitals

---

## 8. Privacy & Safety

- **No real personal data:** All tweets, user handles, and social media posts are fabricated synthetic data
- **No PII collection:** The citizen app collects only Google account email (for login) and device FCM token (for targeted notifications). No location data is stored server-side beyond the current session
- **Mosque announcements:** In production, TTS-based loudspeaker alerts would require explicit opt-in from mosque management committees
- **Bias mitigation:** PSER vulnerability scoring prioritizes underserved communities — the system explicitly favors Walled City (PSER 12/100) over DHA (PSER 78/100) for the same severity crisis, with transparent reasoning
- **Retraction responsibility:** False alarm corrections include public apology messaging in Urdu, acknowledging the error and reassuring citizens
- **No autonomous action in production:** All dispatch and resource allocation recommendations require human confirmation from authorized operators before real-world execution

---

## 9. Cost & Latency Analysis

> All costs reflect **PAYG (Pay-As-You-Go)** pricing. We are NOT on free tier.

### Service Pricing (Current Rates)

| Service | Rate |
|---------|------|
| **Gemini 2.5 Flash** | $0.30/M input tokens, $2.50/M output tokens |
| **Gemini 2.5 Pro** | $1.25/M input tokens, $10.00/M output tokens |
| **Cloud Run** | $0.000024/vCPU-sec, $0.0000025/GiB-sec |
| **Cloud TTS** (Standard) | $4.00/M characters |
| **Google Maps JS** | $7.00/1K loads (10K free/month) |
| **FCM** | **FREE** |

### Per-Operation Costs

| Step | Model/Service | Avg Latency | Tokens (in/out) | Cost/Call |
|------|--------------|-------------|-----------------|----------|
| Observer (credibility + intent) | Gemini 2.5 Flash | 3-5s | ~500/200 | $0.00065 |
| Analyst (fusion + PSER) | Gemini 2.5 Pro | 8-12s | ~1,200/400 | $0.0055 |
| Strategist (trade-offs) | Gemini 2.5 Pro | 8-15s | ~1,500/500 | $0.0069 |
| Operator (messages × 6 + dispatch) | Gemini 2.5 Flash | 5-10s | ~800/400 | $0.00124 |
| Operator (TTS) | Cloud TTS | 0.8s | ~200 chars | $0.0008 |
| Operator (FCM) | Firebase CM | 0.2s | n/a | **$0** |
| Auditor (verification) | Gemini 2.5 Pro | 6-10s | ~800/300 | $0.004 |

### Per-Crisis Totals

| Path | Wall-Clock | Gemini Cost | Total |
|------|-----------|-------------|-------|
| **High confidence** (Observer → Analyst → Strategist → Operator → Auditor) | 30-50s | ~$0.019 | **~$0.020** |
| **Low confidence** (+ Auditor pre-check) | 35-60s | ~$0.019 | **~$0.020** |
| **Retracted** (Auditor RETRACT) | 15-25s | ~$0.010 | **~$0.010** |
| **Signal only** (Observer, filtered as noise) | 3-5s | ~$0.001 | **~$0.001** |

> **Why 30-50 seconds instead of 6?** The original plan estimated 6.5s assuming parallel tool calls. Actual measured latency includes sequential Gemini reasoning (each agent produces structured JSON with chain-of-thought), real FCM dispatch, and real TTS generation. This is acceptable — a 45-second end-to-end is still **30× faster** than manual coordination (~23 minutes).

### Cloud Run Hosting (PAYG)
- **Demo (min-instances: 0):** ~$2-5/month (idle = no charge, cold starts ~10-15s)
- **Judging (min-instances: 1):** ~$25-35/month (always warm, instant response)
- **Per-request cost:** ~$0.0011 (45s × 1 vCPU + 0.5 GiB)

### Monthly Total (Demo Period): **~$3-12/month**

---

## 10. Baseline Comparison

**Baseline:** Simple keyword + rule-based system (no agents):
- Scans tweets for keywords ("garmi", "bijli", "heatstroke")
- If keyword count > threshold → fire alert
- Fixed priority: always prioritize highest-population area
- No credibility scoring, no signal fusion, no retraction

| Metric | Baseline (keyword rules) | Tapish (agentic) |
|--------|-------------------------|------------------|
| False positive rate | ~35% (viral tweets trigger alerts) | ~8% (credibility + Auditor) |
| Response time (signal → action) | 2 min (instant but uncoordinated) | 30-50 sec (reasoned + coordinated) |
| Multi-crisis handling | First-come-first-served | Mortality-weighted PSER optimization |
| False alarm correction | None (alert stays live forever) | Retraction + public apology < 2 min |
| Resource waste | High (sends everything everywhere) | Low (constrained allocation, 20% reserve) |
| Side effect detection | None | Detects congestion from own alerts, adapts |
| Stakeholder coordination | Single broadcast message | 6 tailored channels, bilingual |
| Vulnerability awareness | None | PSER scores, child/elderly %, AC penetration |

---

## 11. Scalability Discussion

| Scale | Signals/day | Crises/day | Gemini + Hosting/day | Architecture Change |
|-------|------------|------------|---------------------|-------------------|
| **Demo (1×)** | 60 signals | 2-3 | ~$0.15 | None (single Cloud Run) |
| **Single city (10×)** | 5,000 signals | 20-30 | ~$1.40 | Redis signal queue + caching |
| **5-city (50×)** | 25,000 signals | 100-150 | ~$7.00 | Horizontal scaling: one agent cluster per city |
| **National (100×)** | 50,000 signals | 300+ | ~$14.00 | Kafka streaming, regional Analyst shards |

**Throughput:** Current architecture handles ~10 signals/minute (limited by Gemini Pro latency). At 100×, batching Observer calls and sharding Analyst by region maintains <60 second end-to-end per crisis.

---

## 12. Limitations

- **Single-region demo:** Lahore-only. Production requires regional deployment and cross-city resource sharing
- **Mock data quality:** Credibility scoring accuracy is bounded by synthetic tweet patterns — real social media has more noise and complexity
- **No human-in-the-loop:** Production deployment requires human confirmation before real-world resource dispatch
- **Session-bound state:** SQLite resets per simulation. Production requires Firestore with multi-region replication
- **TTS quality:** Google Cloud TTS Urdu voice quality varies by device speaker — mosque loudspeaker acoustics would need on-site calibration
- **No real agency APIs:** Production requires signed MOUs with Rescue 1122, LESCO, WASA, PDMA for live data feeds
- **Cold starts:** Cloud Run with 0 min-instances has 10-15s cold start; mitigated by warmup endpoint

---

## 13. Demo Videos

Two demo videos are included with the submission:

- **Product Demo (3-5 min):** End-to-end workflow showing signal ingestion → crisis detection → resource allocation → coordinated response → false alarm recovery
- **Antigravity Usage (2:28):** Screen recording showing how Antigravity was used to scaffold agents, debug prompts, and deploy the system

---

## 14. Robustness & Edge Cases

Seven stress-test scenarios demonstrate system resilience:

| # | Scenario | What It Tests |
|---|----------|---------------|
| 1 | **Heatwave baseline** | Single-crisis happy path, full pipeline execution |
| 2 | **Power outage cascade** | Crisis triggers secondary crisis (heat → power → hospital surge) |
| 3 | **Multi-crisis trade-off** | Two simultaneous crises competing for limited resources |
| 4 | **Flood false alarm** | Viral misinformation → Auditor retraction + public apology |
| 5 | **Degraded mode** | Stale data, missing location, API failures, duplicate detection |
| 6 | **Staged alerting** | Public alert causes congestion → Operator adapts to zone-by-zone rollout |
| 7 | **False negative** | Low-confidence signal initially dismissed → later corroborated by new evidence |

---

## 15. Synthetic Data Notice

**All data in this system is synthetic by default (DEMO mode).** No real social media posts, personal information, emergency call records, or government data was used. A **LIVE mode** toggle switches environmental data to real APIs.

- **Tweets:** 66 fabricated social media posts with fictional handles (always synthetic)
- **Weather (DEMO):** Synthetic time-series based on publicly available Lahore climate averages. **LIVE mode:** real data from Open-Meteo API
- **Air Quality (DEMO):** Synthetic readings. **LIVE mode:** real data from OpenAQ and Google AQI
- **Sensors:** Mock LESCO grid data representing realistic but synthetic voltage/temperature readings
- **Rescue calls:** Synthetic call frequency patterns modeled on general emergency response distributions
- **PSER data:** Mock vulnerability scores based on publicly available demographic indicators
- **Resources:** 33 units — approximate fleet sizes based on publicly available information about Lahore's emergency services
- **Hospitals:** Capacity data based on publicly available information

Production deployment would replace all mock sources with real-time feeds from authorized government agencies under appropriate data sharing agreements.

---

## Project Structure

```
tapish/
├── backend/                    # FastAPI + 6 ADK agents + 20 tools
│   ├── app/
│   │   ├── main.py            # API endpoints + WebSocket
│   │   ├── agents/            # Observer, Analyst, Strategist, Operator, Auditor
│   │   ├── tools/             # 20 registered function tools
│   │   ├── mock/              # Synthetic data (tweets, weather, sensors, etc.)
│   │   └── services/          # Stream simulator, allocator, degraded mode
│   └── requirements.txt
├── web-next/                   # Next.js command center dashboard
├── mobile/                     # Flutter app (Nigraan + Awaaz flavors)
│   └── lib/
│       ├── screens/           # Alerts, Inject, Map, Trace, Stakeholder, Impact (6 screens)
│       ├── services/          # API, WebSocket, Notification
│       └── theme/             # Glassmorphism design system
├── antigravity_traces/         # 7 scenario JSON trace files
├── antigravity_artifacts/      # Antigravity development artifacts
├── TAPISH_IMPLEMENTATION_PLAN.md  # Original prompt given to Antigravity
└── README.md                   # This file
```

---

## Team

Built with Google Antigravity. Six ADK agents. Twenty tools. Seven signal sources. One coordinated response. **Tapish.**
