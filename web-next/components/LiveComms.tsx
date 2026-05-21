"use client";
import { useRef, useEffect } from "react";
import { AGENT_COLORS, EVENT_COLORS, formatTimePKT } from "@/lib/constants";

interface TraceEvent { agent?: string; event?: string; content?: string; action?: string; timestamp?: string; decision?: string; verdict?: string; confidence?: number; crisis_id?: string; [k: string]: unknown; }

export default function LiveComms({ traces, filter, setFilter }: { traces: TraceEvent[]; filter: string; setFilter: (f: string) => void }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [traces]);

  const agents = ["all", "observer", "analyst", "strategist", "operator", "auditor", "predictor"];
  const filtered = filter === "all" ? traces : traces.filter(t => (t.agent || "").toLowerCase() === filter);

  return (
    <div className="flex flex-col h-full">
      <div className="panel-hdr">
        <h3>LIVE COMMS</h3>
        <div className="flex gap-1">
          {agents.map(a => (
            <button key={a} onClick={() => setFilter(a)}
              className={`px-1.5 py-0.5 rounded text-[8px] font-semibold transition-all capitalize ${filter === a ? "text-black" : "bg-white/5 text-[#5c6080] hover:text-white/60"}`}
              style={filter === a ? { background: a === "all" ? "#ff6d00" : (AGENT_COLORS[a] || "#ff6d00") } : {}}>
              {a === "all" ? "ALL" : a.slice(0, 3).toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-1" style={{ fontFamily: "JetBrains Mono, monospace" }}>
        {filtered.slice(-100).map((t, i) => {
          const agent = (t.agent || "").toLowerCase();
          const event = t.event || "";
          const color = agent ? (AGENT_COLORS[agent] || "#5c6478") : (EVENT_COLORS[event] || "#5c6478");
          const msg = t.content || t.action || event || "";
          const ts = t.timestamp ? formatTimePKT(t.timestamp as string) : "";
          return (
            <div key={i} className="comms-line">
              {agent && <span className="comms-tag" style={{ background: `${color}22`, color }}>[{agent.toUpperCase()}]</span>}
              {!agent && event && <span className="comms-tag" style={{ background: `${color}22`, color }}>[{event.toUpperCase().slice(0,12)}]</span>}
              <span className="comms-ts">{ts}</span>
              <span className="comms-msg">{String(msg).substring(0, 120)}</span>
              {t.verdict && <span className="text-[9px] px-1 rounded ml-1" style={{ background: t.verdict === "retract" ? "#ff3d001f" : "#00c8531f", color: t.verdict === "retract" ? "#ff3d00" : "#00c853" }}>{t.verdict}</span>}
              {t.decision && <span className="text-[9px] px-1 rounded ml-1" style={{ background: "#0091ea1f", color: "#0091ea" }}>{t.decision}</span>}
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
