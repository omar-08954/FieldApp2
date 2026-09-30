"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Gauge, Star } from "lucide-react";
import { api } from "@/lib/api";

type Analytics = { total_tasks: number; completed_tasks: number; overdue_tasks: number; average_rating: number | null; technician_load: { technician_id: number; technician_name: string; total: number; completed: number }[] };

export function OperationsAnalytics() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["operations-analytics"], queryFn: () => api<Analytics>("/analytics/operations"), refetchInterval: 60_000 });
  if (isLoading) return <p className="text-sm text-slate-500">جارٍ تحميل المؤشرات…</p>;
  if (isError || !data) return <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">تعذر تحميل المؤشرات التشغيلية.</p>;
  const cards = [[Gauge, "كل المهام", data.total_tasks, "text-brand"], [CheckCircle2, "المكتملة", data.completed_tasks, "text-emerald-600"], [AlertTriangle, "متأخرة عن SLA", data.overdue_tasks, "text-amber-600"], [Star, "متوسط تقييم العملاء", data.average_rating ?? "—", "text-yellow-500"]] as const;
  return <section className="space-y-5"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([Icon, label, value, color]) => <div className="panel flex items-center gap-3" key={label}><Icon className={color} size={24}/><div><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></div></div>)}</div><div className="panel overflow-x-auto"><h2 className="mb-4 font-bold">أداء الفنيين</h2><table className="w-full text-right text-sm"><thead><tr className="text-slate-500"><th className="px-2 py-2">الفني</th><th className="px-2 py-2">المهام</th><th className="px-2 py-2">المكتملة</th><th className="px-2 py-2">نسبة الإنجاز</th></tr></thead><tbody>{data.technician_load.map(row => <tr className="border-t" key={row.technician_id}><td className="px-2 py-3">{row.technician_name}</td><td className="px-2">{row.total}</td><td className="px-2">{row.completed}</td><td className="px-2">{row.total ? `${Math.round(row.completed / row.total * 100)}%` : "—"}</td></tr>)}</tbody></table>{!data.technician_load.length && <p className="py-8 text-center text-sm text-slate-500">لا توجد بيانات كافية بعد.</p>}</div></section>;
}
