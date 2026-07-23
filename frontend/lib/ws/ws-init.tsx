"use client";
import { useEffect, useRef } from "react";
import { useWsStore } from "./store";
import type { WsEvent } from "@/lib/api/types.gen";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
const RECONNECT_MS = 3000;

export function WsInit() {
  const { setConnected, apply } = useWsStore();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);

        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data) as WsEvent;
            apply(data);
          } catch {}
        };

        ws.onclose = () => {
          setConnected(false);
          timerRef.current = setTimeout(connect, RECONNECT_MS);
        };

        ws.onerror = () => ws.close();
      } catch {
        timerRef.current = setTimeout(connect, RECONNECT_MS);
      }
    }

    connect();
    return () => {
      wsRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [setConnected, apply]);

  return null;
}
