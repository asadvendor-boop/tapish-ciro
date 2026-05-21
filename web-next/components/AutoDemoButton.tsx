"use client";
import { useState, useRef, useEffect } from "react";
import { getAdminToken } from "./LoginGate";

interface AutoDemoButtonProps {
  apiBase: string;
}

interface Scenario {
  id: string;
  icon: string;
  label: string;
  desc: string;
  source: string;
  geo_hint?: string;
  text: string;
  expected: string; // "dispatch" | "retract"
}

const SCENARIOS: Scenario[] = [
  {
    id: "heatwave",
    icon: "🔥",
    label: "Heatwave",
    desc: "Punjabi tweet — Bhati Gate, 40+ fainted",
    source: "twitter",
    geo_hint: "Bhati Gate, Walled City, Lahore",
    text: "بھاٹی گیٹ والڈ سٹی وچ گرمی نال 40 توں زیادہ لوک بے ہوش، ریسکیو 1122 دا نمبر بند، فوری مدد چاہیدی اے",
    expected: "dispatch",
  },
  {
    id: "flood_false",
    icon: "🌊",
    label: "Flood",
    desc: "Viral panic tweet — no location, no evidence",
    source: "twitter",
    text: "OMG LAHORE IS SINKING!!! Massive flood EVERYWHERE 😱😱🌊 Share before they DELETE this!! #LahoreFloods #Breaking",
    expected: "retract",
  },
  {
    id: "power_outage",
    icon: "⚡",
    label: "Power Outage",
    desc: "LESCO transformer failure — Model Town",
    source: "rescue_1122",
    geo_hint: "Model Town, Lahore",
    text: "EMERGENCY: Complete power failure across Model Town Blocks C and D. LESCO transformer exploded at main feeder. 8 calls reporting elderly trapped in elevators. UPS backup failing in nursing homes.",
    expected: "dispatch",
  },
  {
    id: "accident",
    icon: "🚨",
    label: "Road Accident",
    desc: "Multi-vehicle crash — Gulberg, corroborated",
    source: "twitter",
    geo_hint: "Gulberg III, Lahore",
    text: "Gulberg Main Boulevard par bari accident ho gayi, 3 gariyan aur ek bus takra gayi. Sadak band hai, logon ne khud injured ko utha ke le ja rahe hain. Koi ambulance nahi aa rahi!",
    expected: "dispatch",
  },
  {
    id: "infrastructure_false",
    icon: "🏗️",
    label: "Infrastructure",
    desc: "Forwarded WhatsApp hoax — no specifics",
    source: "twitter",
    text: "🚨🚨 BREAKING!! Building has COLLAPSED somewhere in Lahore!! Many DEAD!! Govt is HIDING this!! Forward to everyone you know!! 🚨🚨 #PrayForLahore #BuildingCollapse",
    expected: "retract",
  },
  {
    id: "protest",
    icon: "📢",
    label: "Protest",
    desc: "Road blockage — Cantt area, traffic jammed",
    source: "twitter",
    geo_hint: "Cantt, Mall Road, Lahore",
    text: "Mall Road Cantt par dharna shuru ho gaya hai, hazaron log sadak par baithe hain. Tamam traffic ruki hui hai, ambulances bhi nahi guzar sakti. Police force deployed but no clearance yet.",
    expected: "dispatch",
  },
  {
    id: "disease_false",
    icon: "🦠",
    label: "Disease Cluster",
    desc: "WhatsApp rumor — unverified cholera panic",
    source: "twitter",
    text: "Guys CHOLERA has SPREAD in Lahore water supply!! 😰😰 My cousin's friend is doctor he said dont drink tap water AT ALL!! Bohat log admit hain hospitals mein! Share karo sab ko batao!! 🏥💀",
    expected: "retract",
  },
];

export default function AutoDemoButton({ apiBase }: AutoDemoButtonProps) {
  const [open, setOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [runningId, setRunningId] = useState("");
  const [resetting, setResetting] = useState(false);
  const [summary, setSummary] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        if (!running) setOpen(false);
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [running]);

  const runScenario = async (scenario: Scenario) => {
    if (running) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setRunningId(scenario.id);
    setSummary("");
    setOpen(false);

    try {
      const res = await fetch(`${apiBase}/api/signals/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAdminToken()}`,
        },
        body: JSON.stringify({
          raw_text: scenario.text,
          source: scenario.source,
          geo_hint: scenario.geo_hint || null,
        }),
        signal: controller.signal,
      });
      const data = await res.json();
      const result = data.result;
      if (result?.pipeline_status === "complete") {
        const verdict = result.auditor_verdict || "—";
        const dispatched = result.dispatch_executed;
        setSummary(
          dispatched
            ? `✅ ${scenario.icon} Dispatched · ${(result.confidence * 100).toFixed(0)}% conf`
            : verdict === "retract"
            ? `🚫 ${scenario.icon} Retracted — false alarm caught`
            : `⚠️ ${scenario.icon} Verdict: ${verdict}`
        );
      } else if (result?.pipeline_status === "error") {
        setSummary(`❌ Error: ${result.error?.slice(0, 60)}`);
      }
      setTimeout(() => setSummary(""), 12000);
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") {
        // User stopped
      } else {
        console.error("Scenario error:", e);
        setSummary("❌ Network error");
        setTimeout(() => setSummary(""), 8000);
      }
    } finally {
      setRunning(false);
      setRunningId("");
      abortRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setRunning(false);
    setRunningId("");
    setSummary("⏹ Stopped");
    setTimeout(() => setSummary(""), 5000);
  };

  const handleReset = async () => {
    setResetting(true);
    setSummary("");
    try {
      await fetch(`${apiBase}/api/simulation/reset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAdminToken()}`,
        },
      });
      setSummary("🔄 Data cleared");
      setTimeout(() => window.location.reload(), 500);
    } catch {
      setSummary("❌ Reset failed");
      setTimeout(() => setSummary(""), 5000);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="flex items-center gap-2" ref={dropdownRef}>
      {/* Main button: dropdown trigger OR stop */}
      {running ? (
        <button
          onClick={handleStop}
          style={{
            padding: "8px 16px",
            fontSize: 13,
            fontWeight: 600,
            color: "#f87171",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            whiteSpace: "nowrap" as const,
          }}
        >
          <span className="demo-spinner" />
          ⏹ Stop
        </button>
      ) : (
        <div className="relative">
          <button
            onClick={() => setOpen(!open)}
            style={{
              padding: "8px 16px",
              fontSize: 13,
              fontWeight: 600,
              color: "#a78bfa",
              background: "rgba(124,58,237,0.12)",
              border: "1px solid rgba(124,58,237,0.3)",
              borderRadius: 8,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.2s",
              whiteSpace: "nowrap" as const,
            }}
          >
            ▶ Auto Demo
            <span style={{ fontSize: 10, opacity: 0.6 }}>▾</span>
          </button>

          {/* Dropdown */}
          {open && (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                left: 0,
                minWidth: 320,
                background: "#0f1225",
                border: "1px solid rgba(124,58,237,0.3)",
                borderRadius: 10,
                boxShadow: "0 12px 40px rgba(0,0,0,0.6)",
                zIndex: 999,
                padding: "6px 0",
                backdropFilter: "blur(20px)",
              }}
            >
              <div
                style={{
                  padding: "6px 14px 8px",
                  fontSize: 9,
                  fontWeight: 700,
                  color: "rgba(255,255,255,0.3)",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                Select Scenario
              </div>
              {SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => runScenario(s)}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    width: "100%",
                    padding: "8px 14px",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) =>
                    ((e.target as HTMLElement).style.background =
                      "rgba(124,58,237,0.12)")
                  }
                  onMouseLeave={(e) =>
                    ((e.target as HTMLElement).style.background = "transparent")
                  }
                >
                  <span style={{ fontSize: 18, lineHeight: 1 }}>{s.icon}</span>
                  <div>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#e0e0e0",
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      {s.label}
                      {s.expected === "retract" && (
                        <span
                          style={{
                            fontSize: 8,
                            padding: "1px 5px",
                            borderRadius: 4,
                            background: "rgba(239,68,68,0.15)",
                            color: "#f87171",
                            fontWeight: 700,
                          }}
                        >
                          FALSE ALARM
                        </span>
                      )}
                      <span
                        style={{
                          fontSize: 8,
                          padding: "1px 5px",
                          borderRadius: 4,
                          background:
                            s.source === "rescue_1122"
                              ? "rgba(0,200,83,0.12)"
                              : "rgba(0,229,255,0.12)",
                          color:
                            s.source === "rescue_1122"
                              ? "#00c853"
                              : "#00e5ff",
                          fontWeight: 600,
                        }}
                      >
                        {s.source === "rescue_1122" ? "Rescue 1122" : "Twitter"}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "rgba(255,255,255,0.35)",
                        marginTop: 2,
                      }}
                    >
                      {s.desc}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reset button */}
      <button
        onClick={handleReset}
        disabled={resetting || running}
        style={{
          padding: "8px 10px",
          fontSize: 12,
          fontWeight: 600,
          color:
            resetting || running
              ? "rgba(255,255,255,0.2)"
              : "rgba(255,255,255,0.5)",
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 8,
          cursor: resetting || running ? "not-allowed" : "pointer",
          transition: "all 0.2s",
          whiteSpace: "nowrap" as const,
        }}
        title="Clear all data — clean slate"
      >
        {resetting ? "..." : "↺ Reset"}
      </button>

      {/* Summary badge */}
      {summary && (
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded"
          style={{
            background: summary.startsWith("✅")
              ? "rgba(16,185,129,0.15)"
              : summary.startsWith("🔄")
              ? "rgba(0,229,255,0.15)"
              : summary.startsWith("🚫")
              ? "rgba(168,85,247,0.15)"
              : summary.startsWith("⏹")
              ? "rgba(255,255,255,0.08)"
              : "rgba(239,68,68,0.15)",
            color: summary.startsWith("✅")
              ? "#34d399"
              : summary.startsWith("🔄")
              ? "#00e5ff"
              : summary.startsWith("🚫")
              ? "#c084fc"
              : summary.startsWith("⏹")
              ? "rgba(255,255,255,0.5)"
              : "#f87171",
          }}
        >
          {summary}
        </span>
      )}

      <style>{`
        .demo-spinner {
          width: 14px;
          height: 14px;
          border: 2px solid rgba(167, 139, 250, 0.2);
          border-top-color: #a78bfa;
          border-radius: 50%;
          animation: demospin 0.6s linear infinite;
          display: inline-block;
        }
        @keyframes demospin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
