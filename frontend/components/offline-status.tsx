"use client";

import { CloudOff, RefreshCw, Wifi } from "lucide-react";
import { useEffect, useState } from "react";
import { flushOfflineReports, flushOfflineTasks, offlineQueueEvent, pendingReportCount, pendingTaskCount } from "@/lib/offline-queue";

export function OfflineStatus() {
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState(0);
  const refresh = () => { setOnline(navigator.onLine); void pendingReportCount().then(count => setPending(pendingTaskCount() + count)); };
  useEffect(() => { refresh(); window.addEventListener("online", refresh); window.addEventListener("offline", refresh); window.addEventListener(offlineQueueEvent, refresh); return () => { window.removeEventListener("online", refresh); window.removeEventListener("offline", refresh); window.removeEventListener(offlineQueueEvent, refresh); }; }, []);
  async function sync() { await Promise.all([flushOfflineTasks(), flushOfflineReports()]); refresh(); }
  return <div className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs ${online ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300" : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"}`} title={online ? "الاتصال متاح" : "لا يوجد اتصال بالإنترنت"}>{online ? <Wifi size={14} /> : <CloudOff size={14} />}<span className="hidden sm:inline">{online ? "متصل" : "بدون اتصال"}</span>{pending > 0 && <span>({pending})</span>}{online && pending > 0 && <button type="button" onClick={() => void sync()} aria-label="مزامنة الآن" title="مزامنة الآن"><RefreshCw size={13} /></button>}</div>;
}
