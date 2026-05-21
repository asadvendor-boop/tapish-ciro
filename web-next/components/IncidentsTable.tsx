"use client";
import { useState, Fragment } from "react";
import { AnimatePresence } from "framer-motion";
import { CRISIS_ICONS } from "@/lib/constants";
import { getAdminToken } from "./LoginGate";
import CascadeChain from "./CascadeChain";

interface CascadeRisk {
  linked_crisis_type: string;
  probability: number;
  reason: string;
}

interface Crisis {
  crisis_id?: string;
  type?: string;
  primary_location?: string;
  severity?: string;
  confidence?: number;
  status?: string;
  citizen_uid?: string;
  cascade_risks?: CascadeRisk[];
}

const sevClass: Record<string, string> = {
  critical: "sev-critical",
  high: "sev-high",
  medium: "sev-medium",
  low: "sev-low",
};

export default function IncidentsTable({
  crises,
  apiBase,
}: {
  crises: Crisis[];
  apiBase: string;
}) {
  const [banning, setBanning] = useState<string | null>(null);
  const [banned, setBanned] = useState<Set<string>>(new Set());
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleBan = async (uid: string) => {
    if (!confirm(`Ban citizen ${uid.substring(0, 8)}...? They will be unable to submit reports.`)) return;
    setBanning(uid);
    try {
      await fetch(`${apiBase}/api/citizens/${uid}/ban`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAdminToken()}`,
        },
        body: JSON.stringify({ banned: true }),
      });
      setBanned((prev) => new Set([...prev, uid]));
    } catch (e) {
      console.error("Ban failed:", e);
    } finally {
      setBanning(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="panel-hdr">
        <h3>INCIDENTS</h3>
        <span className="text-[9px] text-[#5c6080]">{crises.length} total</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {crises.length === 0 ? (
          <div className="text-[11px] text-[#5c6080] p-4 text-center">
            No incidents detected
          </div>
        ) : (
          <table className="incident-table">
            <thead>
              <tr>
                <th></th>
                <th>Type</th>
                <th>Location</th>
                <th>Severity</th>
                <th>Conf%</th>
                <th>Status</th>
                <th>Reporter</th>
              </tr>
            </thead>
            <tbody>
              {crises.map((c, i) => {
                const rowId = c.crisis_id || String(i);
                const isExpanded = expandedId === rowId;
                const hasCascade = c.cascade_risks && c.cascade_risks.length > 0;
                return (
                  <Fragment key={rowId}>
                    <tr
                      onClick={() => hasCascade && setExpandedId(isExpanded ? null : rowId)}
                      style={{ cursor: hasCascade ? "pointer" : "default" }}
                      className={isExpanded ? "bg-white/[0.03]" : ""}
                    >
                      <td>{CRISIS_ICONS[c.type || ""] || "⚠️"}</td>
                      <td className="capitalize">
                        {(c.type || "unknown").replace(/_/g, " ")}
                        {hasCascade && (
                          <span
                            className="ml-1 text-[8px] align-middle"
                            style={{ color: "#f59e0b" }}
                            title="Has cascade risks"
                          >
                            ⛓
                          </span>
                        )}
                      </td>
                      <td className="text-white/50">{c.primary_location || "—"}</td>
                      <td>
                        <span className={sevClass[c.severity || "medium"] || "sev-medium"}>
                          {c.severity}
                        </span>
                      </td>
                      <td className="text-white/60">
                        {((c.confidence || 0) * 100).toFixed(0)}%
                      </td>
                      <td className={c.status === "retracted" ? "text-purple-400" : "text-emerald-400"}>
                        {c.status || "detected"}
                      </td>
                      <td>
                        {c.citizen_uid ? (
                          banned.has(c.citizen_uid) ? (
                            <span style={{ color: "#f87171", fontSize: 10 }}>🚫 BANNED</span>
                          ) : (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleBan(c.citizen_uid!); }}
                              disabled={banning === c.citizen_uid}
                              style={{
                                fontSize: 9,
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: "rgba(248,113,113,0.1)",
                                border: "1px solid rgba(248,113,113,0.2)",
                                color: "#f87171",
                                cursor: "pointer",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {banning === c.citizen_uid ? "..." : "🚫 Ban"}
                            </button>
                          )
                        ) : (
                          <span style={{ color: "#5c6080", fontSize: 10 }}>—</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && hasCascade && (
                      <tr key={`${rowId}-cascade`}>
                        <td colSpan={7} className="p-0" style={{ background: "rgba(124,58,237,0.04)" }}>
                          <AnimatePresence>
                            <CascadeChain
                              crisisType={c.type || ""}
                              cascadeRisks={c.cascade_risks!}
                            />
                          </AnimatePresence>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
