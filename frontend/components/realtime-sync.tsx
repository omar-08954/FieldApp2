"use client";

import { QueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiBase } from "@/lib/api";
import { token } from "@/lib/auth";

const invalidatedQueries = ["summary", "tasks", "assignments", "notifications", "import-reviews", "users", "materials", "daily-reports"];

function getWebSocketEndpoint(): string | null {
  try {
    const apiUrl = new URL(apiBase, window.location.origin);
    apiUrl.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${apiUrl.toString().replace(/\/$/, "")}/ws/events`;
  } catch (error) {
    console.error("Invalid API base URL for realtime sync", error);
    return null;
  }
}

/** Keeps cached operational data current for every authenticated browser session. */
export function RealtimeSync({ client }: { client: QueryClient }) {
  useEffect(() => {
    const accessToken = token();
    if (!accessToken) return;
    const endpoint = getWebSocketEndpoint();
    if (!endpoint) return;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    let socket: WebSocket | undefined;
    const connect = () => {
      const activeToken = token();
      if (!activeToken) return;
      socket = new WebSocket(endpoint, activeToken);
      socket.onmessage = () => invalidatedQueries.forEach(queryKey => client.invalidateQueries({ queryKey: [queryKey] }));
      socket.onclose = () => { if (!stopped) reconnectTimer = setTimeout(connect, 5_000); };
    };
    connect();
    return () => { stopped = true; if (reconnectTimer) clearTimeout(reconnectTimer); socket?.close(); };
  }, [client]);
  return null;
}
