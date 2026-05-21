"use client";
import { CRISIS_ICONS } from "@/lib/constants";

interface Crisis { type?: string; primary_location?: string; severity?: string; confidence?: number; status?: string; }

export default function AlertTicker({ crises }: { crises: Crisis[] }) {
  const latest = crises.filter(c => c.status !== "retracted").slice(-3);
  if (!latest.length) return (
    <div className="ticker-bar h-7 flex items-center px-4 overflow-hidden shrink-0">
      <span className="text-[10px] text-white/20">⚠ Waiting for crisis events...</span>
    </div>
  );
  const text = latest.map(c => {
    const e = CRISIS_ICONS[c.type || ""] || "⚠️";
    return `${e} ${(c.type||"").toUpperCase()}: ${c.primary_location || "Lahore"} — Severity: ${c.severity} — Confidence ${((c.confidence||0)*100).toFixed(0)}%`;
  }).join("   ●   ");

  return (
    <div className="ticker-bar h-7 flex items-center overflow-hidden shrink-0">
      <span className="sev-critical text-[9px] ml-2 mr-3 shrink-0">⚠ ALERT</span>
      <div className="overflow-hidden flex-1">
        <div className="ticker-scroll whitespace-nowrap text-[11px] text-[#ff6d00]/80">{text}</div>
      </div>
    </div>
  );
}
