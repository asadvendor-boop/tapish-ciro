# React Dashboard Migration — Task Tracker

## P0 — Demo-Breaking
- [x] #35 — Fix inject API body (`content` → `raw_text`)
- [x] #36 — Fix stream toggle body (`stream_name` → `stream`, add `interval_seconds`)
- [x] A — Google Maps integration (SDK loading, markers, InfoWindows, dark theme)
- [x] B — Cold start warmup overlay (full-screen, retry loop, blocking)
- [x] F — API URL input in header + localStorage persistence

## P1 — Functional Gaps
- [x] C — Crisis panel from `/api/crises` (severity colors, retracted badges)
- [x] D — Resource count badge from `/api/resources`
- [x] E — Map auto-refresh polling (15s interval)
- [x] G — Inject error feedback (visible error message)
- [x] H — Alerts WS drives map refresh on crisis_detected
- [x] K — Trace card badges (decision, verdict, confidence, event tag)

## P2 — Polish
- [x] I — LAHORE_LOCATIONS geocoding fallback (19 locations)
- [x] J — localStorage persistence for API URL
- [x] L — System event colors (EVENT_COLORS)
- [x] M — PKT timezone display (Asia/Karachi)
- [x] N — Baseline: add Prioritization row
- [x] O — Trade-off: add footnote line
- [x] P — ADAPT phase color → #0091ea
- [x] #37 — Layout meta "5-agent" → "6-agent"

## Deployment
- [x] Build `web-next` → static export (✓ compiled)
- [x] Copy `out/` to `backend/web/`
- [x] Deploy to Cloud Run (rev 31)
- [ ] Visual verification by user
