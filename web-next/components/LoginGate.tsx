"use client";
import { useState, useEffect } from "react";
import { API_BASE_DEFAULT } from "@/lib/constants";

/**
 * Login gate for Tapish Markaz.
 * Calls /api/admin/login to get a signed JWT — credentials never stored client-side.
 */
/** Check JWT validity from localStorage (runs once at mount) */
function _checkStoredJwt(): { authed: boolean; done: boolean } {
  if (typeof window === "undefined") return { authed: false, done: false };
  const jwt = localStorage.getItem("tapish_jwt");
  if (jwt) {
    try {
      const payload = JSON.parse(atob(jwt.split(".")[1]));
      if (payload.exp * 1000 > Date.now()) {
        return { authed: true, done: true };
      }
      // Expired — clear
      localStorage.removeItem("tapish_jwt");
    } catch {
      localStorage.removeItem("tapish_jwt");
    }
  }
  return { authed: false, done: true };
}

export default function LoginGate({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Check stored JWT after first paint (avoids React #418 hydration mismatch
  // and the set-state-in-effect lint rule by using requestAnimationFrame)
  useEffect(() => {
    const id = requestAnimationFrame(() => {
      const { authed: a } = _checkStoredJwt();
      setAuthed(a);
      setHydrated(true);
    });
    return () => cancelAnimationFrame(id);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const apiBase = localStorage.getItem("tapish_api") || API_BASE_DEFAULT;
    const maxRetries = 2;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await fetch(`${apiBase}/api/admin/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        localStorage.setItem("tapish_jwt", data.token);
        setAuthed(true);
        setLoading(false);
        return; // Success
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Login failed";
        const isAuthError = msg.includes("401") || msg.includes("Invalid credentials");
        if (isAuthError || attempt === maxRetries) {
          setError(msg);
          setLoading(false);
          return;
        }
        // Wait before retry on network errors
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  };

  // Don't render until hydrated (prevents flash of login form)
  if (!hydrated) return <div style={{ width: "100vw", height: "100vh", background: "#0a0a0f" }} />;
  if (authed) return <>{children}</>;

  return (
    <div style={{
      width: "100vw", height: "100vh",
      background: "radial-gradient(circle at 50% 30%, #1a0a35, #0a0a0f)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'Inter', sans-serif",
    }}>
      <form
        onSubmit={handleLogin}
        style={{
          width: 380, padding: 40, borderRadius: 20,
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
          backdropFilter: "blur(20px)",
          display: "flex", flexDirection: "column", gap: 20,
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 8 }}>
          <div style={{
            width: 64, height: 64, margin: "0 auto 16px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #7c3aed, #4f46e5)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 40px rgba(124,58,237,0.3)",
          }}>
            <span style={{ fontSize: 28 }}>🔥</span>
          </div>
          <h1 className="font-urdu" style={{
            fontSize: 34, fontWeight: 700, color: "#fff", margin: 0,
          }}>
            تپش مرکز
          </h1>
          <p style={{
            fontSize: 13, color: "rgba(255,255,255,0.4)",
            marginTop: 6, letterSpacing: 2, fontWeight: 500,
          }}>
            TAPISH MARKAZ — CIRO Command Centre
          </p>
        </div>

        {/* Username */}
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username — صارف نام"
          autoComplete="username"
          style={{
            width: "100%", padding: "14px 16px", fontSize: 14,
            background: "rgba(255,255,255,0.06)", color: "#fff",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 12, outline: "none",
          }}
        />

        {/* Password */}
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password — پاس ورڈ"
          autoComplete="current-password"
          style={{
            width: "100%", padding: "14px 16px", fontSize: 14,
            background: "rgba(255,255,255,0.06)", color: "#fff",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 12, outline: "none",
          }}
        />

        {/* Error */}
        {error && (
          <div style={{
            padding: "10px 14px", borderRadius: 8,
            background: "rgba(239,68,68,0.12)",
            border: "1px solid rgba(239,68,68,0.25)",
            color: "#f87171", fontSize: 13,
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%", padding: "14px", fontSize: 15,
            fontWeight: 600, color: "#fff",
            background: loading
              ? "rgba(124,58,237,0.3)"
              : "linear-gradient(135deg, #7c3aed, #6d28d9)",
            border: "none", borderRadius: 12, cursor: "pointer",
            transition: "all 0.2s",
          }}
        >
          {loading ? "Authenticating..." : <><span>Login</span> — <span className="font-urdu">داخل ہوں</span></>}
        </button>

        <p style={{
          textAlign: "center", fontSize: 11,
          color: "rgba(255,255,255,0.2)", marginTop: 8,
        }}>
          Authorised CIRO personnel only
        </p>
      </form>

      <style>{`
        .spinner {
          width: 24px; height: 24px;
          border: 2px solid rgba(255,255,255,0.1);
          border-top-color: #7c3aed;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        input:focus {
          border-color: rgba(124,58,237,0.5) !important;
          box-shadow: 0 0 0 3px rgba(124,58,237,0.1);
        }
        button:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 20px rgba(124,58,237,0.3);
        }
      `}</style>
    </div>
  );
}

/** Logout utility — clears JWT and reloads */
export function logoutMarkaz() {
  localStorage.removeItem("tapish_jwt");
  window.location.reload();
}

/** Get JWT for API calls — sent as Authorization: Bearer header */
export function getAdminToken(): string {
  const jwt = localStorage.getItem("tapish_jwt") || "";
  if (jwt) {
    try {
      const payload = JSON.parse(atob(jwt.split(".")[1]));
      const expiresAt = payload.exp * 1000;
      const now = Date.now();

      // If expired → force re-login
      if (now > expiresAt) {
        localStorage.removeItem("tapish_jwt");
        window.location.reload();
        return "";
      }

      // If within 1 hour of expiry → silently refresh in background
      const oneHour = 60 * 60 * 1000;
      if (expiresAt - now < oneHour && !_refreshing) {
        _refreshInBackground(jwt);
      }
    } catch {
      // Malformed JWT — clear
      localStorage.removeItem("tapish_jwt");
    }
  }
  return jwt;
}

// Prevent concurrent refresh calls
let _refreshing = false;

async function _refreshInBackground(currentJwt: string) {
  _refreshing = true;
  try {
    const apiBase = localStorage.getItem("tapish_api") || "";
    const res = await fetch(`${apiBase}/api/admin/refresh`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${currentJwt}` },
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("tapish_jwt", data.token);
    }
  } catch {
    // Silent fail — current token still valid for up to 1h
  } finally {
    _refreshing = false;
  }
}
