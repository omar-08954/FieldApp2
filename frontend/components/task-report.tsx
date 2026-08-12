"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

type Report = {
  city: string;
  total_tasks: number;
  completed_tasks: number;
  blocked_tasks: number;
  completion_rate: number;
  by_status: { label: string; value: number }[];
  latest_tasks: {
    id: number;
    task_number: string;
    technician_name: string;
    task_status: string;
    execution_date: string;
  }[];
};

function maxValue(items: { value: number }[]): number {
  return Math.max(1, ...items.map((item) => item.value));
}

export function TaskReport({ city }: { city: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["task-report", city],
    queryFn: () => api<Report>(`/reports/tasks?city=${encodeURIComponent(city)}`),
  });

  if (isLoading) {
    return <section className="panel text-sm text-slate-500">جارٍ إعداد التقرير…</section>;
  }

  if (isError || !data) {
    return (
      <section className="panel text-sm text-red-600">
        تعذر تحميل التقرير. تتطلب هذه الصفحة صلاحية مدير أو مسؤول.
      </section>
    );
  }

  const statusMax = maxValue(data.by_status);

  return (
    <div className="grid gap-5">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["إجمالي المهام", data.total_tasks],
          ["المكتملة", data.completed_tasks],
          ["العوائق", data.blocked_tasks],
          ["معدل الإنجاز", `${data.completion_rate}%`],
        ].map(([label, value]) => (
          <article className="metric" key={String(label)}>
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-3 text-3xl font-bold">{value}</p>
            <p className="mt-1 text-xs text-slate-400">{city}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_1fr]">
        <article className="panel">
          <h2 className="font-bold">توزيع حالات المهام</h2>
          <div className="mt-4 space-y-3">
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
              <p className="py-8 text-center text-sm text-slate-500">لا توجد بيانات لهذه المدينة.</p>
            )}
          </div>
        </article>

        <article className="panel overflow-x-auto">
          <h2 className="mb-4 font-bold">أحدث المهام</h2>
          <table className="w-full text-right text-sm">
            <thead>
              <tr className="text-slate-500">
                <th>المهمة</th>
                <th>الفني</th>
                <th>الحالة</th>
                <th>التاريخ</th>
              </tr>
            </thead>
            <tbody>
              {data.latest_tasks.map((task) => (
                <tr className="border-t" key={task.id}>
                  <td className="py-3">{task.task_number}</td>
                  <td>{task.technician_name}</td>
                  <td>{task.task_status}</td>
                  <td>{task.execution_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.latest_tasks.length && (
            <p className="py-8 text-center text-sm text-slate-500">لا توجد مهام لهذه المدينة.</p>
          )}
        </article>
      </section>
    </div>
  );
}
