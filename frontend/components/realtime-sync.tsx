"use client";

import { QueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiBase } from "@/lib/api";
import { currentUser, token } from "@/lib/auth";

const invalidatedQueries = ["summary", "tasks", "assignments", "notifications", "import-reviews", "users", "materials", "daily-reports", "messages"];

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
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as { event?: string; payload?: { user_ids?: number[]; title?: string; message?: string } };
          const name = event.event ?? "";
          const payload = event.payload ?? {};
          const user = currentUser();
          const targeted = !payload.user_ids || !user || payload.user_ids.includes(user.id);
          if (targeted && payload.title && payload.message && typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("fieldapp:notification", { detail: { title: payload.title, message: payload.message } }));
          }
          const related = name.startsWith("message") ? ["messages", "notifications"] : name.startsWith("notification") ? ["notifications"] : name.startsWith("task") ? ["summary", "tasks", "task-report"] : name.startsWith("import") ? ["summary", "import-reviews"] : name.startsWith("assignment") ? ["assignments", "completed-assignments"] : name.startsWith("daily_report") ? ["daily-reports"] : ["summary"];
          related.forEach(queryKey => client.invalidateQueries({ queryKey: [queryKey] }));
        } catch {
          invalidatedQueries.forEach(queryKey => client.invalidateQueries({ queryKey: [queryKey] }));
        }
      };
      socket.onclose = () => { if (!stopped) reconnectTimer = setTimeout(connect, 5_000); };
    };
    connect();
    return () => { stopped = true; if (reconnectTimer) clearTimeout(reconnectTimer); socket?.close(); };
  }, [client]);
  return null;
}
