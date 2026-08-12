"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardList, ScanSearch } from "lucide-react";

import { api, Summary } from "@/lib/api";

const empty: Summary = {
  total_tasks: 0,
  completion_rate: 0,
  delayed_tasks: 0,
  needs_review: 0,
  by_status: [],
  daily_trend: [],
  latest_tasks: [],
  top_technicians: [],
};

const cards = (data: Summary) => [
  ["إجمالي المهام", data.total_tasks, ClipboardList, "من كامل العمليات"],
  ["معدل الإنجاز", `${data.completion_rate}%`, CheckCircle2, "مهام مكتملة"],
  ["متأخرة", data.delayed_tasks, AlertTriangle, "تحتاج متابعة"],
  ["للمراجعة", data.needs_review, ScanSearch, "من الاستيراد"],
] as const;

function maxValue(items: { value: number }[]): number {
  return Math.max(1, ...items.map((item) => item.value));
}

export function Dashboard() {
  const { data = empty } = useQuery({
    queryKey: ["summary"],
    queryFn: () => api<Summary>("/dashboard/summary"),
  });

  const statusMax = maxValue(data.by_status);
  const technicianMax = maxValue(data.top_technicians);

  return (
    <>
      <section className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-sm font-medium text-brand">مساحة العمليات</p>
          <h1 className="text-3xl font-bold tracking-tight">صباح الخير، فريق العمل</h1>
          <p className="mt-2 text-slate-500">نظرة حية على الأداء والمهام الميدانية.</p>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards(data).map(([label, value, Icon, note]) => (
          <article className="metric" key={label}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-3 text-3xl font-bold">{value}</p>
                <p className="mt-2 text-xs text-slate-400">{note}</p>
              </div>
              <div className="rounded-xl bg-indigo-50 p-2.5 text-brand dark:bg-indigo-950">
                <Icon size={20} />
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.7fr_1fr]">
        <article className="panel">
          <div className="mb-5">
            <h2 className="font-bold">الاتجاه اليومي</h2>
            <p className="text-sm text-slate-500">آخر 14 يوماً من العمليات</p>
          </div>

          <div className="space-y-3">
            {data.daily_trend.length ? (
              data.daily_trend.map((row) => (
                <div key={row.label}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span>{row.label}</span>
                    <span className="font-semibold">{row.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-2 rounded-full bg-brand"
                      style={{ width: `${Math.min(100, row.value * 10)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="py-10 text-center text-sm text-slate-500">لا توجد بيانات يومية بعد.</p>
            )}
          </div>
        </article>

        <article className="panel">
          <h2 className="font-bold">توزيع الحالة</h2>
          <p className="mb-4 text-sm text-slate-500">حالة المهام الحالية</p>

          <div className="space-y-3">
            {data.by_status.length ? (
              data.by_status.map((row) => (
                <div key={row.label}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span>{row.label}</span>
                    <span className="font-semibold">{row.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-2 rounded-full bg-brand"
                      style={{ width: `${(row.value / statusMax) * 100}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="py-10 text-center text-sm text-slate-500">لا توجد حالات مهام بعد.</p>
            )}
          </div>
        </article>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-2">
        <article className="panel">
          <h2 className="mb-4 font-bold">أفضل الفنيين</h2>

          <div className="space-y-3">
            {data.top_technicians.length ? (
              data.top_technicians.map((row) => (
                <div key={row.label}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span>{row.label}</span>
                    <span className="font-semibold">{row.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-2 rounded-full bg-brand"
                      style={{ width: `${(row.value / technicianMax) * 100}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="py-10 text-center text-sm text-slate-500">لا يوجد ترتيب فنيين بعد.</p>
            )}
          </div>
        </article>

        <article className="panel">
          <h2 className="mb-4 font-bold">أحدث المهام</h2>
          <div className="divide-y">
            {data.latest_tasks.length ? (
              data.latest_tasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                  <span>
                    <span className="font-semibold">{task.task_number}</span>
                    <span className="mr-2 text-slate-500">{task.technician_name}</span>
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">
                    {task.task_status}
                  </span>
                </div>
              ))
            ) : (
              <p className="py-10 text-center text-sm text-slate-500">لا توجد مهام بعد.</p>
            )}
          </div>
        </article>
      </section>
    </>
  );
}
