"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Activity, BellRing, Bot, CheckCircle2, Database, RefreshCw, Users, XCircle } from "lucide-react";
import { api, apiRoot } from "@/lib/api";

type Status = { environment: string; total_users: number; total_tasks: number; pending_import_reviews: number; unread_notifications: number; ai_enabled: boolean };
type Health = { service: string; version: string; status: string; database: string; environment: string };
type Scope = "tasks" | "import_reviews";

export function DeveloperStatusPanel() {
  const client = useQueryClient(); const { data, isLoading, isError } = useQuery({ queryKey: ["developer-status"], queryFn: () => api<Status>("/developer/status") });
  const health = useQuery({
    queryKey: ["api-health"],
    queryFn: async () => {
      const response = await fetch(`${apiRoot}/health`, { cache: "no-store" });
      if (!response.ok) throw new Error("Health check failed");
      return response.json() as Promise<Health>;
    },
    refetchInterval: 30_000,
  });
  const [working, setWorking] = useState<Scope>(); const [message, setMessage] = useState("");
  async function cleanup(scope: Scope) { const label = scope === "tasks" ? "المهام" : "مراجعة الاستيراد"; if (!window.confirm(`سيتم حذف ${label} فقط نهائيًا. هل تريد المتابعة؟`)) return; setWorking(scope); setMessage(`جارٍ تنظيف ${label}…`); try { const result = await api<{ deleted: number; message: string }>("/developer/cleanup", { method: "POST", body: JSON.stringify({ scope }) }); setMessage(`${result.message} عدد السجلات المحذوفة: ${result.deleted}.`); client.invalidateQueries({ queryKey: ["developer-status"] }); client.invalidateQueries({ queryKey: ["tasks"] }); client.invalidateQueries({ queryKey: ["import-reviews"] }); } catch (error) { setMessage(error instanceof Error ? error.message : "تعذر تنظيف البيانات."); } finally { setWorking(undefined); } }
  if (isLoading) return <section className="panel text-sm text-slate-500">جارٍ فحص حالة النظام…</section>;
  if (isError || !data) return <section className="panel text-sm text-red-600">لا تملك صلاحية الوصول إلى مركز المطور أو تعذر الاتصال بالخدمة.</section>;
  const cards = [["البيئة", data.environment, Activity], ["المستخدمون", data.total_users, Users], ["المهام", data.total_tasks, Database], ["إشعارات غير مقروءة", data.unread_notifications, BellRing], ["الاستيراد المعلّق", data.pending_import_reviews, Activity], ["المساعد الذكي", data.ai_enabled ? "مفعل" : "غير مفعل", Bot]] as const;
  return <div className="space-y-6"><section className="panel"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-bold">حالة خدمة API</h2><p className="mt-1 text-sm text-slate-500">يتم تحديث الحالة تلقائيًا كل 30 ثانية.</p></div><button type="button" onClick={() => health.refetch()} disabled={health.isFetching} className="inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold disabled:opacity-60"><RefreshCw size={16} className={health.isFetching ? "animate-spin" : ""} />إعادة الفحص</button></div>{health.isPending ? <p className="mt-4 text-sm text-slate-500">جارٍ الاتصال بخدمة API…</p> : health.isError ? <div className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300"><XCircle size={18} />تعذر الاتصال بخدمة API.</div> : health.data ? <div className="mt-4 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300"><div className="flex items-center gap-2 font-semibold"><CheckCircle2 size={17} />الخدمة متصلة</div><p className="mt-2">{health.data.service} — الإصدار {health.data.version}</p></div><div className="rounded-xl bg-slate-100 p-3 text-sm dark:bg-slate-800"><p className="text-slate-500">قاعدة البيانات</p><p className="mt-1 font-semibold">{health.data.database === "ok" ? "متصلة" : "غير متاحة"}</p></div><div className="rounded-xl bg-slate-100 p-3 text-sm dark:bg-slate-800"><p className="text-slate-500">بيئة التشغيل</p><p className="mt-1 font-semibold">{health.data.environment}</p></div></div> : null}</section><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(([label, value, Icon]) => <article className="metric" key={label}><div className="flex items-start justify-between"><div><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-2xl font-bold">{value}</p></div><Icon className="text-brand" size={20} /></div></article>)}</div><section className="panel"><h2 className="font-bold">تنظيف البيانات</h2><p className="mt-1 text-sm text-slate-500">اختر النطاق المطلوب. لن يتم حذف المستخدمين أو التقارير.</p><div className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={Boolean(working)} onClick={() => cleanup("tasks")} className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-wait disabled:opacity-60">{working === "tasks" ? "جارٍ تنظيف المهام…" : "تنظيف المهام"}</button><button type="button" disabled={Boolean(working)} onClick={() => cleanup("import_reviews")} className="rounded-xl border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 disabled:cursor-wait disabled:opacity-60">{working === "import_reviews" ? "جارٍ تنظيف المراجعة…" : "تنظيف مراجعة الاستيراد"}</button></div>{message && <p className="mt-4 rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-800">{message}</p>}</section></div>;
}
