"use client";
import { useEffect } from "react";
import { flushOfflineReports, flushOfflineTasks } from "@/lib/offline-queue";
export function OfflineSync() { useEffect(() => { if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js"); const sync = () => { void flushOfflineTasks(); void flushOfflineReports(); }; window.addEventListener("online", sync); sync(); return () => window.removeEventListener("online", sync); }, []); return null; }
