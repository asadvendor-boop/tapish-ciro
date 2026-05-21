# Tapish Submission Plan — Mapped to Google Form

---

## GOOGLE FORM FIELDS → ACTION MAP

### 1. Project Overview
**Field:** Text input
**Action:** Write a 2-3 paragraph description of Tapish.
**Status:** ❌ Need to write

---

### 2. Mobile App Link
**Field:** "Upload on any online drive... ONLY SHARE THE LINK"
**Action:** Upload both APKs to a shared drive
**Status:** ✅ APKs built and ready

| APK | Path | Size |
|-----|------|------|
| `TapishNigraan.apk` (Operator) | `/tapish/TapishNigraan.apk` | ~52MB |
| `TapishAwaaz.apk` (Citizen) | `/tapish/TapishAwaaz.apk` | ~52MB |

> [!IMPORTANT]
> Upload BOTH APKs to a shared folder. Include install instructions with:
> - Nigraan login: `nigraan.ops` / `tapish@nigraan2025`
> - Awaaz login: Google Sign-In
> - Backend URL: auto-configured

---

### 3. Optional Web App Link
**Field:** "If web app is deployed... accessible till 25th May 2026"
**Action:** Provide Cloud Run URL
**Status:** ✅ Ready

```
https://tapish-backend-163379998754.asia-south1.run.app
```

> [!WARNING]
> Backend is on 0 min-instances. Cold start takes ~10-15s. Hit `/api/warmup` first. Consider setting `min-instances: 1` before submission (costs ~$0.05/day) to guarantee judges get instant response.

---

### 4. GitHub Repository
**Field:** "Make sure it is accessible and working. ONLY SHARE THE LINK"
**Action:** Create public GitHub repo, push code
**Status:** ❌ Need to create

**What to push:**
```
tapish/
├── backend/           # FastAPI + 6 ADK agents + 20 tools
├── web-next/          # Next.js dashboard (rename to web/)
├── mobile/            # Flutter (Nigraan + Awaaz flavors)
├── antigravity_traces/  # 7 scenario JSON trace files ✅
├── antigravity_artifacts/ # Dev artifacts from Antigravity sessions
├── docs/              # README, ARCHITECTURE, etc.
├── TAPISH_IMPLEMENTATION_PLAN.md
└── README.md
```

**What NOT to push:**
- `build/` folders, `node_modules/`, `.dart_tool/`
- APK files (too large for GitHub, use Drive link)
- `.env` files with API keys
- `web/` (deleted vanilla app)

**Ensure `.gitignore` excludes:** `*.apk`, `build/`, `node_modules/`, `.next/`, `.dart_tool/`, `__pycache__/`, `.env`

---

### 5. Demo Video (3-5 min)
**Field:** "Use this video to showcase overall workflow, how agency has been achieved, how is it innovative"
**Action:** Record and upload
**Status:** ❌ User must record

**Suggested flow (~4 min):**
1. **0:00-0:20** — Hook: "Lahore heatwave. Fragmented response. Tapish coordinates."
2. **0:20-1:10** — Nigraan: Run **Heatwave Auto Demo** → show Trace tab (Observer→Analyst→Strategist→Operator→Auditor)
3. **1:10-1:50** — Run **Power Outage** (2nd crisis) → show trade-off reasoning on Trace
4. **1:50-2:30** — Stakeholder Messages (all 6 tabs) + FCM notification + Urdu TTS audio
5. **2:30-3:00** — Run **False Alarm** → Auditor retraction visible on Trace
6. **3:00-3:30** — Switch to **Awaaz citizen app** → voice report → instant submit → targeted verdict notification
7. **3:30-3:50** — Show Alerts inbox (server-backed) + Map view
8. **3:50-4:10** — Web dashboard (wide map + agent waterfall)
9. **4:10-4:20** — Close: "6 ADK agents, 20 tools, 7 sources. Built with Google Antigravity."

> [!TIP]
> **Before recording:** Hit `/api/warmup` to wake the backend. Run one test scenario to confirm everything works. Then record clean.

---

### 6. Antigravity Usage Video (2-3 min)
**Field:** "Share a screen recording, on how your team has made use of Antigravity"
**Action:** Upload existing video
**Status:** ✅ Done

```
File: AG usage Tapish Video.mp4
Duration: 2:28
Resolution: 1280x720
```

---

### 7. README / Documentation
**Field:** "Explaining overall design, architecture, mock/real APIs, agents, integrations"
**Action:** Write comprehensive README.md
**Status:** ❌ Need to write

**Required sections (15 total):**

| # | Section | Content |
|---|---------|---------|
| 1 | Project description | One paragraph pitch |
| 2 | The problem | Lahore heatwave context, Karachi 2015 stats |
| 3 | System architecture | Mermaid: 5-agent pipeline + conditional routing |
| 4 | Data schemas | Signal, CrisisEvent, Resource, Action, StakeholderMessage |
| 5 | Antigravity usage | Dev-time scaffolding + runtime ADK orchestration |
| 6 | APIs/Tools | 13 tools table (real vs mock) |
| 7 | Setup steps | Copy-paste bash commands |
| 8 | Assumptions | All data synthetic, no real Twitter/LESCO APIs |
| 9 | Privacy/Safety | No PII, mock handles, opt-in TTS |
| 10 | Cost & latency | Per-operation cost table, per-crisis total |
| 11 | Baseline comparison | Agentic vs keyword-rules table |
| 12 | Scalability | 10x/100x scaling discussion |
| 13 | Limitations | Single-region, mock data, no human-in-loop |
| 14 | Demo videos | Included with submission |
| 15 | Synthetic data label | Clear disclaimer |

---

### 8. Antigravity Trace / Logs
**Field:** "Compressed zipped files including all implementation plans, task lists, walkthrough generated during the development for all team members who used Antigravity to vibe code"
**Status:** ⚠️ Files exist, need to collect + zip

> [!IMPORTANT]
> This is NOT pipeline traces — it's **Antigravity development artifacts** from our coding sessions!

**What to include in the zip:**

#### A. Antigravity Dev Artifacts (from our sessions)
| Session | Topic | Artifacts |
|---------|-------|-----------|
| `2f386bc1` | CIRO Dashboard Build | implementation_plan, task, walkthrough |
| `aaaa3f6e` | Mobile Apps + Notifications | implementation_plan, task, walkthrough |
| `ae6a8df3` | Trace Logs Audit | task, walkthrough |
| Current session | Final polish + docs | implementation_plan |

#### B. Pipeline Trace Logs (7 scenario JSONs — already exist ✅)
```
antigravity_traces/
├── scenario_1_baseline.json        (30KB)
├── scenario_2_cascade.json         (30KB)
├── scenario_3_multi_crisis.json    (62KB)
├── scenario_4_false_alarm.json     (19KB)
├── scenario_5_degraded_mode.json   (16KB)
├── scenario_6_staged_alerting.json (39KB)
└── scenario_7_false_negative.json  (179KB)
```

#### C. Master Implementation Plan
```
TAPISH_IMPLEMENTATION_PLAN.md (87KB, 1429 lines)
```

**Action:** Collect all above into `tapish_antigravity_logs.zip`

---

### 9. Additional Supporting Files (Optional, PDF/MD/PPTX)
**Action:** Could include:
- `ARCHITECTURE.md` with Mermaid diagrams
- `COST_LATENCY.md` with detailed analysis
- A 1-page PDF executive summary

---

### 10. Submission Checklist
**Must check all:**
- [x] Mobile App Link
- [ ] Github Repository
- [ ] Demo Video
- [x] Antigravity Usage Video
- [ ] README / Documentation
- [ ] Antigravity Logs
- [ ] Challenge Selected → **Challenge 3: CIRO**

---

## EXECUTION ORDER

| # | Task | Who | Est. Time |
|---|------|-----|-----------|
| 1 | Write `README.md` | Antigravity | ~10 min |
| 2 | Collect AG artifacts → create zip | Antigravity | ~5 min |
| 3 | Create GitHub repo + push code | Antigravity + User | ~10 min |
| 4 | Upload APKs to shared drive | User | ~5 min |
| 5 | Upload AG usage video | User | ~5 min |
| 6 | Record product demo video | User | ~30 min |
| 7 | Upload demo video | User | ~10 min |
| 8 | Set min-instances=1 on Cloud Run | Antigravity | ~2 min |
| 9 | Fill Google Form | User | ~5 min |

**Total: ~1.5 hours** (most is video recording)

> [!CAUTION]
> **Deadline awareness:** Make sure the backend stays warm until May 25. Consider `min-instances: 1` for reliability.
