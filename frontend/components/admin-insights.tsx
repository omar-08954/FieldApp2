"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Performance = { technician_id:number; technician_name:string; city:string|null; assigned_tasks:number; completed_assignments:number; recorded_tasks:number; blocked_tasks:number; completion_rate:number };
type Audit = { id:number; actor_name:string; action:string; entity_type:string; entity_id:number|null; details:string|null; created_at:string };

export function AdminInsights() {
  const performance = useQuery({ queryKey:["technician-performance"], queryFn:()=>api<Performance[]>("/performance/technicians") });
  const audit = useQuery({ queryKey:["audit-logs"], queryFn:()=>api<Audit[]>("/audit-logs?limit=100") });
  return <div className="space-y-6">
    <section className="panel overflow-x-auto"><div className="mb-4"><h2 className="font-bold">تقييم أداء الفنيين</h2><p className="mt-1 text-sm text-slate-500">نسبة الإنجاز وعدد المهام المتأخرة/المعطلة حسب البيانات الحالية.</p></div>
      {performance.isLoading ? <p className="text-sm text-slate-500">جارٍ تحميل الأداء…</p> : performance.isError ? <p className="text-sm text-red-600">تعذر تحميل تقييم الأداء.</p> : <table className="w-full min-w-[720px] text-right text-sm"><thead><tr className="text-slate-500"><th className="pb-3">الفني</th><th>المدينة</th><th>المسندة</th><th>المنجزة</th><th>المسجلة</th><th>المعطلة</th><th>نسبة الإنجاز</th></tr></thead><tbody>{performance.data?.map(row=><tr className="border-t" key={row.technician_id}><td className="py-3 font-medium">{row.technician_name}</td><td>{row.city||"—"}</td><td>{row.assigned_tasks}</td><td>{row.completed_assignments}</td><td>{row.recorded_tasks}</td><td>{row.blocked_tasks}</td><td><span className={row.completion_rate>=80?"text-emerald-600":"text-amber-600"}>{row.completion_rate}%</span></td></tr>)}</tbody></table>}
    </section>
    <section className="panel overflow-x-auto"><div className="mb-4"><h2 className="font-bold">سجل تعديلات المدير</h2><p className="mt-1 text-sm text-slate-500">آخر 100 عملية إدارية مع وقت التنفيذ والبيانات المرتبطة بها.</p></div>
      {audit.isLoading ? <p className="text-sm text-slate-500">جارٍ تحميل السجل…</p> : audit.isError ? <p className="text-sm text-red-600">تعذر تحميل سجل التعديلات.</p> : <table className="w-full min-w-[760px] text-right text-sm"><thead><tr className="text-slate-500"><th className="pb-3">الوقت</th><th>المدير</th><th>العملية</th><th>العنصر</th><th>التفاصيل</th></tr></thead><tbody>{audit.data?.map(row=><tr className="border-t" key={row.id}><td className="py-3 whitespace-nowrap">{new Date(row.created_at).toLocaleString("ar-SA")}</td><td>{row.actor_name}</td><td>{row.action}</td><td>{row.entity_type}{row.entity_id?` #${row.entity_id}`:""}</td><td>{row.details||"—"}</td></tr>)}</tbody></table>}
    </section>
  </div>;
}
