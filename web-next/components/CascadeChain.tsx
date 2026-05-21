"use client";
import { motion } from "framer-motion";

interface CascadeRisk {
  linked_crisis_type: string;
  probability: number;
  reason: string;
}

const EMOJI_MAP: Record<string, string> = {
  heatwave: "🔥",
  power_outage: "⚡",
  flood: "💧",
  water: "💧",
  infrastructure: "🔧",
  protest: "📢",
  disease_cluster: "🏥",
  accident: "🚨",
};

function probColor(p: number): string {
  if (p >= 0.7) return "#ef4444";   // red
  if (p >= 0.4) return "#f59e0b";   // orange
  return "#22c55e";                  // green
}

export default function CascadeChain({
  crisisType,
  cascadeRisks,
}: {
  crisisType: string;
  cascadeRisks: CascadeRisk[];
}) {
  if (!cascadeRisks || cascadeRisks.length === 0) return null;

  const rootEmoji = EMOJI_MAP[crisisType] || "⚠️";
  const rootLabel = (crisisType || "unknown").replace(/_/g, " ");

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="overflow-hidden"
    >
      <div className="px-3 py-3">
        {/* Header */}
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-[9px] font-bold tracking-widest" style={{ color: "#7c8db5" }}>
            CASCADE RISK CHAIN
          </span>
        </div>

        {/* Root node */}
        <div className="flex flex-col items-center">
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold"
            style={{
              background: "rgba(124,58,237,0.15)",
              border: "1px solid rgba(124,58,237,0.3)",
              color: "#c4b5fd",
            }}
          >
            <span className="text-base">{rootEmoji}</span>
            <span className="capitalize">{rootLabel}</span>
          </div>

          {/* Arrows + children */}
          {cascadeRisks.map((risk, i) => {
            const emoji = EMOJI_MAP[risk.linked_crisis_type] || "⚠️";
            const pct = Math.round(risk.probability * 100);
            const color = probColor(risk.probability);

            return (
              <motion.div
                key={risk.linked_crisis_type + i}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.1, duration: 0.25 }}
                className="flex flex-col items-center w-full"
              >
                {/* Arrow */}
                <svg width="2" height="20" className="my-0.5">
                  <motion.line
                    x1="1" y1="0" x2="1" y2="20"
                    stroke="#5c6080"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ delay: 0.1 + i * 0.1, duration: 0.3 }}
                  />
                </svg>
                <svg width="10" height="6" className="-mt-0.5 mb-0.5">
                  <polygon points="5,6 0,0 10,0" fill="#5c6080" />
                </svg>

                {/* Child node */}
                <div
                  className="flex items-start gap-2 w-full rounded-lg px-3 py-2"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: `1px solid ${color}22`,
                  }}
                >
                  <span className="text-base mt-0.5 shrink-0">{emoji}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold capitalize" style={{ color: "#e2e8f0" }}>
                        {(risk.linked_crisis_type || "").replace(/_/g, " ")}
                      </span>
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                        style={{
                          color,
                          background: `${color}18`,
                        }}
                      >
                        {pct}%
                      </span>
                    </div>
                    <p className="text-[10px] mt-0.5 leading-tight" style={{ color: "#7c8db5" }}>
                      {risk.reason}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
