# Migrate Web Dashboard: Vanilla → React (Next.js)

> **Goal**: Replace the vanilla dashboard with React/Next.js, fixing ALL 19 gaps so React is strictly superior.

---

## 🔴 BROKEN — Will 422 on Every Click (2 bugs)

### #35 — Inject API Body Mismatch
- **Vanilla (correct)**: `{ raw_text: text }` → `app.js:499`
- **React (broken)**: `{ content: injectText, source: "twitter" }` → `page.tsx:68`
- **Problem**: `content` ≠ `raw_text`. FastAPI returns 422.
- **Fix**: Change to `{ raw_text: injectText }`

### #36 — Stream Toggle Body Mismatch
- **Vanilla (correct)**: `{ stream: streamName, interval_seconds: 25 }` → `app.js:527`
- **React (broken)**: `{ stream_name: name }` → `page.tsx:83`
- **Problem**: `stream_name` ≠ `stream`, missing `interval_seconds`. FastAPI returns 422.
- **Fix**: Change to `{ stream: name, interval_seconds: 25 }`

---

## 🔴 MAJOR Features Missing (10 items)

### A — Google Maps (crisis markers, resource markers, InfoWindows, geocoding, dark style)
- **Vanilla**: Full implementation — 19 Lahore locations, auto-refresh 15s, click-to-inspect, retracted = purple pin
- **React**: Empty `<div id="gmap">` with gradient placeholder and 🗺️ emoji. No Maps SDK loaded.
- **Fix**: Dynamic Maps SDK loading via `/api/config/maps-key`. Crisis markers (red/orange/yellow/purple). Resource markers (blue/green). InfoWindows with sanitized content. `LAHORE_LOCATIONS` geocoding fallback. Dark theme. Resize handling.

### B — Cold Start Warmup (blocking overlay until backend responds)
- **Vanilla**: Full-screen overlay, Urdu text, spinner, 15-attempt retry loop with status messages, blocks UI
- **React**: One-shot `/api/warmup` fetch, sets `backendWarm=true` even on failure. Tiny amber badge.
- **Fix**: New `<WarmupOverlay>` with Framer Motion. Full-screen dark overlay, spinner, Urdu title, attempt counter ("Attempt 3/15"), 2s retry, blocks UI. Success → fade out. Exhausted → error message.

### C — Crisis Info Panel (API-backed, not WS-only)
- **Vanilla**: Fetches `/api/crises` every 15s. Shows ALL crises with severity colors, confidence %, status, RETRACTED badge. Persists across refresh.
- **React**: Only shows last 5 WS `crisis_detected` events. Ephemeral — page refresh = empty. Never calls `/api/crises`.
- **Fix**: New `<CrisisPanel>` component. Polls `/api/crises`. Full severity cards with all fields. `❌ RETRACTED` badge.

### D — Resource Count Badge
- **Vanilla**: Shows actual count from `/api/resources` ("12 Resources"), polled every 15s
- **React**: Only counts incremental WS `signal_ingested` events. Not real resource count.
- **Fix**: Poll `/api/resources` alongside crises. Show real count in badge.

### E — Map Auto-Refresh Polling
- **Vanilla**: `setInterval(loadMapData, 15000)` polls crises + resources
- **React**: No polling at all. Only WS events.
- **Fix**: `useEffect` with 15s `setInterval` calling `loadMapData()`, cleanup on unmount.

### F — API URL Input (judges can change backend URL)
- **Vanilla**: Visible `<input>` in header, persists to `localStorage`
- **React**: No input. Hardcoded in `constants.ts`. Judge can't point to a different backend.
- **Fix**: Add `<input>` in header. `onChange` updates `apiBase` state + saves to `localStorage`. Read from `localStorage` on mount.

### G — Inject Error Feedback
- **Vanilla**: Checks `res.ok`, parses error detail, shows `alert()` with message
- **React**: `catch {}` — silently swallows all errors. User has no idea inject failed.
- **Fix**: Check `res.ok`. Parse error. Show visible error feedback (toast or inline message).

### H — Alerts WS Drives Map Refresh
- **Vanilla**: `crisis_detected` → `loadMapData()` → markers update immediately
- **React**: No map markers to update. Crisis events only append cards.
- **Fix**: On `crisis_detected` alert, call `loadMapData()` to refresh markers.

### I — LAHORE_LOCATIONS Geocoding Fallback
- **Vanilla**: 19-location dictionary for name → coords when GPS is missing
- **React**: Not present. No geocoding at all.
- **Fix**: Port to `lib/constants.ts`. Use in marker placement.

### J — localStorage Persistence
- **Vanilla**: `updateApiUrl()` saves to `localStorage`. Maps loader reads it.
- **React**: No `localStorage` usage.
- **Fix**: Read `apiBase` from `localStorage` on mount. Save on change.

---

## 🟡 MEDIUM Features Missing / Worse (6 items)

### K — Trace Card Badges (decision, verdict, confidence)
- **Vanilla**: Inline color-coded badges: routing decision (blue), verdict VERIFY/RETRACT (green/red), confidence score
- **React**: Missing entirely. Only shows agent badge, phase, timestamp, content.
- **Fix**: Add conditional badges in `TraceCard` for `decision`, `verdict`, `confidence`.

### L — System Event Colors
- **Vanilla**: `EVENT_COLORS` map gives distinct colors to `routing_decision`, `pipeline_complete`, `pipeline_error`, `auditor_verdict`, `crisis_detected`, `crisis_retracted`
- **React**: Only `AGENT_COLORS`. System events get generic gray `#5c6478`.
- **Fix**: Port `EVENT_COLORS` to `constants.ts`. Use as fallback color in `TraceCard`.

### M — PKT Timezone Display
- **Vanilla**: `formatTime()` forces `timeZone: 'Asia/Karachi'` — always shows PKT
- **React**: `toLocaleTimeString()` — shows user's local timezone. Judge in UTC sees UTC times.
- **Fix**: Add `timeZone: 'Asia/Karachi'` to timestamp formatting in `TraceCard`.

### N — Baseline: Prioritization Row
- **Vanilla**: Has "Prioritization: FIFO queue → PSER × mortality" comparison row
- **React**: Row missing from baseline overlay.
- **Fix**: Add 7th row to both baseline arrays.

### O — Trade-off: Context Closing Line
- **Vanilla**: "Strategist Agent explicitly reasons about this trade-off in every pipeline run."
- **React**: Missing this line.
- **Fix**: Add footnote `<div>` below trade-off data.

### P — ADAPT Phase Color Inconsistency
- **Vanilla**: `adapt: '#0091ea'` (blue)
- **React**: `adapt: '#e040fb'` (magenta) — inconsistent
- **Fix**: Change to `'#0091ea'` in `constants.ts` to match vanilla.

---

## 🔴 BUG Not Ported (1 item)

### #37 — Layout Metadata Says "5-agent"
- **File**: `layout.tsx:9`
- **Current**: "5-agent ADK pipeline"
- **Fix**: Change to "6-agent ADK pipeline"

---

## ✅ BETTER in Next.js (KEEP these)

| Feature | Why it's better |
|---|---|
| Predictor button | "🔮 Predict & Pre-position" calls `/api/predict/preposition`, shows result in overlay. Vanilla has no Predictor UI. |
| Heat map toggle | Radial heat blobs visualization overlay. Vanilla doesn't have this. |
| Framer Motion animations | Trace cards: smooth slide-in/out. Overlays: motion transitions. Vanilla has none. |
| React architecture | TypeScript, proper hooks (`useWebSocket`, `useSound`), component isolation. Vanilla is one 700-line JS file. |
| XSS-safe by default | React JSX auto-escapes. No `escapeHtml()` needed. |
| Tailwind design | Modern glassmorphism, backdrop blur, consistent spacing. |
| Sound effects | Web Audio API tick/chime/alert on pipeline events. |

---

## Execution Priority

| Priority | Items | Why |
|---|---|---|
| **P0 — Demo-breaking** | #35, #36, A, B, F | No inject, no streams, no map, no warmup, no URL change = broken demo |
| **P1 — Functional gaps** | C, D, E, G, H, K | Missing data panels, no error feedback, no polling |
| **P2 — Polish** | I, J, L, M, N, O, P, #37 | Geocoding, localStorage, colors, timezone, text rows, metadata |

## Deployment Plan

1. `cd web-next && npm run build` → static HTML in `/out/`
2. Replace `backend/web/` with `web-next/out/`
3. `gcloud run deploy` → React dashboard at Cloud Run root URL
4. Single URL, no Firebase needed

## Verification Checklist

- [ ] `npm run build` exits 0
- [ ] Root URL returns 200 HTML
- [ ] Google Maps renders (dark theme, Lahore center)
- [ ] Inject signal → 200 response, trace appears
- [ ] Stream toggle → starts/stops without 422
- [ ] Crisis marker appears on map after inject
- [ ] InfoWindow opens on marker click
- [ ] Warmup overlay shows on cold start with retry counter
- [ ] Crisis panel shows severity cards from API
- [ ] Trace cards show decision/verdict/confidence badges
- [ ] Baseline overlay has 7 rows including Prioritization
- [ ] Trade-off overlay has footnote
- [ ] API URL input visible, changes persist to localStorage
- [ ] Timestamps show PKT timezone
- [ ] Sound effects play (tick, chime, alert)
- [ ] Framer Motion animations on all overlays
