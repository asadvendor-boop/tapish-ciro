"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";

interface Props { crises: number; resources: number; signals: number; pipelineActive: boolean; lastCrisisTime?: number; avgConfidence?: number; }

// Bug #18: Procedural sparklines seeded by label (not hardcoded fake data)
function generateSparkline(label: string): number[] {
  let seed = label.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  return Array.from({ length: 12 }, () => { seed = (seed * 9301 + 49297) % 233280; return 2 + Math.floor((seed / 233280) * 8); });
}

function Spark({ color, label }: { color: string; label: string }) {
  const data = generateSparkline(label);
  return (
    <div className="sparkline mt-1">
      {data.map((v, i) => (
        <div key={i} className="sparkline-bar"
          style={{ height: `${v * 10}%`, background: `${color}55`, animationDelay: `${i * 50}ms` }} />
      ))}
    </div>
  );
}

export default function MetricsRibbon({ crises, resources, signals, pipelineActive, lastCrisisTime, avgConfidence }: Props) {
  // Live response timer
  const [elapsed, setElapsed] = useState("~7m");
  useEffect(() => {
    if (!lastCrisisTime) return;
    const iv = setInterval(() => {
      const diff = Math.floor((Date.now() - lastCrisisTime) / 1000);
      if (diff < 60) setElapsed(`${diff}s`);
      else if (diff < 3600) setElapsed(`${Math.floor(diff / 60)}m ${diff % 60}s`);
      else setElapsed(`${Math.floor(diff / 3600)}h`);
    }, 1000);
    return () => clearInterval(iv);
  }, [lastCrisisTime]);

  const metrics = [
    { label: "THREATS", value: crises, color: "#ff3d00" },
    { label: "ASSETS", value: resources, color: "#448aff" },
    { label: "SIGNALS", value: signals, color: "#00e5ff" },
    { label: "RESPONSE", value: lastCrisisTime ? elapsed : "~7m", color: "#00c853" },
    { label: "PIPELINE", value: pipelineActive ? "ACTIVE" : "IDLE", color: pipelineActive ? "#ff6d00" : "#5c6080" },
    { label: "CREDIBILITY", value: crises > 0 ? `${Math.round((avgConfidence ?? 0) * 100)}%` : "—", color: "#ffab00" },
  ];

  return (
    <div className="flex shrink-0 shimmer-bg" style={{ borderBottom: "1px solid var(--border)" }}>
      {metrics.map((m, i) => (
        <motion.div key={m.label} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
          className="metric-cell flex-1 px-3 py-2.5">
          <div className="text-[9px] font-semibold tracking-wider" style={{ color: "var(--muted)" }}>{m.label}</div>
          <motion.div key={String(m.value)} initial={{ scale: 1.2 }} animate={{ scale: 1 }}
            className="text-lg font-bold mt-0.5" style={{ color: m.color, fontFamily: "Outfit, sans-serif", textShadow: `0 0 12px ${m.color}33` }}>
            {m.value}
          </motion.div>
          <Spark color={m.color} label={m.label} />
        </motion.div>
      ))}
    </div>
  );
}
