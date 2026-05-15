import { useEffect, useRef } from "react";

type WebSocketEventHandler = (event: unknown) => void;

interface UseWebSocketOptions {
  sessionId: string;
  token: string;
  onEvent: WebSocketEventHandler;
  enabled?: boolean;
}

export function useWebSocket({
  sessionId,
  token,
  onEvent,
  enabled = true,
}: UseWebSocketOptions) {
  const retries = useRef(0);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled || !sessionId || !token) {
      return;
    }

    let socket: WebSocket | null = null;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const host = window.location.host;
      const url = `${proto}://${host}/ws/${sessionId}?token=${encodeURIComponent(token)}`;
      socket = new WebSocket(url);

      socket.onmessage = (message) => {
        try {
          onEventRef.current(JSON.parse(message.data));
        } catch {
          onEventRef.current(message.data);
        }
      };

      socket.onopen = () => {
        retries.current = 0;
      };

      socket.onclose = () => {
        if (cancelled) {
          return;
        }
        const delayMs = Math.min(1000 * 2 ** retries.current, 15000);
        retries.current += 1;
        reconnectTimer = setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [enabled, sessionId, token]);
}
