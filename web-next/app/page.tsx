"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useSound } from "@/hooks/useSound";
import { API_BASE_DEFAULT, CRISIS_ICONS, DARK_MAP_STYLE, LAHORE_CENTER, geocode, escapeHtml } from "@/lib/constants";
import AlertTicker from "@/components/AlertTicker";
import MetricsRibbon from "@/components/MetricsRibbon";
import IncidentsTable from "@/components/IncidentsTable";
import AgentWaterfall from "@/components/AgentWaterfall";
import LiveComms from "@/components/LiveComms";
import LoginGate, { logoutMarkaz, getAdminToken } from "@/components/LoginGate";
import AutoDemoButton from "@/components/AutoDemoButton";

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global { interface Window { initMap?: () => void; google?: any; } }

interface TraceEvent { agent?: string; event?: string; content?: string; action?: string; phase?: string; crisis_id?: string; timestamp?: string; decision?: string; verdict?: string; confidence?: number; [k: string]: unknown; }
interface Crisis { crisis_id?: string; type?: string; primary_location?: string; severity?: string; confidence?: number; status?: string; lat?: number; lng?: number; latitude?: number; longitude?: number; citizen_uid?: string; cascade_risks?: { linked_crisis_type: string; probability: number; reason: string }[]; }

export default function Dashboard() {
  // #J — read API base from localStorage on mount
  const [apiBase, setApiBase] = useState(() => {
    if (typeof window !== "undefined") return localStorage.getItem("tapish_api") || API_BASE_DEFAULT;
    return API_BASE_DEFAULT;
  });
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [filter, setFilter] = useState("all");
  const [injectText, setInjectText] = useState("");
  const [injecting, setInjecting] = useState(false);
  const [baselineOpen, setBaselineOpen] = useState(false);
  const [tradeoffOpen, setTradeoffOpen] = useState(false);
  const [predictionOpen, setPredictionOpen] = useState(false);
  const [prediction, setPrediction] = useState("");
  const [predicting, setPredicting] = useState(false);
  const [heatmapOn] = useState(true);
  const [legendOpen, setLegendOpen] = useState(false);
  const [dataMode, setDataMode] = useState<"live" | "demo">("demo");
  const [modeSwitching, setModeSwitching] = useState(false);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  const { playTick, playChime, playAlert } = useSound();

  // #C, #D — API-backed crisis + resource data
  const [crises, setCrises] = useState<Crisis[]>([]);
  const [resourceCount, setResourceCount] = useState(0);
  const [signalCount, setSignalCount] = useState(0);
  const [lastCrisisTime, setLastCrisisTime] = useState<number>(0);

  // #A — Maps refs
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const heatmapLayerRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // #B — Warmup overlay with retry
  const [warmupState, setWarmupState] = useState<"warming" | "done" | "failed">("warming");
  const [warmupAttempt, setWarmupAttempt] = useState(0);
  const WARMUP_MAX = 15;

  // #E — loadMapData: fetch crises + resources, update markers
  const loadMapData = useCallback(async () => {
    try {
      const [cr, rr] = await Promise.all([
        fetch(`${apiBase}/api/crises`), fetch(`${apiBase}/api/resources`)
      ]);
      if (!cr.ok || !rr.ok) return;
      const [cd, rd] = await Promise.all([cr.json(), rr.json()]);
      const c = cd.crises || []; const r = rd.resources || [];
      setCrises(c); setResourceCount(r.length);

      // Update map markers — only if data actually changed (Bug #20)
      const map = mapRef.current;
      if (!map || !window.google) return;
      const newKey = JSON.stringify(c.map((x: any) => x.id + (x.status||'')).sort()) + '|' + JSON.stringify(r.map((x: any) => x.id + (x.status||'')).sort());
      if ((map as any).__lastMarkerKey === newKey) return;
      (map as any).__lastMarkerKey = newKey;
      markersRef.current.forEach((m: any) => m.setMap(null));
      markersRef.current = [];

      c.forEach((crisis: Crisis) => {
        const pos = geocode(crisis);
        if (!pos) return;
        const sev = crisis.severity || "medium";
        const status = crisis.status || "detected";
        const emoji = CRISIS_ICONS[crisis.type || ""] || "⚠️";
        const iconColor = status === "retracted" ? "purple" : sev === "critical" ? "red" : sev === "high" ? "orange" : "yellow";
        const marker = new window.google.maps.Marker({
          position: pos, map, title: `${emoji} ${crisis.primary_location || ""} — ${crisis.type}`,
          icon: { url: `https://maps.google.com/mapfiles/ms/icons/${iconColor}-dot.png` },
        });
        const info = new window.google.maps.InfoWindow({
          content: `<div style="color:#222;max-width:220px"><strong>${emoji} ${escapeHtml((crisis.type || "").toUpperCase())}</strong><br>📍 ${escapeHtml(crisis.primary_location || "Unknown")}<br>Severity: <strong>${escapeHtml(sev)}</strong><br>Confidence: ${((crisis.confidence || 0) * 100).toFixed(0)}%<br>Status: ${escapeHtml(status)}</div>`,
        });
        marker.addListener("click", () => info.open(map, marker));
        markersRef.current.push(marker);
      });

      r.forEach((res: any) => {
        let loc: any;
        try { loc = typeof res.current_location === "string" ? JSON.parse(res.current_location) : res.current_location; } catch { return; }
        if (!loc?.lat || !loc?.lng) return;
        const marker = new window.google.maps.Marker({
          position: { lat: loc.lat, lng: loc.lng }, map,
          title: `${res.id} — ${res.type} (${res.status})`,
          icon: { url: `https://maps.google.com/mapfiles/ms/icons/${res.status === "dispatched" ? "green" : "blue"}-dot.png` },
        });
        const info = new window.google.maps.InfoWindow({
          content: `<div style="color:#222;max-width:200px"><strong>${escapeHtml(res.id || "")}</strong><br>Type: ${escapeHtml(res.type || "")}<br>Operator: ${escapeHtml(res.operator || "N/A")}<br>Status: <strong>${escapeHtml(res.status || "")}</strong></div>`,
        });
        marker.addListener("click", () => info.open(map, marker));
        markersRef.current.push(marker);
      });
    } catch {}
  }, [apiBase]);

  // Trace WS
  const onTrace = useCallback((data: TraceEvent) => {
    setTraces(prev => [...prev.slice(-199), data]);
    const evt = data.event || "";
    if (evt === "pipeline_start") { playTick(); setPipelineRunning(true); }
    else if (evt === "agent_trace") playTick();
    else if (evt === "crisis_detected") { playChime(); setLastCrisisTime(Date.now()); }
    else if (evt === "crisis_retracted" || evt === "pipeline_error") { playAlert(); setPipelineRunning(false); }
    else if (evt === "pipeline_complete") setPipelineRunning(false);
    if (evt === "signal_ingested") setSignalCount(c => c + 1);
  }, [playTick, playChime, playAlert]);

  const { connected: traceConn } = useWebSocket({ path: "/ws/trace", baseUrl: apiBase, onMessage: onTrace });

  // #H — Alerts WS drives map refresh
  const onAlert = useCallback((data: Record<string, unknown>) => {
    if (data.event === "crisis_detected") { playChime(); loadMapData(); }
    if (data.event === "signal_ingested") { playTick(); }
  }, [playChime, playTick, loadMapData]);

  useWebSocket({ path: "/ws/alerts", baseUrl: apiBase, onMessage: onAlert });



  // #B — Warmup with retry loop
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let succeeded = false;
      for (let i = 1; i <= WARMUP_MAX; i++) {
        if (cancelled) return;
        setWarmupAttempt(i);
        try {
          const r = await fetch(`${apiBase}/api/admin/health`, { signal: AbortSignal.timeout(8000) });
          if (r.ok) { succeeded = true; setWarmupState("done"); break; }
        } catch {}
        await new Promise(r => setTimeout(r, 2000));
      }
      if (!cancelled && !succeeded) setWarmupState("failed");
    })();
    return () => { cancelled = true; };
  }, [apiBase]);

  // #A — Load Maps SDK once warmup is done
  useEffect(() => {
    if (warmupState !== "done") return;
    // Load map data (deferred to avoid synchronous setState in effect)
    setTimeout(loadMapData, 0);
    const iv = setInterval(loadMapData, 15000);

    // Load Google Maps SDK
    if (window.google?.maps) {
      initMap(); return () => { clearInterval(iv); };
    }
    window.initMap = initMap;
    // Guard: don't inject a second script tag (Bug #8), but DO set callback above
    if (document.querySelector('script[src*="maps.googleapis.com"]')) {
      // Script exists but hasn't loaded yet — initMap will fire via callback
      return () => { clearInterval(iv); };
    }
    fetch(`${apiBase}/api/config/maps-key`).then(r => r.json()).then(d => {
      if (!d.key) return;
      if (document.querySelector('script[src*="maps.googleapis.com"]')) return; // race guard
      const s = document.createElement("script");
      s.src = `https://maps.googleapis.com/maps/api/js?key=${d.key}&libraries=visualization&callback=initMap&loading=async`;
      s.async = true; s.defer = true;
      document.body.appendChild(s);
    }).catch(() => {});

    function initMap() {
      if (!mapContainerRef.current) {
        // Container not in DOM yet (login gate transition) — retry shortly
        setTimeout(initMap, 200);
        return;
      }
      // Allow re-creation if map ref is stale
      if (mapRef.current) {
        try { mapRef.current = null; } catch {}
      }
      mapRef.current = new window.google.maps.Map(mapContainerRef.current, {
        center: LAHORE_CENTER, zoom: 12, styles: DARK_MAP_STYLE,
        disableDefaultUI: false, zoomControl: true, mapTypeControl: false, streetViewControl: false, fullscreenControl: true,
      });
      setMapLoaded(true);
      setTimeout(() => { window.google?.maps?.event?.trigger(mapRef.current, "resize"); }, 300);
      loadMapData();
    }
    return () => { clearInterval(iv); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [warmupState, apiBase]);

  // #HEATMAP — sync Google Maps HeatmapLayer with toggle + crisis data
  useEffect(() => {
    if (!mapRef.current || !window.google?.maps?.visualization) return;
    if (heatmapOn && crises.length > 0) {
      // Build weighted data from crisis positions
      const sevWeight: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
      const points = crises
        .filter(c => c.status !== "retracted")
        .map(c => {
          const pos = geocode(c);
          if (!pos) return null;
          return { location: new window.google.maps.LatLng(pos.lat, pos.lng), weight: sevWeight[c.severity || "medium"] || 1 };
        })
        .filter(Boolean);
      if (heatmapLayerRef.current) {
        heatmapLayerRef.current.setMap(null);
      }
      heatmapLayerRef.current = new window.google.maps.visualization.HeatmapLayer({
        data: points,
        map: mapRef.current,
        radius: 35,
        opacity: 0.7,
        gradient: ["rgba(0,0,0,0)", "#00ff88", "#44ff00", "#bbff00", "#ffee00", "#ffaa00", "#ff6600", "#ff2200", "#ff0000"],
      });
    } else {
      if (heatmapLayerRef.current) {
        heatmapLayerRef.current.setMap(null);
        heatmapLayerRef.current = null;
      }
    }
  }, [heatmapOn, crises]);

  // Inject signal
  const [injectError, setInjectError] = useState("");

  const inject = async () => {
    if (!injectText.trim() || injecting) return;
    setInjecting(true); setInjectError("");
    try {
      const res = await fetch(`${apiBase}/api/signals/ingest`, {
        method: "POST", headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getAdminToken()}` },
        body: JSON.stringify({ raw_text: injectText }),
      });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `HTTP ${res.status}`); }
      setInjectText("");
    } catch (e: unknown) { setInjectError(e instanceof Error ? e.message : "Inject failed"); }
    setInjecting(false);
  };

  // Run predictor
  const runPrediction = async () => {
    setPredicting(true); setPredictionOpen(true);
    try {
      const res = await fetch(`${apiBase}/api/predict/preposition`, { method: "POST" });
      const data = await res.json();
      setPrediction(data.prediction || "No prediction available");
    } catch { setPrediction("Prediction failed — check backend connection"); }
    setPredicting(false);
  };



  // PKT clock
  const [clock, setClock] = useState("");
  useEffect(() => {
    const iv = setInterval(() => {
      setClock(new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Asia/Karachi" }));
    }, 1000);
    return () => clearInterval(iv);
  }, []);

  return (
    <LoginGate>
    <div className="flex flex-col h-screen text-[#e8e8f0] overflow-hidden" style={{ background: "var(--bg)", fontFamily: "'JetBrains Mono', monospace" }}>
      {/* Warmup overlay */}
      <AnimatePresence>
        {warmupState === "warming" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] flex flex-col items-center justify-center" style={{ background: "rgba(5,5,16,0.92)", backdropFilter: "blur(20px)" }}>
            <div className="rounded-2xl px-10 py-8 flex flex-col items-center glow-orange" style={{ background: "var(--surface)", border: "1px solid rgba(255,109,0,0.15)" }}>
              <div className="w-14 h-14 border-4 border-[#ff6d00]/20 border-t-[#ff6d00] rounded-full animate-spin mb-6" />
              <div className="font-urdu text-xl font-bold mb-2" style={{ color: "#ff6d00" }}>🔥 تپش</div>
              <div className="font-urdu text-sm mb-3" style={{ color: "rgba(255,255,255,0.6)" }}>بیک اینڈ شروع ہو رہا ہے...</div>
              <div className="text-xs" style={{ color: "#8ec3b9" }}>Attempt {warmupAttempt}/{WARMUP_MAX} — pinging backend...</div>
              <div className="mt-4 w-48 h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.05)" }}>
                <div className="h-full rounded-full" style={{ width: `${(warmupAttempt / WARMUP_MAX) * 100}%`, background: "linear-gradient(to right, #ff6d00, #ff9100)" }} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {warmupState === "failed" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="fixed inset-0 z-[9999] flex flex-col items-center justify-center" style={{ background: "rgba(10,14,26,0.95)" }}>
            <div className="text-lg font-semibold" style={{ color: "#f87171" }}>⚠️ Backend did not respond.</div>
            <div className="text-sm mt-2" style={{ color: "rgba(255,255,255,0.4)" }}>Check the API URL and try refreshing.</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ ROW 1: HEADER ═══ */}
      <header className="header-bar gradient-border-top flex items-center justify-between px-4 py-2 shrink-0 z-20">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold tracking-wide" style={{ color: "#ff6d00", textShadow: "0 0 20px rgba(255,109,0,0.3)" }}>🔥 <span className="font-urdu" style={{ fontSize: 25 }}>تپش مرکز</span> — TAPISH MARKAZ</span>
          <AutoDemoButton apiBase={apiBase} />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold glow-teal" style={{ color: "#00e5ff", textShadow: "0 0 12px rgba(0,229,255,0.3)" }}>PKT {clock}</span>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${traceConn ? 'badge-connected' : 'badge-disconnected'}`}>
            <span className={traceConn ? "live-dot inline-block" : ""}>●</span> {traceConn ? "CONNECTED" : "DISCONNECTED"}
          </span>
          <div
            onClick={async () => {
              if (modeSwitching) return;
              setModeSwitching(true);
              const next = dataMode === "demo" ? "live" : "demo";
              try {
                await fetch(`${apiBase}/api/data-mode`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: next }) });
                setDataMode(next);
              } catch {} finally { setModeSwitching(false); }
            }}
            className="flex items-center rounded-full text-[9px] font-bold relative select-none"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.1)",
              cursor: modeSwitching ? "wait" : "pointer",
              padding: 2,
              width: 90,
              height: 24,
            }}
            title={dataMode === "live" ? "Using real APIs (Open-Meteo, OpenAQ, Google AQI)" : "Using mock JSON data"}
          >
            {/* Sliding pill */}
            <div className="absolute rounded-full transition-all duration-300" style={{
              width: 43,
              height: 20,
              top: 2,
              left: dataMode === "live" ? 45 : 2,
              background: dataMode === "live" ? "rgba(0,200,83,0.25)" : "rgba(255,109,0,0.2)",
              border: `1px solid ${dataMode === "live" ? "#00c85355" : "#ff6d0055"}`,
            }} />
            <span className="relative z-10 flex-1 text-center py-0.5" style={{ color: dataMode === "demo" ? "#ff6d00" : "rgba(255,255,255,0.3)" }}>DEMO</span>
            <span className="relative z-10 flex-1 text-center py-0.5" style={{ color: dataMode === "live" ? "#00c853" : "rgba(255,255,255,0.3)" }}>LIVE</span>
          </div>
          <button onClick={logoutMarkaz} className="px-2 py-0.5 rounded text-[10px] font-bold" style={{ color: "#f87171", background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.2)" }} title="Logout">⏻</button>
        </div>
      </header>

      {/* ═══ ROW 2: ALERT TICKER ═══ */}
      <AlertTicker crises={crises} />

      {/* ═══ ROW 2.5: SOURCES BAR ═══ */}
      <div className="flex items-center gap-4 px-4 py-1.5 text-[10px] shrink-0" style={{ background: "#080a14", borderBottom: "1px solid var(--border)" }}>
        <span style={{ color: "var(--muted)" }} className="font-semibold">📡 Sources:</span>
        <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full" style={{ background: "#34d399" }} /><span style={{ color: "rgba(255,255,255,0.6)" }}>🐦 Twitter</span><span className="px-1 rounded" style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.3)" }}>Manual</span></div>
        <div className="flex items-center gap-1.5"><span className={`w-1.5 h-1.5 rounded-full${pipelineRunning ? " animate-pulse" : ""}`} style={{ background: pipelineRunning ? "#34d399" : "rgba(255,255,255,0.2)" }} /><span style={{ color: pipelineRunning ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.4)" }}>🚑 Rescue 1122</span></div>
        <div className="flex items-center gap-1.5"><span className={`w-1.5 h-1.5 rounded-full${pipelineRunning ? " animate-pulse" : ""}`} style={{ background: pipelineRunning ? "#34d399" : "rgba(255,255,255,0.2)" }} /><span style={{ color: pipelineRunning ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.4)" }}>⚡ LESCO</span></div>
      </div>

      {/* ═══ ROW 3: METRICS RIBBON ═══ */}
      <MetricsRibbon crises={crises.length} resources={resourceCount} signals={signalCount} pipelineActive={traceConn} lastCrisisTime={lastCrisisTime || undefined} avgConfidence={crises.length > 0 ? crises.reduce((sum: number, c: any) => sum + (c.confidence || 0), 0) / crises.length : undefined} />

      {/* ═══ ROW 4: MAIN CONTENT ═══ */}
      <main className="flex flex-1 overflow-hidden" style={{ minHeight: 0 }}>
        {/* LEFT 55%: MAP + INJECT */}
        <section className="relative flex flex-col" style={{ flex: "0 0 55%", minWidth: 0, overflow: "hidden" }}>
          <div className="relative flex-1">
            <div ref={mapContainerRef} className="absolute inset-0" />
            <div className="absolute inset-0 map-vignette z-[1]" />
            {!mapLoaded && (
              <div className="absolute inset-0 flex items-center justify-center" style={{ background: "linear-gradient(135deg, #0d1b2a, #1a1a2e, #060810)", opacity: 0.3 }}><span className="text-6xl">🗺️</span></div>
            )}

            {/* Legend overlay — compact, collapsible */}
            <div className="absolute top-3 left-3 z-10 legend-glass glow-sm" style={{ padding: legendOpen ? 10 : 6 }}>
              <button onClick={() => setLegendOpen(!legendOpen)} className="flex items-center gap-2 w-full text-left" style={{ color: "var(--muted)" }}>
                <span className="text-[9px] font-bold tracking-wider">☰</span>
                {!legendOpen && (
                  <div className="flex items-center gap-1.5">
                    {[["#ef4444"], ["#f97316"], ["#eab308"], ["#3b82f6"], ["#22c55e"]].map(([c], i) => (
                      <span key={i} className="w-2 h-2 rounded-full" style={{ background: c }} />
                    ))}
                  </div>
                )}
                {legendOpen && <span className="text-[9px] font-bold tracking-wider">LEGEND</span>}
              </button>
              {legendOpen && (
                <div className="mt-2">
                  {[["#ef4444", "Critical"], ["#f97316", "High"], ["#eab308", "Medium"], ["#3b82f6", "Resource"], ["#22c55e", "Dispatched"]].map(([c, l]) => (
                    <div key={l} className="flex items-center gap-2 py-0.5">
                      <span className="w-2 h-2 rounded-full" style={{ background: c }} /><span className="text-[9px]" style={{ color: "rgba(255,255,255,0.5)" }}>{l}</span>
                    </div>
                  ))}
                  <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "5px 0" }} />
                  <button onClick={() => { setBaselineOpen(!baselineOpen); setTradeoffOpen(false); }}
                    className="w-full text-left px-2 py-1 rounded text-[9px] font-semibold"
                    style={{ background: baselineOpen ? "rgba(255,109,0,0.15)" : "rgba(255,255,255,0.05)", color: baselineOpen ? "#ff6d00" : "var(--muted)" }}>
                    📊 {baselineOpen ? "Tapish ✓" : "Baseline"}
                  </button>
                  <button onClick={() => { setTradeoffOpen(!tradeoffOpen); setBaselineOpen(false); }}
                    className="w-full text-left px-2 py-1 mt-0.5 rounded text-[9px] font-semibold"
                    style={{ background: tradeoffOpen ? "rgba(170,0,255,0.15)" : "rgba(255,255,255,0.05)", color: tradeoffOpen ? "#aa00ff" : "var(--muted)" }}>
                    ⚖️ {tradeoffOpen ? "Trade-off ✓" : "Trade-off"}
                  </button>
                  <button onClick={runPrediction} disabled={predicting}
                    className="w-full text-left px-2 py-1 mt-0.5 rounded text-[9px] font-semibold"
                    style={{ background: predictionOpen ? "rgba(0,229,255,0.15)" : "rgba(255,255,255,0.05)", color: predictionOpen ? "#00e5ff" : "var(--muted)" }}>
                    🔮 {predicting ? "..." : predictionOpen ? "Predict ✓" : "Predict"}
                  </button>
                </div>
              )}
            </div>

            {/* Baseline Overlay */}
            <AnimatePresence>
              {baselineOpen && (
                <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} className="overlay-panel" style={{ top: 12, left: "50%", transform: "translateX(-50%)" }}>
                  <div className="text-xs font-bold mb-2" style={{ color: "#f87171" }}>❌ Without Tapish (Heuristic Baseline)</div>
                  {[["Response Time", "~23 min"], ["False Positive Rate", "~40%"], ["Channels", "1 (SMS)"], ["Verification", "None"], ["Error Recovery", "None"], ["Language", "English only"], ["Prioritization", "FIFO"]].map(([k, v]) => (
                    <div key={k} className="flex justify-between py-0.5 text-[11px]"><span style={{ color: "rgba(255,255,255,0.5)" }}>{k}</span><span className="font-semibold" style={{ color: "#f87171" }}>{v}</span></div>
                  ))}
                  <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "6px 0" }} />
                  <div className="text-xs font-bold mb-2" style={{ color: "#34d399" }}>✅ With Tapish (Agentic)</div>
                  {[["Response Time", "~7 min (3.3×)"], ["False Positive Rate", "~8% (5×)"], ["Channels", "6 channels"], ["Verification", "Auditor Agent"], ["Error Recovery", "Auto-retract"], ["Language", "Urdu + Roman + EN"], ["Prioritization", "PSER × mortality"]].map(([k, v]) => (
                    <div key={k} className="flex justify-between py-0.5 text-[11px]"><span style={{ color: "rgba(255,255,255,0.5)" }}>{k}</span><span className="font-semibold" style={{ color: "#34d399" }}>{v}</span></div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Trade-off Overlay */}
            <AnimatePresence>
              {tradeoffOpen && (
                <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} className="overlay-panel" style={{ top: 12, left: "50%", transform: "translateX(-50%)", borderColor: "rgba(170,0,255,0.15)" }}>
                  <div className="text-xs font-bold mb-2" style={{ color: "#aa00ff" }}>⚖️ Strategist Trade-off Reasoning</div>
                  {[["Scoring Formula", "PSER × mortality × pop"], ["Walled City PSER", "0.85 (high)"]].map(([k, v]) => (
                    <div key={k} className="flex justify-between py-0.5 text-[11px]"><span style={{ color: "rgba(255,255,255,0.5)" }}>{k}</span><span className="font-semibold" style={{ color: "#34d399" }}>{v}</span></div>
                  ))}
                  <div className="flex justify-between py-0.5 text-[11px]"><span style={{ color: "rgba(255,255,255,0.5)" }}>DHA Phase 5 PSER</span><span className="font-semibold" style={{ color: "#fbbf24" }}>0.25 (low)</span></div>
                  <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "6px 0" }} />
                  <div className="text-[11px] mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>When 2 crises compete for 4 ambulances:</div>
                  <div className="flex justify-between py-0.5 text-[11px]"><span style={{ color: "rgba(255,255,255,0.5)" }}>Walled City</span><span className="font-semibold" style={{ color: "#34d399" }}>3 ambulances (PSER 0.85)</span></div>
                  <div className="flex justify-between py-0.5 text-[11px]"><span style={{ color: "rgba(255,255,255,0.5)" }}>DHA</span><span className="font-semibold" style={{ color: "#fbbf24" }}>1 ambulance (PSER 0.25)</span></div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Prediction Overlay */}
            <AnimatePresence>
              {predictionOpen && (
                <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} className="overlay-panel" style={{ top: 12, left: "50%", transform: "translateX(-50%)", borderColor: "rgba(0,229,255,0.15)", maxWidth: 500, maxHeight: "60vh", overflowY: "auto" }}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-bold" style={{ color: "#00e5ff" }}>🔮 Predictive Pre-Positioning</div>
                    <button onClick={() => setPredictionOpen(false)} className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>✕</button>
                  </div>
                  {predicting ? (
                    <div className="flex items-center gap-2 py-4">
                      <div className="w-4 h-4 border-2 rounded-full animate-spin" style={{ borderColor: "#00e5ff", borderTopColor: "transparent" }} />
                      <span className="text-[11px]" style={{ color: "rgba(255,255,255,0.5)" }}>Analyzing 24hr forecast + PSER data...</span>
                    </div>
                  ) : (
                    <div className="text-[11px] leading-relaxed whitespace-pre-wrap" style={{ color: "rgba(255,255,255,0.6)" }}>{prediction}</div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Heatmap is now rendered via google.maps.visualization.HeatmapLayer — no CSS overlay needed */}
          </div>

          {/* Inject bar below map */}
          <div className="inject-bar flex items-center gap-2 px-3 py-2.5 shrink-0">
            <input value={injectText} onChange={e => { setInjectText(e.target.value); if (injectError) setInjectError(""); }}
              onKeyDown={e => e.key === "Enter" && inject()}
              placeholder="Type a tweet to inject..."
              className="inject-input flex-1 px-3 py-2 rounded-lg text-xs focus:outline-none"
              style={{ color: "#e8e8f0", fontFamily: "JetBrains Mono, monospace" }} />
            <button onClick={inject} disabled={injecting}
              className="inject-btn px-5 py-2 rounded-lg text-xs font-bold"
              style={{ color: "#000", opacity: injecting ? 0.5 : 1 }}>
              {injecting ? "⏳..." : "🔥 INJECT"}
            </button>
            {injectError && <span className="text-[10px] max-w-[150px] truncate flex items-center gap-1" style={{ color: "#f87171" }}>{injectError}<button onClick={() => setInjectError("")} className="hover:opacity-70" style={{ color: "#f87171" }}>✕</button></span>}
          </div>
        </section>

        {/* RIGHT 45%: 3 STACKED PANELS */}
        <section className="right-panel flex flex-col" style={{ flex: "0 0 45%", borderLeft: "1px solid var(--border)" }}>
          {/* Panel 1: Incidents Table — 35% */}
          <div style={{ flex: "0 0 35%", borderBottom: "1px solid var(--border)", overflow: "hidden" }}>
            <IncidentsTable crises={crises} apiBase={apiBase} />
          </div>
          {/* Panel 2: Agent Waterfall — 35% */}
          <div style={{ flex: "0 0 35%", borderBottom: "1px solid var(--border)", overflow: "hidden" }}>
            <AgentWaterfall traces={traces} />
          </div>
          {/* Panel 3: Live Comms — 30% */}
          <div style={{ flex: "1 1 30%", overflow: "hidden" }}>
            <LiveComms traces={traces} filter={filter} setFilter={setFilter} />
          </div>
        </section>
      </main>
    </div>
    </LoginGate>
  );
}
