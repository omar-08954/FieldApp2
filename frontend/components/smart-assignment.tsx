"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState } from "react";

type Suggestion = { technician_id: number; technician_name: string; city: string | null; active_assignments: number; score: number };

export function SmartAssignmentPanel() {
  const [city, setCity] = useState("");
  const { data = [], isFetching } = useQuery({ queryKey: ["assignment-suggestions", city], queryFn: () => api<Suggestion[]>(`/assignments/suggestions${city ? `?city=${encodeURIComponent(city)}` : ""}`), refetchInterval: 30_000 });
  return <section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-bold">التوزيع الذكي</h2><p className="mt-1 text-sm text-slate-500">اقتراح أفضل فني حسب المدينة والحمل الحالي.</p></div><select value={city} onChange={event => setCity(event.target.value)} className="rounded-xl border bg-transparent p-3 text-sm"><option value="">كل المدن</option><option>جدة</option><option>مكة</option></select></div><div className="mt-4 grid gap-2">{data.slice(0, 5).map((item, index) => <div className={`flex items-center justify-between rounded-xl border p-3 ${index === 0 ? "border-brand bg-brand/5" : ""}`} key={item.technician_id}><div><span className="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">#{index + 1}</span><span className="font-semibold">{item.technician_name}</span><span className="mr-2 text-xs text-slate-500">{item.city || "دون مدينة"}</span></div><span className="text-xs text-slate-500">{item.active_assignments} مهام نشطة</span></div>)}{isFetching && <p className="text-sm text-slate-500">جارٍ تحديث الاقتراحات…</p>}{!isFetching && !data.length && <p className="py-5 text-center text-sm text-slate-500">لا يوجد فنيون متاحون.</p>}</div></section>;
}
