"use client";
import { useState, useEffect, useMemo } from "react";
import { AGENT_COLORS } from "@/lib/constants";

interface TraceEvent { agent?: string; event?: string; step?: string; reasoning?: string; content?: string; timestamp?: string; [k: string]: unknown; }

const AGENTS = ["observer", "analyst", "strategist", "operator", "auditor"];
const AGENT_EMOJIS: Record<string, string> = {
  observer: "👁", analyst: "🧠", strategist: "⚖️", operator: "⚡", auditor: "✅"
};

type AgentStatus = "RETRACTED" | "VERIFIED" | "COMPLETE" | "PROCESSING" | "WAITING";

const STATUS_STYLE: Record<AgentStatus, { bg: string; color: string; glow?: string }> = {
  RETRACTED: { bg: "rgba(239,68,68,0.15)",  color: "#ef4444", glow: "0 0 6px rgba(239,68,68,0.4)" },
  VERIFIED:  { bg: "rgba(34,197,94,0.15)",  color: "#22c55e", glow: "0 0 6px rgba(34,197,94,0.4)" },
  COMPLETE:  { bg: "rgba(0,229,255,0.12)",  color: "#00e5ff" },
  PROCESSING:{ bg: "rgba(251,191,36,0.15)", color: "#fbbf24", glow: "0 0 6px rgba(251,191,36,0.3)" },
  WAITING:   { bg: "rgba(92,100,120,0.2)",  color: "#5c6478" },
};

function deriveStatus(agent: string, traces: TraceEvent[], now: number): AgentStatus {
  // Get all traces for this agent in the last 10 minutes, sorted newest first
  const recent = traces
    .filter(t => (t.agent || "").toLowerCase() === agent && t.timestamp)
    .filter(t => now - new Date(t.timestamp as string).getTime() < 10 * 60 * 1000)
    .sort((a, b) => new Date(b.timestamp as string).getTime() - new Date(a.timestamp as string).getTime());

  if (recent.length === 0) return "WAITING";

  const latest = recent[0];
  // WS events use `content`, Firestore/REST traces use `reasoning` — check both
  const textToSearch = ((latest.reasoning || "") + " " + (latest.content || "")).toLowerCase();
  const step = (latest.step || "").toLowerCase();

  // Check for retraction first — highest priority badge
  if (textToSearch.includes("retract_alert") || textToSearch.includes('"verdict": "retract"')) return "RETRACTED";
  // Check for verify verdict
  if (textToSearch.includes('"verdict": "verify"') || textToSearch.includes("verify_crisis")) return "VERIFIED";
  // Completed output
  if (step === "agent_output") return "COMPLETE";
  // Mid-processing
  if (step === "tool_call" || step === "tool_result") return "PROCESSING";
  // Has trace but unclear — treat as complete
  return "COMPLETE";
}

export default function AgentWaterfall({ traces }: { traces: TraceEvent[] }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  const { agentBlocks, windowStart, windowMs } = useMemo(() => {
    const windowMs = 10 * 60 * 1000;
    const agentBlocks: Record<string, { start: number; end: number }[]> = {};
    AGENTS.forEach(a => { agentBlocks[a] = []; });

    traces.forEach(t => {
      const agent = (t.agent || "").toLowerCase();
      if (!AGENTS.includes(agent) || !t.timestamp) return;
      const ts = new Date(t.timestamp as string).getTime();
      if (isNaN(ts) || ts < now - windowMs) return;
      const blocks = agentBlocks[agent];
      const last = blocks[blocks.length - 1];
      if (last && ts - last.end < 15000) { last.end = ts; }
      else { blocks.push({ start: ts, end: ts + 3000 }); }
    });

    return { agentBlocks, windowStart: now - windowMs, windowMs };
  }, [traces, now]);

  // Find handoff connections: when one agent's block ends and next agent starts
  const connections: { fromAgent: number; toAgent: number; fromPct: number; toPct: number }[] = [];
  for (let i = 0; i < AGENTS.length - 1; i++) {
    const fromBlocks = agentBlocks[AGENTS[i]];
    const toBlocks = agentBlocks[AGENTS[i + 1]];
    if (!fromBlocks.length || !toBlocks.length) continue;
    for (const fb of fromBlocks) {
      for (const tb of toBlocks) {
        if (tb.start >= fb.start && tb.start - fb.end < 30000) {
          const fromPct = ((fb.end - windowStart) / windowMs) * 100;
          const toPct = ((tb.start - windowStart) / windowMs) * 100;
          connections.push({ fromAgent: i, toAgent: i + 1, fromPct: Math.min(98, Math.max(2, fromPct)), toPct: Math.min(98, Math.max(2, toPct)) });
          break;
        }
      }
    }
  }

  // Count active agents (have blocks in last 30s)
  const activeCount = AGENTS.filter(a => agentBlocks[a].some(b => now - b.end < 30000)).length;

  return (
    <div className="flex flex-col h-full">
      <div className="panel-hdr">
        <h3>AGENT WATERFALL</h3>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: "rgba(0,229,255,0.12)", color: "#00e5ff" }}>
              {activeCount} active
            </span>
          )}
          <span className="text-[9px]" style={{ color: "var(--muted)" }}>10m window</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 relative">
        {/* Time axis */}
        <div className="flex justify-between mb-2" style={{ marginLeft: 114 }}>
          {[0, 2, 4, 6, 8, 10].map(m => (
            <span key={m} className="text-[8px]" style={{ color: "var(--muted)" }}>{m}m</span>
          ))}
        </div>

        {/* Agent rows */}
        {AGENTS.map((agent) => {
          const color = AGENT_COLORS[agent] || "#5c6478";
          const blocks = agentBlocks[agent];
          const isActive = blocks.some(b => now - b.end < 30000);
          const status = deriveStatus(agent, traces, now);
          const statusStyle = STATUS_STYLE[status];
          return (
            <div key={agent} className="wf-row" style={{ marginBottom: 2 }}>
              <div className="wf-label capitalize" style={{ color: isActive ? color : undefined }}>
                <span className="mr-1">{AGENT_EMOJIS[agent]}</span>
                <span style={{ flexShrink: 0 }}>{agent}</span>
                {/* Status badge — stolen from Stitch, powered by real trace data */}
                <span style={{
                  marginLeft: 4,
                  fontSize: 7,
                  fontWeight: 700,
                  letterSpacing: "0.06em",
                  padding: "1px 4px",
                  borderRadius: 3,
                  background: statusStyle.bg,
                  color: statusStyle.color,
                  boxShadow: statusStyle.glow,
                  flexShrink: 0,
                  lineHeight: "14px",
                  ...(status === "PROCESSING" ? { animation: "pulse 1.2s ease-in-out infinite" } : {}),
                }}>
                  {status}
                </span>
              </div>
              <div className="wf-track">
                {blocks.map((b, i) => {
                  const leftPct = ((b.start - windowStart) / windowMs) * 100;
                  const widthPct = Math.max(3, ((b.end - b.start) / windowMs) * 100);
                  return (
                    <div key={i} className="wf-block" style={{
                      left: `${Math.max(0, leftPct)}%`,
                      width: `${widthPct}%`,
                      background: status === "RETRACTED"
                        ? `linear-gradient(135deg, #ef444488, #ef444455)`
                        : `linear-gradient(135deg, ${color}, ${color}aa)`,
                      boxShadow: status === "RETRACTED"
                        ? "0 0 8px rgba(239,68,68,0.3)"
                        : `0 0 10px ${color}44`,
                      opacity: status === "RETRACTED" ? 0.7 : 1,
                    }}>
                      {/* Arrow tip on right edge */}
                      <div style={{
                        position: "absolute", right: -5, top: "50%", transform: "translateY(-50%)",
                        width: 0, height: 0,
                        borderTop: "5px solid transparent", borderBottom: "5px solid transparent",
                        borderLeft: `6px solid ${status === "RETRACTED" ? "#ef4444" : color}`,
                      }} />
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* SVG flow arrows connecting agents */}
        {connections.length > 0 && (
          <svg className="absolute pointer-events-none" style={{ top: 28, left: 114, right: 0, bottom: 0, width: "calc(100% - 122px)", height: AGENTS.length * 26 + 4 }} preserveAspectRatio="none">
            {connections.map((c, i) => {
              const x1 = `${c.fromPct}%`;
              const x2 = `${c.toPct}%`;
              const y1 = c.fromAgent * 26 + 13;
              const y2 = c.toAgent * 26 + 13;
              const midY = (y1 + y2) / 2;
              const agentColor = AGENT_COLORS[AGENTS[c.toAgent]] || "#5c6478";
              return (
                <g key={i}>
                  <path
                    d={`M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`}
                    fill="none"
                    stroke={agentColor}
                    strokeWidth="1.5"
                    strokeOpacity="0.4"
                    strokeDasharray="4,3"
                  />
                  {/* Arrow head */}
                  <circle cx={x2} cy={y2} r="3" fill={agentColor} fillOpacity="0.6" />
                </g>
              );
            })}
          </svg>
        )}

        {traces.length === 0 && (
          <div className="text-[10px] text-center mt-4" style={{ color: "var(--muted)" }}>
            Inject a signal to see pipeline activity
          </div>
        )}
      </div>
    </div>
  );
}
