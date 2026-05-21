"use client";
import { useState, useEffect, useRef } from "react";

interface WsOptions {
  path: string;
  baseUrl: string;
  onMessage?: (data: Record<string, unknown>) => void;
}

export function useWebSocket({ path, baseUrl, onMessage }: WsOptions) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { onMessageRef.current = onMessage; });

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      try {
        const wsBase = baseUrl.replace(/^http/, "ws");
        const ws = new WebSocket(`${wsBase}${path}`);
        wsRef.current = ws;

        ws.onopen = () => { if (!cancelled) setConnected(true); };
        ws.onclose = () => {
          if (!cancelled) {
            setConnected(false);
            reconnectTimerRef.current = setTimeout(connect, 3000);
          }
        };
        ws.onerror = () => { if (!cancelled) setConnected(false); };
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            onMessageRef.current?.(data);
          } catch {}
        };
      } catch {}
    }

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [path, baseUrl]);

  return { connected };
}
