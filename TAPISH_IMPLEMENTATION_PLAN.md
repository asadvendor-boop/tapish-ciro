# TAPISH — Agentic Crisis Response Orchestrator for Lahore
## Master Implementation Plan for Google Antigravity

> **⚠️ Historical Document:** This is the **original Day 1 master specification** given to Antigravity as the initial prompt. Production metrics evolved during the 7-day build — e.g., Python 3.11 → 3.13, estimated 6.5s latency → measured 30-50s, 60 → 66 tweets, 5 → 6 agents (Predictor added), 13 → 20 tools. See `README.md` and `docs/COST_LATENCY.md` for final production numbers.

> **For the Antigravity executor:** This document is your single source of truth. Build the system as specified. When ambiguous, prefer the simplest implementation that passes the demo script in section 14. Generate agent traces as first-class outputs — they are demoed live, not buried in logs.

---

## 1. The One-Line Pitch

**Tapish is an agentic AI system that fuses multi-source signals to detect, predict, prioritize, and coordinate Lahore's response to heatwave crises — turning fragmented, reactive emergency response into autonomous, traceable, multi-agent action.**

---

## 2. Why This Wins (Internal North Star)

Every design decision must serve one of these five judge-facing moments:

1. **The Roman Urdu moment** — A citizen types *"Androon Lahore mein bachay garmi se ro rahe hain, bijli 8 ghantay se nahi"* and the system extracts intent, location, urgency, and credibility in real time.
2. **The agent-trace moment** — Judges see five named ADK agents thinking on the MOBILE app's Trace Console, passing structured messages, with visible confidence scores and phase badges.
3. **The trade-off moment** — Strategist Agent justifies prioritizing Walled City over DHA on screen, with explicit PSER-based reasoning.
4. **The mosque loudspeaker moment** — Auto-generated Urdu emergency announcement plays as real Google Cloud TTS audio on stage.
5. **The retraction moment** — A false alarm gets caught, system retracts, log shows correction.
6. **The false-negative moment** — System retroactively upgrades a signal it initially ignored after new evidence arrives. Most teams won't even attempt this.
7. **The live judge moment** — A judge types any Roman Urdu tweet into the MOBILE app's "Inject" screen and watches it flow through all 5 agents in real time on the phone in their hand.
8. **The real push notification moment** — A real Firebase Cloud Messaging (FCM) notification lights up the demo phone when the Operator Agent dispatches stakeholders. Not simulated. Real-world. 100% Google ecosystem.

If a feature doesn't serve one of these moments, cut it.

---

## 3. System Architecture (5-Agent Pipeline)

```
┌──────────────────────────────────────────────────────────────────┐
│                    ANTIGRAVITY ORCHESTRATOR                       │
│  (manages plan → dispatch → execution → trace logging)            │
└──────────────────────────────────────────────────────────────────┘
        │             │             │            │             │
        ▼             ▼             ▼            ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌──────────┐  ┌──────────┐  ┌─────────┐
   │OBSERVER │   │ ANALYST │   │STRATEGIST│  │ OPERATOR │  │ AUDITOR │
   │         │ → │         │ → │          │→ │          │→ │         │
   │ ingest, │   │ classify│   │ allocate │  │ execute, │  │ verify, │
   │ score   │   │ predict │   │ prioritize│ │ notify   │  │ retract │
   └─────────┘   └─────────┘   └──────────┘  └──────────┘  └─────────┘
        │              │              │              │             │
        └──────────────┴──── shared event bus ──────┴─────────────┘
                                    │
                          ┌─────────┴──────────┐
                          ▼                    ▼
                    WEB DASHBOARD        MOBILE APP
                    (command center)    (citizen + field)
```

### Agent Roles (precise contracts)

| Agent | Input | Output | LLM Use |
|---|---|---|---|
| **Observer** | raw mock streams (tweets, weather, traffic, sensors, calls) | `Signal` objects with credibility score, geolocation confidence, urgency score | Gemini Flash for credibility scoring + Urdu NLP |
| **Analyst** | clustered Signals | `CrisisEvent` with type, severity, confidence, affected radius, population, predicted peak, evolution | Gemini Pro for fusion reasoning |
| **Strategist** | active CrisisEvents + ResourcePool | `ResourceAllocation` per crisis with trade-off justification | Gemini Pro for multi-criteria reasoning |
| **Operator** | ResourceAllocation | Executed `Action` objects + `StakeholderMessage` notifications + `MapUpdate` events | Gemini Flash for Urdu message generation |
| **Auditor** | All agent outputs + new contradicting signals | `Verification` verdict + `Retraction` if false alarm | Gemini Pro for cross-validation logic |

---

## 4. Tech Stack (Locked, Don't Deviate)

| Layer | Choice | Why |
|---|---|---|
| **Backend** | Python 3.11 + FastAPI | Best Gemini SDK ergonomics |
| **Agent runtime** | **Google ADK (Agent Development Kit)** + native Gemini function calling | Google's official multi-agent framework. Antigravity scaffolds the ADK code. This is what the rubric means by "use Antigravity to orchestrate." |
| **LLM** | `gemini-2.5-flash` (fast paths) + `gemini-2.5-pro` (reasoning paths) | Cost/latency balance |
| **DB** | SQLite + SQLAlchemy (demo) → Firestore (production note) | SQLite for fast demo build; Firestore is the production path (documented as such) |
| **Realtime** | FastAPI WebSockets | Stream agent traces to UI |
| **Web app** | Next.js 14 + TypeScript + Tailwind + shadcn/ui | Speed + polish |
| **Maps (web)** | **Google Maps JavaScript API** | Same Google ecosystem as mobile. Consistent visual treatment. |
| **Mobile app** | Flutter 3.x + Dart | Google's own framework, single codebase, direct APK build via `flutter build apk` |
| **Maps (mobile)** | `google_maps_flutter` | Native Google Maps |
| **Mobile state** | Riverpod | Lightweight, reactive |
| **Mobile WebSocket** | `web_socket_channel` | Real-time alerts from backend |
| **Mobile routing** | GoRouter | Declarative, clean |
| **TTS for mosque demo** | Google Cloud TTS API (`ur-PK-Standard-A`) + Browser `SpeechSynthesis` fallback | High-quality Urdu voices |
| **Real stakeholder notifications** | **Firebase Cloud Messaging (free, Google-native)** | A real FCM push notification arrives on the demo phone during stakeholder dispatch. 100% Google ecosystem. Goosebump moment for judges. |
| **Animations** | Framer Motion (web), Flutter built-in animations (mobile) | Judge-grade polish |
| **Charts** | Recharts (web) | Quick wins |
| **Deployment** | **Google Cloud Run (backend, `min-instances: 1` during judging) + Firebase Hosting (web) + APK sideload (mobile)** | All Google ecosystem. Free tier sufficient for demo. `min-instances: 1` eliminates cold starts during judging — costs ~$0.05/day but guarantees instant response if a judge tests the live URL. |
| **Auth** | None (demo scope) | Cut scope |

---

## 5. Project Structure

```
tapish/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry, WebSocket routes
│   │   ├── agents/                    # Google ADK agents
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py        # SequentialAgent + ConditionalAgent (ADK)
│   │   │   ├── observer.py            # LlmAgent with credibility + Urdu NLP
│   │   │   ├── analyst.py             # LlmAgent with PSER + weather fusion
│   │   │   ├── strategist.py          # LlmAgent with resource allocation
│   │   │   ├── operator.py            # LlmAgent with FCM push, TTS, dispatch tools
│   │   │   ├── auditor.py             # LlmAgent with verification + retraction
│   │   │   └── trace_adapter.py       # Converts ADK traces → WebSocket events
│   │   ├── schemas/
│   │   │   ├── signal.py
│   │   │   ├── crisis.py
│   │   │   ├── resource.py
│   │   │   ├── action.py
│   │   │   └── stakeholder.py
│   │   ├── mock/
│   │   │   ├── tweets.json            # 60 Roman Urdu / Urdu / English tweets
│   │   │   ├── weather.json           # Time-series weather data
│   │   │   ├── traffic.json           # Mock Maps API responses
│   │   │   ├── sensors.json           # Mock IoT temperature sensors
│   │   │   ├── calls.json             # Mock Rescue 1122 call frequency
│   │   │   ├── resources.json         # Ambulances, generators, water tankers
│   │   │   ├── hospitals.json         # Lahore hospitals with capacity
│   │   │   ├── pser_data.json         # Mock PSER (Punjab Socio-Economic Registry) household vulnerability scores per neighborhood
│   │   │   ├── neighborhoods.geojson  # Lahore neighborhoods with PSER vulnerability overlay
│   │   │   └── stress_scenarios.json  # 5 scripted demo scenarios
│   │   ├── prompts/
│   │   │   ├── observer_credibility.txt
│   │   │   ├── observer_urdu_intent.txt
│   │   │   ├── analyst_classification.txt
│   │   │   ├── strategist_tradeoff.txt
│   │   │   ├── operator_stakeholder_msg.txt
│   │   │   ├── operator_mosque_announcement.txt
│   │   │   └── auditor_verification.txt
│   │   ├── tools/                     # ADK FunctionTool implementations (called by agents)
│   │   │   ├── pser_tool.py           # Query mock PSER vulnerability data
│   │   │   ├── weather_tool.py        # Fetch mock weather signals
│   │   │   ├── traffic_tool.py        # Fetch mock traffic state
│   │   │   ├── fcm_tool.py            # REAL Firebase Cloud Messaging — sends actual push notifications on demo
│   │   │   ├── tts_tool.py            # Google Cloud TTS for Urdu mosque announcements
│   │   │   ├── credibility_tool.py    # Credibility scoring heuristics
│   │   │   ├── deduplicator_tool.py   # Detect duplicate signals
│   │   │   ├── geocode_tool.py        # Mock geocoding
│   │   │   ├── travel_time_tool.py    # Compute resource→crisis travel time
│   │   │   ├── dispatch_tool.py       # Update resource status in DB
│   │   │   ├── escalation_tool.py     # Push to Manual Review queue + FCM push notification
│   │   │   ├── recent_signals_tool.py # Query SQLite for signals within 2km + 30min (Analyst clustering)
│   │   │   ├── sensor_readings_tool.py # Check mock LESCO grid + temp sensor data
│   │   │   ├── rescue_calls_tool.py   # Check mock Rescue 1122 call frequency
│   │   │   ├── cross_reference_tool.py # Cross-reference signals against multiple sources
│   │   │   ├── retract_alert_tool.py  # Update CrisisEvent status to "retracted" in SQLite
│   │   │   ├── stakeholder_msg_tool.py # Generate tailored messages per audience
│   │   │   └── map_route_tool.py      # Update map pin positions for rerouting
│   │   └── services/
│   │       ├── stream_simulator.py    # Pumps mock streams on a configurable timer
│   │       ├── allocator.py           # Constrained resource optimizer (mortality × PSER × travel_time)
│   │       └── degraded_mode.py       # Handles stale data, missing geo, API failures, rate limits
│   ├── tests/
│   │   └── test_scenarios.py
│   ├── requirements.txt
│   └── .env.example
├── web/
│   ├── app/
│   │   ├── page.tsx                   # Command center dashboard (main view)
│   │   ├── admin/page.tsx             # Admin panel (resources, thresholds, health)
│   │   ├── trace/page.tsx             # Full agent trace viewer
│   │   └── layout.tsx
│   ├── components/
│   │   ├── CrisisMap.tsx              # Google Maps with crisis overlays + resource movement
│   │   ├── SignalFeed.tsx             # Live ingesting signals with credibility badges
│   │   ├── LiveSignalInject.tsx       # THE JUDGE KILLER — text input to inject live tweets
│   │   ├── AgentTracePanel.tsx        # Streaming agent thoughts, color-coded
│   │   ├── ResourceAllocator.tsx      # Trade-off visualization with constraint display
│   │   ├── StakeholderInbox.tsx       # Tailored notifications grouped by audience
│   │   ├── BeforeAfterToggle.tsx      # Impact simulation (with-Tapish vs without-Tapish)
│   │   ├── BaselineComparison.tsx     # Side-by-side metrics chart (response time, lives saved)
│   │   ├── RetractionBanner.tsx       # False alarm correction UI with timeline
│   │   ├── AdminResources.tsx         # Admin: add/remove/relocate resources on map
│   │   ├── AdminThresholds.tsx        # Admin: adjust agent confidence thresholds
│   │   └── AdminHealth.tsx            # Admin: system health, API latency, stream status
│   ├── lib/
│   │   ├── api.ts
│   │   └── ws.ts                      # WebSocket client
│   └── package.json
├── mobile/                              # Flutter app
│   ├── lib/
│   │   ├── main.dart                    # Entry point + theme + GoRouter setup
│   │   ├── screens/
│   │   │   ├── alerts_screen.dart       # Citizen alerts feed (bilingual Urdu/English)
│   │   │   ├── nearby_screen.dart       # Heat stroke centers / relief points map
│   │   │   └── report_screen.dart       # Citizen incident report (Roman Urdu input)
│   │   ├── widgets/
│   │   │   ├── alert_card.dart          # Severity-colored alert card
│   │   │   ├── cooling_center_map.dart  # Google Maps with pins
│   │   │   ├── report_form.dart         # Roman Urdu / Urdu / English input
│   │   │   └── agent_badge.dart         # Shows which agent generated the alert
│   │   ├── services/
│   │   │   ├── ws_service.dart          # WebSocket client for real-time alerts
│   │   │   └── api_service.dart         # REST calls to backend
│   │   ├── models/
│   │   │   ├── alert_model.dart
│   │   │   └── cooling_center_model.dart
│   │   └── providers/
│   │       └── crisis_provider.dart     # Riverpod state management
│   ├── android/                         # Android-specific config
│   ├── pubspec.yaml
│   └── build_apk.sh                     # Script: flutter build apk --release
├── docs/
│   ├── README.md                      # Submission README (all 15 required sections)
│   ├── ARCHITECTURE.md                # Mermaid diagrams, data flow, agent contracts
│   ├── ANTIGRAVITY_USAGE.md           # How Antigravity is used (for the 20-25% score)
│   ├── COST_LATENCY.md                # Cost per op, baseline comparison, 10x/100x scaling
│   ├── SYNTHETIC_DATA_NOTICE.md       # Required: clearly label all mock data as synthetic
│   └── DEMO_SCRIPT.md
└── demo/
    ├── video1_product_demo/           # 3-5 min product demo video assets
    ├── video2_antigravity_usage/      # 2-3 min Antigravity screen recording assets
    │   └── RAW_CAPTURES.md            # Notes on when to start/stop screen recording during dev
    └── storyboard.md
├── antigravity_traces/                  # REQUIRED DELIVERABLE — raw JSON agent trace logs
│   ├── scenario_1_baseline.json
│   ├── scenario_2_cascade.json
│   ├── scenario_3_multi_crisis.json
│   ├── scenario_4_false_alarm.json
│   ├── scenario_5_degraded_mode.json
│   ├── scenario_6_staged_alerting.json
│   └── scenario_7_false_negative.json
```

---

## 6. Data Schemas (Pydantic)

```python
# schemas/signal.py
class Signal(BaseModel):
    id: str
    source: Literal["twitter", "weather", "traffic", "sensor", "call", "field_report"]
    raw_content: str
    language: Literal["urdu", "roman_urdu", "english", "n/a"]
    timestamp: datetime
    geolocation: GeoPoint | None
    geo_confidence: float  # 0-1
    credibility_score: float  # 0-1 (computed as mean of credibility_factors)
    credibility_factors: dict  # {specificity_score, emotional_amplification, viral_intent_score, source_authority}
    urgency_keywords: list[str]  # words conveying urgency extracted by Observer
    urgency_score: float  # 0-1 (computed from urgency_keywords density)
    mention_velocity: int  # mentions per 5 min window
    contradictions: list[str]  # IDs of contradicting signals
    extracted_intent: dict  # crisis type, location, severity hints

# schemas/crisis.py
class CrisisEvent(BaseModel):
    id: str
    type: Literal["heatwave", "power_outage", "flood", "accident", "infrastructure", "protest", "disease_cluster"]
    primary_location: str  # e.g. "Walled City - Mochi Gate"
    affected_radius_km: float
    affected_population_est: int
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float  # 0-1
    predicted_peak_time: datetime
    expected_duration_hrs: float
    spread_risk: float
    uncertainty_range: dict  # {"severity": "high could be critical", "population": "35k-55k", "duration": "4-8 hrs"}
    contributing_signals: list[str]  # Signal IDs that were fused into this crisis
    cascade_risks: list[dict]  # [{linked_crisis_type, probability, reason}] — matches Analyst prompt output
    status: Literal["detected", "verified", "active", "resolved", "retracted"]  # Analyst defaults to "detected"

# schemas/resource.py
class Resource(BaseModel):
    id: str
    type: Literal["ambulance", "generator", "water_tanker", "rescue_team", "drone", "field_team"]
    operator: Literal["rescue_1122", "lesco", "wasa", "edhi", "chhipa", "punjab_health"]
    current_location: GeoPoint
    status: Literal["available", "dispatched", "in_use", "returning"]
    capacity: int
    assigned_crisis: str | None

class ResourceAllocation(BaseModel):
    crisis_id: str
    allocated: list[Resource]
    rationale: str  # natural language justification from Strategist
    tradeoffs: list[str]  # crises NOT prioritized and why

# schemas/action.py
class Action(BaseModel):
    id: str
    type: Literal["reroute_traffic", "dispatch_unit", "open_cooling_center",
                  "alert_hospital", "request_grid_priority", "deploy_water_tanker",
                  "issue_public_alert", "mosque_announcement"]
    target_location: GeoPoint
    parameters: dict
    expected_impact: dict  # response_time_delta, lives_saved_est, congestion_delta
    resource_cost: dict  # {"units_consumed": 2, "estimated_hours": 3, "opportunity_cost": "DHA gets delayed response"}
    side_effects: list[str]  # e.g. "hospital alert may cause panic rush on GT Road"
    status: Literal["planned", "executing", "completed", "failed", "cancelled"]

# schemas/stakeholder.py
class StakeholderMessage(BaseModel):
    audience: Literal["public", "rescue_1122", "hospital", "lesco", "wasa", "traffic_police_transport_authority", "media_command_center", "mosque", "cm_health_program"]
    channel: Literal["push", "sms", "email", "dashboard", "loudspeaker_tts"]
    language: Literal["urdu", "roman_urdu", "english"]
    content: str
    urgency: Literal["info", "advisory", "urgent", "emergency"]
    crisis_id: str
```

---

## 7. Mock Data Specifications

### 7.1 Tweets (60 entries, mix of credible/non-credible/contradicting)

Generate `mock/tweets.json` with this distribution:
- **20 credible heatwave signals** in Walled City — Roman Urdu, Urdu, English mixed
- **15 credible power outage signals** in DHA/Gulberg
- **10 noise/irrelevant tweets** (cricket, food, politics — to test filtering)
- **8 ambiguous tweets** (could be heatwave or something else)
- **5 low-credibility/misinformation** (the Liberty Market false alarm seed)
- **2 contradicting field report tweets** (water main vs flood — borrowed from PDF example)

Sample entries:
```json
[
  {
    "id": "tw_001",
    "user": "@bilal_lhr",
    "follower_count": 432,
    "verified": false,
    "text": "Androon Lahore mein bachay garmi se ro rahe hain, bijli 8 ghantay se nahi hai. Mohalle wale pareshan hain.",
    "timestamp": "2026-05-12T14:03:00+05:00",
    "geo_hint": "Bhati Gate area",
    "_ground_truth": "credible_heatwave"
  },
  {
    "id": "tw_034",
    "user": "@viral_lahore",
    "follower_count": 12000,
    "verified": false,
    "text": "Breaking! Liberty Market mein 20 log behosh ho gaye hain garmi se! Share karo jaldi!",
    "timestamp": "2026-05-12T15:20:00+05:00",
    "geo_hint": "Liberty Market",
    "_ground_truth": "false_alarm"
  }
]
```

### 7.2 Lahore neighborhoods (`neighborhoods.geojson`)

Polygon features for at least these 8 areas, with `vulnerability_score` metadata (0–1):
- Walled City (Mochi Gate, Bhati Gate, Shahalmi cluster) — vulnerability 0.92
- Misri Shah — 0.85
- Shahdara — 0.80
- Baghbanpura — 0.78
- DHA Phase 5 — 0.35
- Gulberg III — 0.30
- Model Town — 0.40
- Cantt — 0.32

Vulnerability factors derived from **Mock PSER (Punjab Socio-Economic Registry) Data:**
- PSER household poverty score (0-100, lower = more vulnerable)
- Population density per sq km
- AC penetration estimate (proxy from PSER income band)
- Tree cover / heat island index
- Distance to nearest hospital
- Percentage of households with children under 5 or elderly 65+ (from PSER demographic data)

**Why PSER:** The Punjab Socio-Economic Registry is CM Maryam Nawaz's flagship digital initiative to map every household's socio-economic status for targeted subsidies. Using PSER data (mocked) signals that Tapish is built for Punjab's CURRENT digital infrastructure — not legacy datasets. Judges familiar with Punjab's civic-tech landscape will immediately recognize this alignment.

### 7.3 Resources (`resources.json`)

- **12 ambulances** (Rescue 1122 + Edhi + Chhipa), distributed across Lahore
- **6 mobile generators** (LESCO + private)
- **8 water tankers** (WASA)
- **4 rescue teams** (Rescue 1122)
- **3 drones** (for damage assessment)

### 7.4 Stress test scenarios (`stress_scenarios.json`)

Five pre-scripted scenarios that the stream simulator can play in sequence:

1. **Baseline heatwave** — single-crisis happy path
2. **Cascade** — heatwave triggers power outage triggers hospital surge
3. **Multi-crisis** — heatwave in Walled City + power outage in Gulberg (the trade-off scenario)
4. **False alarm** — viral misinformation about Liberty Market, system retracts with public apology + log update
5. **Degraded mode** — weather API stops responding mid-crisis, system falls back to sensor + social only, flags data staleness
6. **Staged alerting** — public alert for Walled City causes evacuation congestion on GT Road; Operator Agent detects congestion spike as side effect, switches to staged/zone-by-zone alerting + reroutes evacuation traffic. This scenario is EXPLICITLY required by the updated rubric.
7. **False NEGATIVE (natural pipeline detection)** — Observer initially scores a vague tweet ("Mera AC nahi chal raha bhai") at credibility 0.31, filters it as noise. 10 minutes later, 5 more similar tweets arrive from the same area. These new tweets enter the pipeline normally: Observer scores them individually (each ~0.4-0.5), then **Analyst clusters them** with the earlier 0.31 signal, detects the geographic pattern, and calls `check_sensor_readings_tool` which reveals a LESCO voltage drop in that zone. The Analyst generates a new high-confidence CrisisEvent (0.85+) that triggers the full Strategist → Operator dispatch chain. This proves the system catches false negatives **naturally within the standard pipeline flow** — no phantom background sweep needed. The key is the Analyst's signal fusion + sensor cross-reference on the second pass.

**Additional degraded mode sub-tests baked into scenario 5:**
- Stale data: weather API returns data with 45-min-old timestamp → system flags as stale, reduces confidence by 0.15, adds uncertainty note
- Missing location: tweet has no geo_hint → system attempts fuzzy match from text, falls back to "Lahore-wide" if no match, logs low geo_confidence
- Duplicate incidents: two tweets about same event in Bhati Gate → system deduplicates by location + time window, merges into single signal cluster
- Rate limits: Gemini API returns 429 → system queues request, processes next signal from cache, retries with exponential backoff

The judges should see scenarios 3, 4, 5, 6, and 7 in the demo video. (Scenario 7 = false negative is a critical rubric requirement Gemini's review flagged.)

---

## 8. Agent Prompt Templates (Concrete, Production-Ready)

### 8.1 Observer — Urdu Intent Extraction

```
You are the Observer Agent in Tapish, a crisis response system for Lahore.

A citizen has posted: "{text}"
Language detected: {language}
User metadata: {follower_count} followers, verified: {verified}
Timestamp: {timestamp}

Extract and return STRICT JSON:
{
  "crisis_type_hint": "heatwave|power_outage|flood|accident|other|none",
  "location_mentions": ["specific places named, e.g. 'Bhati Gate', 'Walled City'"],
  "urgency_keywords": ["words conveying urgency"],
  "severity_hint": "low|medium|high|critical",
  "language_confidence": 0.0-1.0,
  "translation_en": "english translation if not english",
  "credibility_factors": {
    "specificity_score": 0.0-1.0,
    "emotional_amplification": 0.0-1.0,
    "viral_intent_score": 0.0-1.0,
    "source_authority": 0.0-1.0
  },
  "trace_reasoning": "one sentence explaining your reading"
}

Be skeptical of vague viral-sounding posts. Be charitable to specific, geolocated, low-follower posts (they're often the most credible).
```

### 8.2 Analyst — Classification & Severity

```
You are the Analyst Agent. Fuse the following clustered signals into a CrisisEvent.

Signals:
{signals_json}

Mock weather context:
{weather_json}

Mock traffic context:
{traffic_json}

Historical context: Lahore in May 2026. Last week saw 44C peak. Karachi 2015 heatwave (1200+ deaths) is the comparable reference event.

PSER (Punjab Socio-Economic Registry) vulnerability data per neighborhood:
{pser_vulnerability_data}
(PSER scores: 0-100 where lower = more vulnerable. Includes household poverty score, child/elderly %, AC penetration estimate.)

Return STRICT JSON CrisisEvent with:
- type, primary_location, affected_radius_km, affected_population_est
- severity (low/medium/high/critical)
- confidence (0-1) — be honest. <0.6 means more signals needed.
- predicted_peak_time, expected_duration_hrs, spread_risk
- contributing_signals: array of signal IDs that you fused into this crisis
- cascade_risks: array of {linked_crisis_type, probability, reason}
- status: always "detected" (will be updated by later agents)
- trace_reasoning: 2-3 sentence explanation including any contradictions noticed

If signals contradict (e.g., flood vs water main burst), set confidence below 0.65 and list both hypotheses.
```

### 8.3 Strategist — Trade-off Justification

```
You are the Strategist Agent. You have N active crises and constrained resources. Allocate optimally and explain trade-offs.

Active crises:
{crises_json}

Available resources:
{resources_json}

Rules:
1. Mortality risk dominates: severity × population × PSER vulnerability score is the primary objective. Lower PSER score = higher priority.
2. Travel time matters: don't dispatch a unit 15km away when one is 3km away.
3. Reserve at least 20% capacity for unexpected events.
4. Always document what you DID NOT prioritize, and why.
5. For pediatric emergencies in high-vulnerability zones, flag for routing to CM Children Heart Surgery Program (Maryam Ki Masihaai) facilities if applicable.

Return STRICT JSON: ResourceAllocation[] for each crisis.

For each allocation include:
- allocated: list of resource IDs
- rationale: 1-2 sentences in plain language
- tradeoffs: explicit list of {deprioritized_crisis_id, reason}
- expected_response_time_minutes
- mortality_risk_reduction_estimate (qualitative: low/medium/high)
- trace_reasoning: your step-by-step decision logic

The trade-off explanation is what wins us the demo. Make it crisp and defensible.
```

### 8.4 Operator — Mosque Announcement (Urdu TTS)

```
You are the Operator Agent. Generate a 20-second Urdu announcement to be played on neighborhood loudspeakers.

Crisis: {crisis_type}
Location: {primary_location} (specifically: {neighborhood_detail})
Severity: {severity}
Recommended action for citizens: {action}
Nearest relief point: {relief_point_name} ({distance_km} km, directions: {directions})
(Relief points include: Maryam Ki Masihaai heat stroke center, WASA water tanker location, nearest hospital emergency ward, or government shelter)

Tone: calm, authoritative, respectful. Use simple Urdu that elderly and children can understand. Start with "السلام علیکم". End with Rescue 1122 helpline number and reassurance.

IMPORTANT: Use culturally appropriate language. Do NOT use Western terms like "cooling center". Instead reference:
- "قریبی ہسپتال" (nearest hospital)
- "حکومتی ہیٹ سٹروک سینٹر" (government heat stroke center — Maryam Ki Masihaai program)
- "واسا پانی کی ٹینکی" (WASA water tanker point)
- "سبیل" (community cold water distribution)
- Rescue 1122 helpline: 1122

EXECUTION ORDER (MANDATORY — do NOT skip tool calls):
1. FIRST: Call `send_fcm_notification_tool` for each stakeholder that needs a push notification
2. THEN: Call `generate_urdu_tts_tool` with the Urdu text to create the audio file
3. THEN: Call `dispatch_resource_tool` for each resource movement
4. THEN: Call `update_map_route_tool` for any traffic rerouting
5. ONLY AFTER all tools return success: Output the final JSON summary of actions taken

Do NOT just write the message text and stop. You MUST call the tools to execute the actions.

Output:
1. Urdu text (for TTS)
2. Roman Urdu transliteration (for the dashboard display)
3. English translation (for judges who don't read Urdu)
```

### 8.6 Operator — Media Press Brief

```
You are the Operator Agent. Generate TWO separate media press briefs for immediate release.

Crisis: {crisis_type}
Location: {primary_location}
Severity: {severity}
Affected population: {affected_population_est}
Actions taken: {actions_summary}
Resources deployed: {resources_deployed}

Tone: factual, authoritative, no speculation. Include: what happened, what is being done, who to contact.

You MUST output TWO separate message objects:
1. First message: language="english", audience="media_command_center" — 3-sentence English press brief
2. Second message: language="urdu", audience="media_command_center" — 3-sentence Urdu press brief

Do NOT combine both languages into a single message. Each message gets its own language tag.
```

### 8.5 Auditor — Verification

```
You are the Auditor Agent. Recently issued alert: {alert}

New incoming signals that may relate:
{new_signals}

Independent corroboration sources (mock):
- Rescue 1122 call frequency in area: {call_frequency}
- Sensor readings: {sensor_readings}
- Traffic anomaly: {traffic_state}
- Hospital admission spike: {admission_data}

Decide: VERIFY | RETRACT | INVESTIGATE_FURTHER

Return STRICT JSON:
{
  "verdict": "verify|retract|investigate",
  "confidence": 0.0-1.0,
  "supporting_evidence": [...],
  "contradicting_evidence": [...],
  "recommended_action": "string",
  "public_retraction_message_urdu": "if retract: a respectful retraction notice",
  "trace_reasoning": "your verification logic"
}

A retraction is not a failure. It's a feature. State explicitly when correcting.

EXECUTION ORDER (MANDATORY):
- If verdict is RETRACT: You MUST call `retract_alert_tool` with the crisis_id to update its status to "retracted" in the database BEFORE outputting JSON. This ensures the Flutter app removes the map pin and shows the retraction banner.
- If verdict is INVESTIGATE_FURTHER: You MUST call `human_escalation_tool` to push the signal to the Manual Review queue + send an FCM push notification.
- If verdict is VERIFY: No tool call needed — just output the JSON verdict.

Do NOT output a retract verdict without calling retract_alert_tool. The database must reflect the decision.
```

---

## 9. Orchestrator (Google ADK — Agent Development Kit)

**Critical rubric alignment:** The hackathon requires Antigravity to orchestrate multi-agent workflows. We use **Google's Agent Development Kit (ADK)** — Google's official open-source multi-agent framework — as the runtime orchestrator. Antigravity scaffolds, debugs, and iterates this ADK code as part of development. This is exactly what "use Antigravity to orchestrate" means: Antigravity is the dev-time agent that builds the runtime agent system using Google's native patterns.

**⚠️ CRITICAL IMPLEMENTATION RULE: All FunctionTools MUST wrap external calls in try/except.** If a mock API throws an exception (HTTP 500, timeout, rate limit), the tool must catch it and return an error string like `{"error": "API_TIMEOUT_500", "source": "weather_api", "fallback": "use cached data"}` back to the LLM. This lets the agent reason about the failure and trigger fallback logic — instead of the Python process crashing and killing the entire SequentialAgent pipeline. This is non-negotiable for Scenario 5 (Degraded Mode).

```python
# agents/orchestrator.py
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner

# Sub-agents (each is a Gemini-powered LlmAgent with tools)
observer_agent = LlmAgent(
    name="observer",
    model="gemini-2.5-flash",
    instruction=OBSERVER_PROMPT,
    tools=[deduplicate_signal_tool, geocode_tool, credibility_score_tool],
    output_key="signal",
)

analyst_agent = LlmAgent(
    name="analyst",
    model="gemini-2.5-pro",
    instruction=ANALYST_PROMPT,
    tools=[fetch_weather_tool, fetch_traffic_tool, query_pser_tool, check_sensor_readings_tool, query_recent_signals_tool],
    output_key="crisis_event",
)

strategist_agent = LlmAgent(
    name="strategist",
    model="gemini-2.5-pro",
    instruction=STRATEGIST_PROMPT,
    tools=[get_resources_tool, compute_travel_time_tool, query_pser_tool],
    output_key="allocation",
)

operator_agent = LlmAgent(
    name="operator",
    model="gemini-2.5-flash",
    instruction=OPERATOR_PROMPT,
    tools=[
        generate_stakeholder_message_tool,
        send_fcm_notification_tool,       # REAL FCM push notification
        generate_urdu_tts_tool,            # Google Cloud TTS
        update_map_route_tool,
        dispatch_resource_tool,
        fetch_traffic_tool,                # Needed for Scenario 6: detect congestion side effects from own alerts
    ],
    output_key="actions",
)

auditor_agent = LlmAgent(
    name="auditor",
    model="gemini-2.5-pro",
    instruction=AUDITOR_PROMPT,
    tools=[
        cross_reference_signals_tool,
        check_rescue_1122_calls_tool,
        check_sensor_readings_tool,
        retract_alert_tool,
        human_escalation_tool,             # For INVESTIGATE_FURTHER: pushes to Manual Review queue + FCM notification
    ],
    output_key="verdict",
)

# ⚠️ CRITICAL: The pipeline must NOT run Strategist/Operator after a RETRACT verdict.
# ⚠️ CRITICAL: SequentialAgent runs ALL items in order — so dispatch logic must be
#    INSIDE conditional branches, never loose in the top-level array.

# Reusable dispatch chain (Strategist → Operator)
dispatch_branch = SequentialAgent(
    name="dispatch_branch",
    sub_agents=[strategist_agent, operator_agent],
)

# Main pipeline
tapish_pipeline = SequentialAgent(
    name="tapish_orchestrator",
    sub_agents=[
        observer_agent,
        analyst_agent,
        ConditionalAgent(
            condition=lambda ctx: ctx.get("crisis_event", {}).get("confidence", 1.0) < 0.65,
            # LOW CONFIDENCE PATH: Auditor verifies first
            on_true=SequentialAgent(
                name="verification_branch",
                sub_agents=[
                    auditor_agent,
                    # Only dispatch if Auditor says VERIFY (not RETRACT/INVESTIGATE_FURTHER)
                    # NOTE: Must match Auditor prompt output exactly — prompt says "verify|retract|investigate"
                    ConditionalAgent(
                        condition=lambda ctx: ctx.get("verdict", "").lower() == "verify",
                        on_true=dispatch_branch,
                        # on_false: pipeline stops here — crisis retracted or escalated safely
                    ),
                ],
            ),
            # HIGH CONFIDENCE PATH: dispatch immediately, Auditor sweeps post-dispatch
            on_false=SequentialAgent(
                name="dispatch_and_sweep",
                sub_agents=[
                    dispatch_branch,
                    auditor_agent,  # Post-dispatch sweep for false negatives
                ],
            ),
        ),
    ],
)

# NOTE: Exact ADK ConditionalAgent API (kwargs, on_false=None behavior) will be
# verified on Day 1 with the ADK hello-world test. The LOGIC above is correct —
# the syntax may need minor adjustment based on the installed ADK version.

runner = Runner(agent=tapish_pipeline, app_name="tapish")
```

**Key ADK benefits the rubric will reward:**
- **Built-in tracing:** ADK exports structured traces (workplan, task plan, tool calls, decisions, outcomes) natively — perfect for the rubric's trace requirements
- **Tool registry:** Every external integration (FCM, TTS, PSER lookup, Maps) is a registered `FunctionTool` that shows up in the trace as a tool call
- **Conditional flows:** Native `ConditionalAgent` for the low-confidence → Auditor routing
- **Parallel execution:** Auditor runs concurrently with Operator to detect false alarms in real time
- **Memory + state:** Built-in session state passes structured data between agents (no manual state machine needed)
- **Direct Vertex AI integration:** Production path is one config change away

Every ADK agent invocation auto-emits trace events. We pipe these to our WebSocket `/ws/trace` endpoint with one adapter function.

---

## 10. WebSocket Trace Protocol

Every agent emits structured events:

```json
{
  "agent": "observer",
  "step": "credibility_scoring",
  "phase": "observe",
  "timestamp": "2026-05-12T14:03:01.234Z",
  "workplan": "Ingest tweet → extract intent → score credibility → cluster with existing signals",
  "task": "Score credibility of incoming tweet tw_001",
  "input_summary": "Tweet from @bilal_lhr about Bhati Gate: 'Androon Lahore mein bachay garmi se ro rahe hain...'",
  "reasoning": "Specific location (Bhati Gate), low follower count (432 = low viral intent), urgency keywords present ('ro rahe hain', 'bijli nahi'). No contradiction with existing signals. Credibility 0.82.",
  "tool_calls": [
    {"tool": "gemini-2.5-flash", "action": "extract_intent", "input_tokens": 180, "output_tokens": 95},
    {"tool": "deduplicator", "action": "check_duplicate", "result": "no_match"}
  ],
  "decision": "Flag as credible_heatwave signal, pass to clustering",
  "output_summary": "Signal scored: credibility=0.82, urgency=0.78, type=heatwave, location=Bhati Gate",
  "error_recovery": null,
  "adaptation": null,
  "duration_ms": 312,
  "model": "gemini-2.5-flash"
}
```

**Adaptation trace example** (from Operator Agent when staged alerting kicks in):
```json
{
  "agent": "operator",
  "step": "staged_alerting_adaptation",
  "phase": "adapt",
  "workplan": "Issue public alert → monitor side effects → adapt if congestion detected",
  "task": "Adapt alert strategy after detecting evacuation congestion",
  "reasoning": "Initial full-zone alert for Walled City caused GT Road congestion spike (traffic API shows 3x baseline). Switching to zone-by-zone staged alerting: Bhati Gate first, Mochi Gate in 8 min, Shahalmi in 15 min. This distributes evacuation load.",
  "tool_calls": [
    {"tool": "traffic_api_mock", "action": "check_congestion", "result": "3x_baseline_GT_Road"},
    {"tool": "gemini-2.5-flash", "action": "generate_staged_schedule", "input_tokens": 220, "output_tokens": 140}
  ],
  "decision": "Switch from full-zone to staged 3-phase alerting",
  "adaptation": "Strategy changed from single bulk alert to staged zone-by-zone rollout based on observed congestion side effect. This is the system ADAPTING — not following a fixed rule.",
  "error_recovery": null,
  "duration_ms": 580,
  "model": "gemini-2.5-flash"
}
```

**Error recovery trace example** (from degraded mode):
```json
{
  "agent": "analyst",
  "step": "stale_data_recovery",
  "phase": "evaluate",
  "reasoning": "Weather API returned data with 45-min-old timestamp. Marking as stale. Reducing confidence by 0.15. Falling back to sensor + social signals only.",
  "error_recovery": {"type": "stale_data", "source": "weather_api", "staleness_minutes": 45, "action": "confidence_penalty_applied", "fallback": "sensor+social_only"},
  "adaptation": "Analyst now weights sensor data 2x higher than usual to compensate for missing weather confirmation."
}
```

**The 6-phase agentic loop** (judges will look for ALL of these):
| Phase | Agent | What judges see |
|---|---|---|
| **Observe** | Observer | Ingests signals, scores credibility |
| **Reason** | Analyst | Fuses signals, classifies crisis, predicts severity |
| **Decide** | Strategist | Allocates resources, justifies trade-offs |
| **Act** | Operator | Dispatches units, sends alerts, generates mosque announcement |
| **Evaluate** | Auditor | Verifies signals, catches false alarms, retracts |
| **Adapt** | Operator (re-entry) | Changes strategy based on side effects (staged alerting, congestion rerouting) |

Each trace event carries a `phase` field so the dashboard can visually group them into the 6-phase loop. This directly maps to the rubric's requirement.

The Web Dashboard's `AgentTracePanel` renders these as cascading cards, one per agent. Each card has a colored stripe (Observer=blue, Analyst=purple, Strategist=orange, Operator=green, Auditor=red). The `phase` badge (observe/reason/decide/act/evaluate/adapt) shows in the top-right corner of each card.

**This is the 20-25% Antigravity score made visible.**

---

## 11. UI/UX Specification

### 11.1 Web Dashboard (Supplementary Big-Screen View)

**Scope cut:** Web is OPTIONAL per rubric. Mobile carries the wow features. Web is the big-screen accompaniment for the demo video and a presentation-quality view for judges' eyes.

**Single page, 2-column layout (simplified from 3 to save build time):**

- **Left column (60%)** — **Google Maps** of Lahore with crisis hotspots, resource movement animations, PSER vulnerability overlay. Big and visual — this is what shows on the projector during demo.
- **Right column (40%)** — Live agent trace stream + stakeholder inbox + scenario controls

**Top bar:** Scenario selector, simulation speed slider, pause/play. Live Signal Inject box (same backend endpoint as mobile — judges can use either).

**Admin Panel (minimized to ONE tab — System Health):**
- Gemini API latency
- WebSocket connection count
- Mock stream status
- Last trace timestamp
- FCM connection status (online/offline)

That's it. Cut the Resources/Thresholds/Scenario Manager tabs from earlier plan — too much scope, mobile carries the actual judge interaction.

**Polish touches:**
- Google Maps custom style: dark mode with Lahore landmarks highlighted
- Smooth Framer Motion transitions for crisis appearance
- Sound design: subtle "tick" when new signal arrives, soft alert chime when crisis confirmed
- "Trade-off Mode" toggle that splits the map side-by-side
- "Without Tapish" baseline comparison toggle

### 11.2 Mobile App (Flutter) — **PRIMARY COMMAND CENTER**, 5 screens, bilingual UI, APK deliverable

**Critical rubric alignment:** Mobile is the MANDATORY deliverable; web is optional. So mobile gets the wow features, not web. Live Signal Inject, agent trace overlay, and trade-off visualization all live primarily on mobile.

**All UI text is bilingual** — Urdu primary, English secondary. Tab labels, button text, headers, empty states all show both. Example: tab label shows "الرٹس / Alerts". Cultural sensitivity signal.

**Screen 1: Alerts (default tab) — "الرٹس"**
- Card-based feed of active alerts in user's area
- Each card shows: crisis icon, severity color, **Urdu headline** + English subtitle, distance from user, time, and **"Agent badge"** showing which of the 5 agents generated this alert
- Tap to expand: full details, recommended actions, FULL agent reasoning trace inline
- Real FCM push notification arrives on the phone when crisis fires
- Pull-to-refresh, WebSocket-driven, haptic feedback on arrival

**Screen 2: Live Map (map tab) — "نقشہ"**
- `google_maps_flutter` with current location
- Crisis hotspots pulse with severity-colored auras
- Resource icons (ambulances) animate along streets toward dispatched locations
- PSER vulnerability overlay (subtle red-to-green shading by neighborhood)
- Tap any crisis pin → opens crisis detail sheet with full agent trace
- Toggle button: "Without Tapish" mode — same signals but no coordination, shows the chaos baseline

**Screen 3: Inject (the JUDGE KILLER tab) — "تجربہ"**
- Big text input that accepts Roman Urdu / Urdu / English
- Placeholder: "...اپنی جگہ کا مسئلہ بیان کریں — judge, test it"
- Suggested prompts as chips: example tweets judges can tap to inject
- **Optimistic UI / streaming states (CRITICAL for demo):** When submitted, do NOT show a generic loading spinner. Instead:
  - Observer badge immediately glows blue + pulses → its output renders as it arrives via WebSocket
  - Analyst badge lights purple → crisis card starts forming
  - Strategist badge lights orange → trade-off reasoning streams in
  - Operator badge lights green → stakeholder messages appear
  - Auditor badge lights red (if triggered)
  - This turns a 12-second pipeline wait into a **fascinating live execution sequence** instead of a frozen app
- Real-time: Observer → Analyst → (maybe Auditor) → Strategist → Operator
- This is the SAME pipeline as scripted scenarios, fired by judge's own input
- End state: crisis card appears, real FCM push notification arrives on the phone

**Screen 4: Trace Console (trace tab) — "ایجنٹ ٹریس"**
- Live-streaming agent trace panel — color-coded cards
- Phase badges (observe/reason/decide/act/evaluate/adapt)
- Tap any trace → expand to see workplan, tools called, decision, outcome
- Filter chips: by agent (Observer/Analyst/etc.) or by crisis
- This is the agentic transparency the rubric demands, on the mandatory deliverable

**Screen 5: Stakeholder Inbox (inbox tab) — "اطلاعات"**
- Grouped by audience: Public / Rescue 1122 / Hospital / LESCO / WASA / Transport Authority (Lahore Traffic Police) / Media & Command Center / CM Health Program
- Each message shows: language, urgency, content, delivery channel (push notification/dashboard/loudspeaker)
- **Bilingual display:** Urdu text displayed prominently, with an *italicized English translation* immediately below it — ensures non-Urdu-reading judges understand every message
- For mosque announcements: Urdu text + Roman Urdu transliteration + English translation, all visible
- Tap a stakeholder message → see how it was generated (which agent, which prompt, which trace)
- Shows the "stakeholder communication" rubric requirement explicitly

**Polish touches:**
- Material 3 theming with custom Tapish brand colors (heat orange + cool blue)
- Hero animations between alert card and detail view
- HapticFeedback on alert arrival
- Real push notifications via `flutter_local_notifications` triggered by WebSocket events
- **Mosque TTS plays ON THE PHONE:** Use `audioplayers` Flutter package. When Operator generates TTS, the audio URL streams via WebSocket to the app. The phone itself speaks the Urdu announcement — no laptop speakers needed. Makes the mobile deliverable feel like a real command center.
- Empty states with friendly bilingual copy
- Splash screen with Tapish logo

**APK build:** `flutter build apk --release` → produces `build/app/outputs/flutter-apk/app-release.apk`
Include `build_apk.sh` script in repo root for one-command build.

---

## 12. Backend API Surface

```
# Simulation control
POST /api/simulation/start         body: {scenario_id}
POST /api/simulation/pause
POST /api/simulation/reset
GET  /api/simulation/status        current scenario, time, active agents

# Core data
POST /api/signals/ingest           body: {raw_text, language, geo_hint?} — LIVE INJECT from dashboard or mobile
GET  /api/crises                   list active crises with full CrisisEvent objects
GET  /api/crises/{id}              single crisis detail
GET  /api/crises/{id}/trace        full agent trace chain for a crisis
GET  /api/crises/{id}/actions      all actions taken for this crisis
GET  /api/resources                resource pool state
PATCH /api/resources/{id}          update resource location/status (admin panel)
GET  /api/stakeholder/messages     recent notifications grouped by audience
GET  /api/cooling_centers/nearby   query: {lat, lng, radius_km} → list

# Admin panel
GET  /api/admin/health             Gemini API latency, WS connections, stream status, last trace
GET  /api/admin/thresholds         current agent thresholds
PATCH /api/admin/thresholds        update confidence/severity thresholds
GET  /api/admin/scenarios          list available stress test scenarios
POST /api/admin/scenarios          create/edit a scenario from JSON

# Baseline comparison
GET  /api/baseline/compare/{crisis_id}   returns with-Tapish vs without-Tapish metrics

# WebSocket channels
WS   /ws/trace                     real-time agent trace stream (dashboard)
WS   /ws/map                       resource movements + crisis state (dashboard)
WS   /ws/alerts                    citizen-facing alerts (mobile app listens here)
```

---

## 13. Day-by-Day Build Schedule (Progressive Enhancement)

> **The Golden Rule:** At the end of Day 4, you must have a submittable project. Days 5-6 are polish. Day 7 is packaging. If anything slips, you ship what you have — a working 5-agent pipeline with 3 mobile screens beats a half-finished 5-screen app every time.

### Day 1 (Monday) — Foundation + Mock Data + ADK Setup
**Morning:**
- Repo init, monorepo structure (`backend/`, `web/`, `mobile/`, `antigravity_artifacts/`, `antigravity_traces/`)
- **Create Antigravity implementation_plan.md (FIRST THING):** Ask Antigravity to generate the official implementation plan as a native artifact. This becomes the "source of truth" that judges will see. All subsequent task tracking happens through Antigravity artifacts.
- Backend: FastAPI scaffold, Pydantic schemas (incl. `uncertainty_range`, `resource_cost`), env config
- **Install Google ADK:** `pip install google-adk`
- **ADK Hello World (MANDATORY before any agent code):** Create a minimal `LlmAgent` with one `FunctionTool`, run it with Gemini Flash, verify exact import paths (`from google.adk.agents import LlmAgent` etc.). If the pip release has different class names, discover them now — not after 500 lines of agent logic. Save the working hello-world as `tests/test_adk_hello.py`.
- Gemini API integration test (Flash + Pro)
- Google Cloud TTS API test with Urdu voice (`ur-PK-Standard-A`)
- **Firebase setup:** Create Firebase project, enable FCM, add `google-services.json` to Flutter app, test push notification to demo phone
- **Verify Antigravity deployment path:** Check if Antigravity has a native "Deploy" or "Host" feature. If yes → use it (maximizes 20-25% integration score). If it deploys TO Cloud Run natively (which it does via its Cloud Run MCP tools) → deploy through Antigravity, not via manual `gcloud` CLI. Document this in ANTIGRAVITY_USAGE.md: "Deployment orchestrated through Antigravity's built-in Cloud Run integration."
- **START SCREEN RECORDING for Antigravity Usage Video** (Video 2)

**Afternoon:**
- Generate ALL mock data: tweets (60 incl. false-negative seed tweets), weather, neighborhoods GeoJSON, resources, hospitals, heat stroke centers (Maryam Ki Masihaai), WASA tanker points, **PSER vulnerability data**
- Write `stream_simulator.py` (configurable speed)
- SQLite schema: signals, crises, resources, actions, traces, stakeholder_messages
- WebSocket `/ws/trace`, `/ws/alerts` skeletons

**End of day gate:** Mock stream pumps tweets. `POST /api/signals/ingest` works. FCM push notification sends test message to demo phone. ADK installed and one hello-world ADK agent runs.

### Day 2 (Tuesday) — Observer + Analyst Agents (Google ADK)
**Morning:**
- Implement Observer as an `LlmAgent` with tools: `deduplicate_signal_tool`, `geocode_tool`, `credibility_score_tool`
- All FunctionTools wrapped in try/except (return error strings, never crash)
- Test with credible vs viral vs noise tweets
- ADK trace adapter → WebSocket emission working

**Afternoon:**
- Implement Analyst as an `LlmAgent` with tools: `weather_tool`, `traffic_tool`, `pser_tool`
- Wire up first end-to-end flow via ADK `SequentialAgent`
- Confirm PSER tool returns vulnerability scores per neighborhood
- Test with the cascade scenario to verify multi-signal fusion

**End of day gate:** Observer + Analyst run as ADK agents. Trace stream visible. PSER tool call shows up in trace as a tool invocation.

### Day 3 (Wednesday) — Strategist + Operator + Auditor + Full Pipeline
**Morning:**
- Implement Strategist `LlmAgent` with tools: `get_resources_tool`, `compute_travel_time_tool`, `pser_tool`
- Multi-crisis prioritization test (scenario 3)
- Implement `resource_cost` computation per action

**Afternoon:**
- Implement Operator `LlmAgent` with tools: `generate_stakeholder_message_tool`, `send_fcm_notification_tool` (REAL), `generate_urdu_tts_tool`, `dispatch_resource_tool`, `fetch_traffic_tool`
- Implement Auditor `LlmAgent` with tools: `cross_reference_signals_tool`, `retract_alert_tool`, `check_sensor_readings_tool`, `human_escalation_tool`
- Wire full ADK orchestrator with `ConditionalAgent` (low confidence → Auditor)
- Implement Live Signal Inject endpoint
- **Test:** Run scenario 3, verify real FCM push notification arrives + TTS generates

**End of day gate:** Full 5-agent ADK pipeline runs scenarios 1 and 3. Real FCM push arrives on phone. Mosque TTS generates. This is your CORE PRODUCT — everything after this is delivery vehicle.

---

### 🛑 STOP GATE 1: After Day 3, the AI is done. Everything below is UI + packaging.

---

### Day 4 (Thursday) — Flutter Mobile App: 3 CORE SCREENS (Submittable MVP)

> **After Day 4, you have a submittable project.** 3 screens + working pipeline = competitive entry.

**Morning:**
- `flutter create tapish_mobile` + dependencies: `web_socket_channel`, `flutter_riverpod`, `go_router`, `audioplayers`, `flutter_local_notifications`
- 3-screen scaffold with bottom nav (bilingual tab labels: الرٹس / تجربہ / ٹریس)
- WebSocket clients for `/ws/alerts` and `/ws/trace`
- **Screen 1 (Alerts):** Card feed with Urdu headlines + English subtitle + severity color + agent badge. Pull-to-refresh. WebSocket-driven.

**Afternoon:**
- **Screen 2 (Inject — THE JUDGE KILLER):** Text input + streaming agent badges (Observer blue → Analyst purple → Strategist orange → Operator green → Auditor red). Optimistic UI — agents light up one-by-one, never show a loading spinner.
- **Screen 3 (Trace Console):** Scrolling color-coded agent trace cards with phase badges (observe/reason/decide/act/evaluate/adapt). Tap to expand reasoning.
- Material 3 theme (heat orange + cool blue), splash screen
- `audioplayers` plays mosque TTS when Operator fires
- `flutter_local_notifications` triggers on WebSocket alert arrival
- **Connect to backend:** Inject → full pipeline → alert appears → FCM push notification → TTS plays on phone

**End of day gate:** APK installs on real Android phone. All 3 screens work. Judge types a tweet on Inject screen → 5 agents fire → trace shows on Trace Console → alert appears on Alerts screen → FCM push arrives → phone speaks Urdu. **THIS IS A SUBMITTABLE PROJECT.**

---

### 🛑 STOP GATE 2: If you're behind, skip Day 5 progressive items. Deploy what you have. Ship > polish.

---

### Day 5 (Friday) — Progressive Enhancement + Deploy

**Morning (PROGRESSIVE — only if Day 4 is solid):**
- **Screen 4 (Map):** Add `google_maps_flutter` + `geolocator`. Simple Google Map with colored circle markers for crisis zones + resource position pins. **NO animated ambulances, NO route drawing, NO traffic overlay.** Just pins. This takes 3-4 hours max.
- **Minimal web page (for projector):** Single HTML page with Google Maps JS + WebSocket trace sidebar. No framework needed — just vanilla JS. For the demo video's "wide map" shot. 2-3 hours max.

**Afternoon — DEPLOY (NON-NEGOTIABLE):**
- Backend → **Google Cloud Run** via Antigravity's Cloud Run tools. Set `min-instances: 1`.
- Web page → **Firebase Hosting** (`firebase deploy`)
- Point Flutter app to Cloud Run URL, rebuild APK
- Smoke test: everything works over the internet, not localhost
- Verify FCM push notifications from Cloud Run
- Verify TTS generates from Cloud Run

**End of day gate:** Deployed to the public internet. APK has production URL. Everything works remotely. If map screen shipped, bonus. If not, 3 screens still win.

### Day 6 (Saturday) — Stress Scenarios + Polish
**Morning:**
- Implement remaining scenarios: 2 (cascade), 4 (false alarm + retraction), 5 (degraded mode), 6 (staged alerting), **7 (false negative — Auditor retroactive upgrade)**
- Tune ALL agent prompts (iterate 2-3 times per prompt)
- Verify each scenario emits clean traces

**Afternoon:**
- Full UI polish pass on mobile (the primary deliverable)
- Mosque TTS audio quality test through phone speaker
- Run the FULL demo flow front-to-back 3 times with screen recording
- Fix everything that breaks
- **Export traces:** Run all 7 scenarios, save JSON to `antigravity_traces/`

**End of day gate:** All 7 scenarios run cleanly. Mobile app feels solid. Live FCM push + TTS + Inject all work end-to-end from Cloud Run.

### Day 7 (Sunday) — TWO Demo Videos + Documentation + Submission
**Morning:**
- Write final README with ALL 15 required sections
- ANTIGRAVITY_USAGE.md (critical for 20-25% score)
- COST_LATENCY.md with actual measured latencies
- ARCHITECTURE.md with Mermaid diagrams
- SYNTHETIC_DATA_NOTICE.md

**Afternoon:**
- **Video 1 (Product Demo, 4 min):** Record using storyboard in section 14. Mobile-first. Include real phone footage.
- **Video 2 (Antigravity Usage, 2:30 min):** Edit raw screen recordings from Days 2-3.
- **Export agent traces:** Run all 7 scenarios, capture to `antigravity_traces/`
- **Export Antigravity artifacts to repo (REQUIRED DELIVERABLE):**
  ```
  📁 antigravity_artifacts/
  ├── implementation_plan.md    ← Created by Antigravity on Day 1 as the official plan
  ├── task.md                   ← Progress tracking created during Days 1-6
  ├── walkthrough.md            ← Post-build summary created on Day 7
  └── sample_prompts.md         ← Curated key prompts given to Antigravity
  ```
  These are the artifacts judges will review. They prove Antigravity orchestrated the development.
- Final APK rebuild if any last-minute fixes
- Upload both videos to YouTube (unlisted)
- Submission: GitHub repo (public) + Video 1 + Video 2 + APK + Antigravity artifacts

**IMPORTANT:** Cloud Run backend must be warm before submission — `curl /api/simulation/status`.

---

## 14. Demo Video Storyboard (4 min target)

**This is the script. Memorize it. The video makes or breaks the submission.**

- **Video pacing note:** The 7 scenarios + 5 agents + TTS + FCM push in ~4 min means tight pacing. Fast-forward agent "thinking" pauses (6-sec waits) at 2x in the editor. Keep raw trace logs visible but move the visual pace along. Never pause on a loading spinner.
- **CRITICAL STAGING:** Mobile (Flutter APK, screen-mirrored) is the PRIMARY visual for 80%+ of the video. Web dashboard appears ONLY for the wide map view. Judges must see the mandatory deliverable doing the heavy lifting.

### 0:00–0:25 — The Hook
- Black screen. Text fades in: *"Karachi, June 2015. A heatwave killed 1,200 people in three days. Lahore in May 2026 is hotter."*
- Cut to heat shimmer B-roll over Lahore skyline (royalty-free)
- Voiceover: *"The signals existed. The data was there. Fragmented systems failed to coordinate. Tapish is what coordinated response looks like."*
- Title card: **TAPISH** — Agentic Crisis Response for Lahore

### 0:25–1:10 — Detection (MOBILE-FIRST)
- **Split screen: Flutter app (screen-mirrored, left 60%) + terminal/trace log (right 40%)**
- Phone shows **Screen 1 (Alerts)** — empty, waiting
- Voiceover: *"2:00 PM, May 12, 2026. Walled City."*
- Tweets start appearing on the Alerts screen — Roman Urdu text visible on the phone
- Tap an alert card → expand view shows **agent badge** (Observer) + credibility score 0.82
- Switch to **Screen 4 (Trace Console)** on the phone
- Observer Agent card glows blue, its **reasoning steps** stream in: *"Specific location (Bhati Gate), low follower count, urgency keywords present. Credibility 0.82."*
- Voiceover: *"The Observer Agent ingests social posts, weather, traffic, sensor data. Each signal gets a credibility score — these are the agent's reasoning steps, visible in real time on the phone."*
- Analyst Agent card lights purple on the Trace Console
- Voiceover: *"The Analyst Agent fuses signals: heatwave in Bhati Gate, severity CRITICAL, confidence 91%, predicted peak 4 PM. 45,000 people in the affected radius."*

### 1:10–2:00 — The Trade-off (MOBILE TRACE CONSOLE)
- Still on the phone's **Screen 4 (Trace Console)**
- New crisis card appears: power outage in DHA
- Voiceover: *"While we're tracking the Walled City crisis, a second event emerges."*
- **Strategist Agent** card lights orange on the Trace Console
- Voiceover: *"4 ambulances. 2 generators. Two simultaneous crises. The Strategist Agent makes the agent decision."*
- Trace Console shows the Strategist's reasoning streaming in: *"Walled City: PSER vulnerability score 12/100, no AC, 38% elderly/child. Gulberg: PSER 78/100, AC-dependent. Prioritize Walled City: 3 ambulances. Pediatric cases flagged for Maryam Ki Masihaai."*
- **Side effect prediction visible:** Trace card shows: *"⚠️ Side Effect: Re-routing 3 ambulances leaves Gulberg with 1 unit for 45 min. Mitigation: Edhi backup notified."*
- Voiceover: *"The agent decision is transparent — it shows what it prioritized, what it deprioritized, and why. This is the trade-off moment."*

### 2:00–2:50 — Coordinated Execution (MOBILE + REAL-WORLD ACTIONS)
- Switch to **Screen 2 (Live Map)** on the phone
- **Traffic rerouting simulation (NO polylines needed):** Trace Console shows Operator action: *"GT Road BLOCKED — generating alternate route via Canal Road."* On the map, a Transport Authority pin snaps to the GT Road / Bhati Gate intersection to simulate the physical blockade. Voiceover: *"The system doesn't just detect — it coordinates. Transport Authority dispatched to GT Road."*
- Ambulance pins animate toward Walled City (simple marker position updates)
- Switch to **Screen 5 (Stakeholder Inbox)** on the phone
- Messages cascade, each with bilingual Urdu + *English translation*:
  - "Mayo Hospital: incoming heatstroke admissions, prepare 6 beds"
  - "WASA: deploy 2 tankers to Mochi Gate sabeel point"
  - "LESCO: priority restoration — Bhati Gate sector"
  - "Transport Authority: Reroute GT Road, deploy wardens to Canal Road"
  - "Media & Command Center: FOR IMMEDIATE RELEASE — Heatwave emergency..."
- Voiceover: *"Each stakeholder receives a tailored message. This is the action execution phase — five coordinated actions dispatched simultaneously."*
- **REAL FCM PUSH MOMENT:** Keep the Flutter app open in foreground (Screen 5). The push notification drops down as a **heads-up banner** at the top of the screen while the app remains visible. *"🚨 TAPISH ALERT — Heatwave dispatch to Bhati Gate."* The ping sound plays. **Do NOT lock the phone** — Android blocks background audio if the app is backgrounded.
- Voiceover: *"That's a real Firebase Cloud Messaging push notification. Not simulated. 100% Google ecosystem."*
- **MOSQUE TTS MOMENT:** Immediately after, the phone speaks the Urdu announcement through its speaker via `audioplayers` (app is still in foreground, so audio plays unblocked): *"السلام علیکم۔ یہ اعلان ہے..."*
- Voiceover: *"Google Cloud TTS generates the Urdu mosque announcement. The phone is the command center."*

### 2:50–3:30 — False Alarm AND False Negative (MOBILE TRACE CONSOLE)
- Back to **Screen 4 (Trace Console)** on the phone

**False Positive:**
- New signal card appears: *"BREAKING: Liberty Market mein 20 log behosh!"* — credibility badge shows 🔴 0.21
- **Auditor Agent** card lights red on Trace Console
- Trace shows reasoning: *"Rescue 1122 calls in Liberty: 0. Sensors: normal. Hospital admissions: flat. Verdict: RETRACT."*
- Voiceover: *"Before issuing a public alert, the Auditor Agent's reasoning steps cross-reference four independent sources. The agent decision: retract. False alarm caught before public panic."*

**False Negative:**
- Earlier tweet flashes: *"Mera AC nahi chal raha bhai"* — originally scored 0.31
- 10 min later (fast-forward): 5 similar tweets arrive from the same area
- New tweets enter the pipeline normally → Observer scores each ~0.4-0.5
- **Analyst clusters them** with the earlier 0.31 signal, detects geographic pattern, calls sensor tool → LESCO voltage drop confirmed
- Analyst generates high-confidence CrisisEvent (0.85+) → full dispatch chain fires
- Voiceover: *"Five new tweets from the same neighborhood. The Analyst's reasoning steps cluster them with the earlier dismissed signal, cross-references sensor data, and generates a high-confidence crisis. The false negative is caught naturally — same pipeline, second pass, better evidence."*

### 3:30–3:50 — Impact (BRIEF WEB DASHBOARD — 20 seconds only)
- **Only now** cut to the web dashboard for the wide map view
- Side-by-side comparison displayed as a simple text table (no React toggle needed — vanilla JS renders this):
  - **Without Tapish:** 17 heatstroke admissions, 4 critical, avg response delay 23 min
  - **With Tapish:** 17 admissions, 0 critical, avg response delay 7 min
- Lives saved counter: **12**
- Voiceover: *"Same signals. Same resources. Different system. Here's the baseline comparison on the command center map."*

### 3:50–4:10 — The Judge Killer (MOBILE — LIVE INJECT)
- Back to the phone: **Screen 3 (Inject)**
- Type live: *"Misri Shah mein garmi bahut zyada hai"*
- Hit submit → agents light up one by one on screen (Observer blue → Analyst purple → Strategist orange → Operator green)
- Crisis card appears, FCM push notification arrives
- Voiceover: *"Any tweet. Any language. The same pipeline. Try it yourself."*

### 4:10–4:20 — Close
- Five agent badges line up on the phone screen
- *"Built with Google Antigravity. Five ADK agents. One coordinated response. Tapish."*
- Logo + team name + GitHub link
- *"Hand us the phone — type any tweet."* (tease Live Signal Inject for Q&A)

---

## 14B. SECOND Demo Video — Antigravity Usage Recording (2-3 min)

**This is a SEPARATE deliverable.** The rubric requires a 2-3 minute screen recording showing how your team used Antigravity to build the system. This is NOT the product demo — it's a behind-the-scenes of your development process.

**Record this during Day 2-3 while actively building.** Don't reconstruct it later — judges can tell.

### Storyboard (2:30 target)

**0:00–0:20 — Setup**
- Show Antigravity IDE open with the project
- Voiceover: *"Here's how we used Google Antigravity to build Tapish's 5-agent pipeline."*
- Show the TAPISH_IMPLEMENTATION_PLAN.md loaded as context

**0:20–0:50 — Agent Scaffolding**
- Screen record: Antigravity generating the Observer Agent code from the prompt template
- Show it creating `observer.py` with the credibility scoring logic
- Show the agent generating the Pydantic schemas from the spec
- *"Antigravity scaffolded our agent contracts and prompt templates. We iterated on the Observer's credibility scoring prompt 3 times."*

**0:50–1:20 — Orchestration Wiring**
- Screen record: Antigravity helping wire the Google ADK orchestrator
- Show it creating the ConditionalAgent routing (low confidence → Auditor)
- Show it generating the WebSocket trace emitter
- *"The multi-agent orchestration graph — with conditional routing — was built and tested in Antigravity."*

**1:20–1:50 — Debugging + Iteration**
- Screen record: A scenario that failed (e.g., Strategist produced bad allocation)
- Show Antigravity helping debug the prompt, adjusting the trade-off logic
- Show the fix and re-run
- *"When the Strategist Agent over-allocated to Gulberg, Antigravity helped us trace the reasoning failure and fix the prompt."*

**1:50–2:10 — Tool Integration**
- Screen record: Antigravity helping integrate Google Cloud TTS for Urdu mosque announcements
- Show it generating the TTS service code
- *"Even the Urdu TTS integration was orchestrated through Antigravity."*

**2:10–2:30 — Close**
- Show the final working pipeline running
- *"Antigravity wasn't just our IDE. It was our development partner — from architecture to debugging to deployment."*
- End card: team name + Tapish logo

**IMPORTANT:** Start screen recording on Day 2 morning. Capture 15-20 minutes of raw footage of you using Antigravity. You'll edit it down to 2:30 on Day 7. Don't try to fake this after the fact.

---

## 15. README.md (Submission)

Required sections (rubric mandates — every one of these is checked by judges):
1. **One-paragraph project description**
2. **The problem** (with Pakistan/Lahore context, heatwave mortality stats)
3. **System architecture** (Mermaid diagram of the 5 agents + 6-phase agentic loop)
4. **Data stream schemas** — link to `schemas/` with Pydantic definitions
5. **How Antigravity is used** — critical, get this right (see section 16)
6. **APIs / Tools used** — Gemini Flash, Gemini Pro, Google ADK, Google Cloud TTS, Google Maps JS API, Google Maps Flutter, Firebase Cloud Messaging, mock streams
7. **Setup steps (copy-paste ready):**
```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add GEMINI_API_KEY, GOOGLE_CLOUD_TTS_KEY, MAPBOX_TOKEN
uvicorn app.main:app --reload --port 8000

# Web Dashboard
cd web && npm install && npm run dev  # opens http://localhost:3000

# Flutter Mobile App
cd mobile && flutter pub get && flutter run  # or: flutter build apk --release
```
8. **Assumptions** — explicit list: all data is synthetic/mock; production would integrate real Twitter API, Maps API, LESCO/Rescue 1122 APIs; no real personal data used; all tweets are fabricated
9. **Privacy / Safety note** — no real personal data; mock tweets use fictional handles; mosque announcements are opt-in in production; no facial data or PII collected
10. **Cost & latency analysis** — see section 17
11. **Baseline comparison** — see section 17B
12. **Scalability discussion** — see section 17C
13. **Limitations** — single-region demo; production needs human-in-the-loop for critical dispatch; mock data quality bounds the credibility scoring accuracy; TTS quality varies by device
14. **Demo video links** — main demo (3-5 min) + Antigravity usage video (2-3 min)
15. **Synthetic data label** — clearly state: "All tweets, sensor data, weather data, and resource positions are synthetic. No real social media posts or personal information were used."

---

## 16. ANTIGRAVITY_USAGE.md (For the 25% / 20% Antigravity Score)

This document is the one judges will read most carefully. Be precise.

### How Antigravity is used (dev-time AND runtime)

**Dev-time orchestration:**
- Antigravity scaffolded the entire Google ADK agent pipeline (Observer, Analyst, Strategist, Operator, Auditor) from the spec
- Antigravity wrote, debugged, and iterated each agent's prompt template across 3 rounds of testing
- Antigravity managed cross-file changes when the schema evolved (e.g., adding `uncertainty_range`, `resource_cost`, `pser_score`)
- Antigravity orchestrated the Flutter mobile app build, FastAPI backend, and Cloud Run deployment as a coordinated multi-component task
- See `demo/video2_antigravity_usage/` for the 2:30 screen recording proving this

**Runtime orchestration (Google ADK — the runtime arm of the Antigravity ecosystem):**
- All 5 agents run as `LlmAgent` instances in Google's Agent Development Kit
- `SequentialAgent` manages the happy-path pipeline
- `ConditionalAgent` routes low-confidence crises to Auditor before Strategist
- `ParallelAgent` runs Auditor concurrently with Operator for real-time false-alarm detection
- ADK's native tracing emits workplan, task plan, tool calls, decisions, and outcomes — exactly matching the rubric trace requirement
- This is what "use Antigravity to orchestrate" means in production: Antigravity (dev) + Google ADK (runtime) is the canonical Google agentic stack

### Decision points Antigravity-orchestrated code makes

| Decision | Where | Logic |
|---|---|---|
| Cluster or new crisis? | After Observer | Geo + time + type proximity |
| Route to Auditor first? | After Analyst | `confidence < 0.65` → Auditor branch |
| Resource allocation | Strategist | mortality × PSER × travel_time, constrained |
| Retract or proceed? | Auditor | Cross-reference rescue calls, sensors, hospital data |
| Staged or full alert? | Operator (adapt) | Side-effect detection from traffic API |
| Retroactive upgrade? | Analyst (fusion) | Clusters new signals with old low-confidence ones, cross-references sensor data, generates high-confidence crisis on second pass |

### Tool integrations (registered as ADK FunctionTools)

| Tool | Purpose | Real or mock |
|---|---|---|
| `pser_tool` | Query PSER vulnerability data | Mock JSON (production: Punjab govt API) |
| `weather_tool` | Fetch weather signals | Mock time series |
| `traffic_tool` | Fetch traffic state | Mock |
| `fcm_tool` | **Send REAL FCM push notifications to stakeholders** | **REAL** (Firebase Cloud Messaging) |
| `tts_tool` | Generate Urdu mosque announcements | **REAL** (Google Cloud TTS `ur-PK-Standard-A`) |
| `credibility_tool` | Score signal credibility | Heuristics + Gemini Flash |
| `deduplicator_tool` | Detect duplicate signals | Real (in-process) |
| `geocode_tool` | Resolve location names to coordinates | Mock with real fallback |
| `travel_time_tool` | Compute resource → crisis travel time | Mock with Google Maps Distance Matrix path documented |
| `dispatch_tool` | Update resource status in SQLite | Real |

### Why Antigravity is NOT used superficially

Antigravity built and orchestrates the entire multi-agent system. Google ADK runs that orchestration at runtime. Every conditional branch, every tool call, every trace event flows through Google-ecosystem primitives. The entire stack is Google-native: Gemini models, ADK orchestration, Cloud Run deployment, Firebase Cloud Messaging for notifications, Cloud TTS for Urdu audio. Zero non-Google dependencies.

Without Antigravity orchestrating the build, this 5-agent + 10-tool + 5-screen mobile app system would not be tractable in 7 days. That's the agentic infrastructure thesis.

---

## 17. COST_LATENCY.md (Required by Rubric, Rarely Done Well)

### 17A. Cost & Latency Per Operation

| Step | Model / Service | Avg latency | Avg cost / call | Tokens (in/out) |
|---|---|---|---|---|
| Observer (credibility + intent) | gemini-2.5-flash via ADK | 0.4s | $0.0003 | ~200/100 |
| Analyst (fusion + PSER lookup) | gemini-2.5-pro via ADK | 1.8s | $0.0021 | ~800/300 |
| Strategist (trade-off reasoning) | gemini-2.5-pro via ADK | 2.1s | $0.0028 | ~1000/400 |
| Operator (msg generation x7 audiences) | gemini-2.5-flash via ADK | 0.5s | $0.0004 | ~300/200 |
| Operator (mosque TTS) | Google Cloud TTS | 0.8s | $0.000004/char | ~200 chars |
| Operator (FCM dispatch) | Firebase Cloud Messaging | 0.2s | **FREE** | n/a |
| Auditor (verification) | gemini-2.5-pro via ADK | 1.6s | $0.0019 | ~600/250 |
| ADK orchestration overhead | Google ADK runtime | 0.3s total | $0 (library) | n/a |

**Per-crisis end-to-end (critical path, Auditor runs parallel):** ~6.1 seconds wall-clock (Observer 0.4 + Analyst 1.8 + Strategist 2.1 + Operator 1.5 + Overhead 0.3), ~$0.0060
**Per-crisis with Auditor on critical path (low confidence route):** ~7.7 seconds wall-clock, ~$0.0079
**Per-signal (Observer only, noise filtered):** ~0.4 seconds, ~$0.0003
**FCM is free at any scale** — production would add WhatsApp Business API via Meta Cloud API for direct citizen messaging at ~$0.05/conversation

### 17B. Baseline Comparison (Non-Agentic vs Agentic)

The baseline is a **simple keyword + rule-based system** that does NOT use agents:
- Scans tweets for keywords ("garmi", "bijli", "heatstroke")
- If keyword count > threshold → fire alert for the matched location
- No credibility scoring, no signal fusion, no trade-off reasoning
- Fixed priority rules: always prioritize highest-population area
- No false alarm detection, no retraction capability

| Metric | Baseline (keyword rules) | Tapish (agentic) |
|---|---|---|
| False positive rate | ~35% (viral tweets trigger alerts) | ~8% (credibility + Auditor catches fakes) |
| Response time (signal → action) | 2 min (instant but dumb) | 6.5 sec (reasoned, coordinated) |
| Multi-crisis handling | First-come-first-served | Mortality-weighted optimization |
| False alarm correction | None (alert stays live) | Retraction + public apology in <15 min |
| Resource waste | High (sends everything everywhere) | Low (constrained allocation with 20% reserve) |
| Side effect detection | None | Detects congestion from own alerts, adapts strategy |

This table goes in the README AND is visualized in the dashboard's BaselineComparison component.

### 17C. Scaling Discussion (10x / 100x)

| Scale | Signals/day | Crises/day | Cost/day | Architecture change needed |
|---|---|---|---|---|
| **Demo (1x)** | 60 mock tweets | 2-3 | $0.02 | None (single server) |
| **Single city production (10x)** | 5,000 signals | 20-30 | $0.75 | Add Redis for signal queue + caching; Gemini batch API for Observer |
| **5-city deployment (50x)** | 25,000 signals | 100-150 | $3.75 | Horizontal scaling: one agent cluster per city; shared Strategist for cross-city resource sharing |
| **National scale (100x)** | 50,000 signals | 300+ | $7.50 | Kafka for signal streaming; dedicated GPU inference for Observer (move off Gemini Flash to fine-tuned model); regional Analyst shards |

**Throughput estimate:** Current architecture handles ~10 signals/second (limited by Gemini Pro latency on Analyst). At 100x, batching Observer calls and sharding Analyst by region maintains <10 second end-to-end per crisis.

**Latency target:** <15 seconds from first signal to first dispatched action at any scale. Current demo achieves 6.5 seconds.

This level of cost honesty wins the "robustness, scalability, cost and latency 10%" slice that nobody else writes about.

---

## 18. The Cuts (What We Intentionally DON'T Build)

State this list in the README. Judges respect knowing-what-you-cut.

**Cuts from original spec (made to keep 7-day scope realistic):**
- **No web admin Resources/Thresholds/Scenarios tabs** — only System Health view. Mobile carries the wow features. → *Production: full admin panel with role-based access*
- **No drone resources** — kept ambulances, generators, water tankers, rescue teams. → *Production: drone integration for damage assessment*
- **No baseline comparison as a full UI** — embedded as a single toggle on the map. → *Production: dedicated A/B analytics view*

**Always-cuts (out of scope by design):**
- **No real Twitter/X API integration** — we use a 60-tweet curated mock dataset. → *Production: Twitter Filtered Stream API or paid social listening tool*
- **No real SMS/WhatsApp dispatch** — BUT we DO send **REAL Firebase Cloud Messaging push notifications** to demonstrate real-world action. 100% Google ecosystem. → *Production: WhatsApp Business API via Meta Cloud API for direct citizen messaging*
- **No authentication** — single-user demo. → *Production: Firebase Auth with role-based access (citizen/operator/admin)*
- **No persistent crisis history beyond session** — SQLite resets per simulation. → *Production: Firestore with multi-region replication*
- **No real LESCO/Rescue 1122 API** — mock endpoints with realistic response shapes. → *Production: signed MOUs and integration with Punjab Safe Cities Authority feeds*
- **No federated multi-city deployment** — Lahore-only. → *Production: Cloud Run multi-region with regional Analyst shards*
- **No production error tracking** — local logs only. → *Production: Google Cloud Logging + Error Reporting*

For each cut, the production-grade replacement is named. Judges see we understand the path to deployment, not just the demo.

---

## 19. Pre-Demo Checklist (Run Day-Of)

- [ ] All 7 scenarios load and run end-to-end without errors (incl. false negative)
- [ ] **Live Signal Inject works on MOBILE** — type a Roman Urdu tweet on the phone, watch full pipeline fire (test 3 different inputs)
- [ ] **REAL FCM push notification arrives on demo phone** during stakeholder dispatch (test 3 times)
- [ ] WebSocket trace stream is smooth on both mobile + web (no lag spikes)
- [ ] Google Maps renders cleanly on both mobile and web (no quota errors)
- [ ] Flutter APK installed on demo phone, connects to Cloud Run backend
- [ ] All 5 mobile screens work: Alerts, Live Map, Inject, Trace Console, Stakeholder Inbox
- [ ] Mosque TTS plays cleanly through laptop speakers (test Google Cloud TTS + fallback)
- [ ] Web admin System Health view loads cleanly
- [ ] Baseline comparison toggle works on mobile
- [ ] Retraction scenario runs cleanly with public apology message
- [ ] Staged alerting scenario shows congestion detection + zone-by-zone rollout
- [ ] **False negative scenario** runs cleanly — Observer retroactively upgrades signal
- [ ] **`antigravity_traces/` folder** contains 7 JSON files — one per scenario, with complete agent trace chains
- [ ] Both demo videos uploaded to YouTube as unlisted (product + Antigravity usage)
- [ ] README links work, GitHub repo public
- [ ] Backup screen recording in case live demo fails
- [ ] Cloud Run backend is warm (hit `/api/simulation/status` to wake it up before demo — Cloud Run cold starts can hurt)
- [ ] Firebase project configured, FCM enabled, `google-services.json` in Flutter app
- [ ] One team member ready to hand the phone to a judge for live Signal Inject during Q&A

---

## 20. The Closing Argument (For the Q&A)

When judges ask "why should this win":

> *"Tapish doesn't just summarize signals. It makes decisions that are normally only made by humans coordinating across five fragmented agencies. The Strategist Agent queries PSER vulnerability data to prioritize the poorest households first — not the loudest complainers. It routes pediatric emergencies to the CM's Maryam Ki Masihaai program. The Auditor catches false positives AND false negatives — it retracts viral misinformation AND retroactively upgrades signals it initially missed. The Operator sends REAL Firebase Cloud Messaging push notifications, plays REAL Urdu mosque announcements through Google Cloud TTS. Five Google ADK agents, thirteen registered tools, one coordinated response — built in seven days using Google Antigravity as the development orchestrator. Every Google primitive, every action observable, every decision traceable. Zero non-Google dependencies. This is what agentic infrastructure for Punjab's current digital reality looks like."*

**If asked "why not just use ChatGPT or a simple workflow?":**
> *"A simple workflow would have escalated the Liberty Market rumor. A simple workflow would have ignored the 'mera AC nahi chal raha' tweet forever. A simple workflow can't justify prioritizing Walled City over Gulberg in a way that survives political scrutiny. Tapish reasons, decides, and adapts. That's the difference between LLM polish and agentic infrastructure."*

---

## END OF PLAN

Antigravity executor: start with Day 1 in section 13. After each day, emit a status report against section 13's "End of day gate" criterion. Surface blockers immediately — do not silently degrade scope. The cuts in section 18 are pre-approved; any additional cuts require explicit sign-off.

**Critical reminders for the executor:**
1. **Google ADK is the runtime orchestrator** — not LangGraph. Install with `pip install google-adk`. All 5 agents are `LlmAgent` instances.
2. **Mobile is the primary deliverable** — web is supplementary. Front-load polish on the Flutter app.
3. **Start the Antigravity Usage screen recording on Day 1 morning** — you need raw footage for Video 2. Don't fake it later.
4. **Firebase project must be set up Day 1** — create project, enable FCM, add `google-services.json` to Flutter, test push notification to your demo phone before writing any agent code.
5. **Test the false-negative scenario at least twice** — most teams will miss this and lose points. Make sure Observer's retroactive upgrade logic actually fires.
6. **Cloud Run cold starts** — warm the backend 5 minutes before demo with `curl /api/simulation/status`. Cold starts can be 8-15 seconds.
7. **If anything slips on Day 5, deploy first, polish later.** A working deployed app beats a polished localhost app every time.
