"use client";

import Link from "next/link";
import { Bell, Check, CheckCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Notification = { id: number; title: string; message: string; is_read: boolean; created_at: string };
type NotificationPage = { items: Notification[]; unread_count: number };

export function NotificationCenter() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<{ title: string; message: string }>();
  const { data } = useQuery({ queryKey: ["notifications"], queryFn: () => api<NotificationPage>("/notifications?page_size=30"), staleTime: 15_000 });
  const items = data?.items ?? [];

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ title: string; message: string }>).detail;
      setToast(detail);
      window.setTimeout(() => setToast(undefined), 6000);
      if ("Notification" in window && Notification.permission === "granted") new Notification(detail.title, { body: detail.message, icon: "/logo.png" });
      client.invalidateQueries({ queryKey: ["notifications"] });
    };
    window.addEventListener("fieldapp:notification", handler);
    return () => window.removeEventListener("fieldapp:notification", handler);
  }, [client]);

  async function read(id: number) {
    await api(`/notifications/${id}/read`, { method: "POST" });
    client.invalidateQueries({ queryKey: ["notifications"] });
  }
  async function readAll() {
    await api("/notifications/read-all", { method: "POST" });
    client.invalidateQueries({ queryKey: ["notifications"] });
  }
  async function enableBrowserNotifications() {
    if ("Notification" in window && Notification.permission === "default") await Notification.requestPermission();
  }

  return <>
    <div className="relative">
      <button type="button" onClick={() => { setOpen(value => !value); void enableBrowserNotifications(); }} className="relative rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="الإشعارات">
        <Bell size={19}/>{Boolean(data?.unread_count) && <span className="absolute -left-1 -top-1 grid min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] leading-4 text-white">{(data?.unread_count ?? 0) > 9 ? "9+" : data?.unread_count}</span>}
      </button>
      {open && <div className="absolute left-0 top-12 z-50 w-[min(92vw,380px)] overflow-hidden rounded-2xl border bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b p-4"><div><h2 className="font-bold">الإشعارات</h2><p className="text-xs text-slate-500">{data?.unread_count ?? 0} غير مقروء</p></div><button type="button" onClick={() => void readAll()} className="inline-flex items-center gap-1 text-xs text-brand"><CheckCheck size={14}/>قراءة الكل</button></div>
        <div className="max-h-96 overflow-y-auto">{items.length ? items.slice(0, 8).map(item => <button type="button" key={item.id} onClick={() => void read(item.id)} className={`flex w-full gap-3 border-b p-3 text-right hover:bg-slate-50 dark:hover:bg-slate-800 ${item.is_read ? "opacity-60" : ""}`}><Bell size={16} className="mt-1 shrink-0 text-brand"/><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{item.title}</span><span className="mt-1 block truncate text-xs text-slate-500">{item.message}</span><span className="mt-1 block text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString("ar-SA")}</span></span>{!item.is_read && <Check size={15} className="mt-1 text-brand"/>}</button>) : <p className="p-8 text-center text-sm text-slate-500">لا توجد إشعارات.</p>}</div>
        <Link href="/notifications" onClick={() => setOpen(false)} className="block border-t p-3 text-center text-sm font-semibold text-brand">عرض كل الإشعارات</Link>
      </div>}
    </div>
    {toast && <div className="fixed left-4 top-20 z-[60] w-[min(92vw,380px)] rounded-2xl border border-brand/20 bg-white p-4 shadow-2xl dark:bg-slate-900"><div className="flex gap-3"><Bell className="mt-0.5 shrink-0 text-brand" size={18}/><div><p className="font-bold">{toast.title}</p><p className="mt-1 text-sm text-slate-500">{toast.message}</p></div></div></div>}
  </>;
}
