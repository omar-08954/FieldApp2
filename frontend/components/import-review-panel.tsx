"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

type Review = { id: number; source_row: number; task_number?: string; technician_name?: string; subscription_number?: string; task_type?: string; task_status?: string; city?: string; notes?: string; execution_date?: string; exception_type: string; error_message: string; field_name?: string; suggested_action?: string; action_taken: string };

const labels: Record<string, string> = { technician_name: "الفني", task_number: "رقم المهمة", subscription_number: "رقم الاشتراك", task_type: "نوع المهمة", task_status: "حالة المهمة", city: "المدينة", notes: "الملاحظات", execution_date: "تاريخ التنفيذ" };

export function ImportReviewPanel() {
  const client = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["import-reviews"], queryFn: () => api<{ items: Review[] }>("/import-reviews") });
  const [editing, setEditing] = useState<Review>();
  const [message, setMessage] = useState("");
  const refresh = () => client.invalidateQueries({ queryKey: ["import-reviews"] });
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!editing) return;
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const values = Object.fromEntries([...new FormData(event.currentTarget).entries()].filter(([, value]) => value !== ""));
    try {
      if (submitter?.name === "reinsert") {
        const result = await api<{ ok: boolean; message?: string }>(`/import-reviews/${editing.id}/reinsert`, { method: "POST", body: JSON.stringify(values) });
        setMessage(result.ok ? "تمت إعادة إدراج المهمة بعد تصحيح العمود المتأثر." : result.message ?? "بقي السجل في المراجعة.");
        if (result.ok) setEditing(undefined);
      } else {
        await api(`/import-reviews/${editing.id}`, { method: "PATCH", body: JSON.stringify(values) });
        setMessage("تم حفظ تصحيح العمود المحدد. راجع الصف ثم أعد إدراجه.");
      }
      refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "تعذر تنفيذ الإجراء."); }
  }
  const fieldClass = (field: string) => `rounded-lg border bg-transparent p-2 ${editing?.field_name === field ? "border-red-500 ring-2 ring-red-200 dark:ring-red-950" : ""}`;
  return <div className="panel overflow-x-auto"><h2 className="mb-2 font-bold">مراجعة الاستيراد</h2><p className="mb-4 text-sm text-slate-500">يتم الاحتفاظ بكل أعمدة الصف، ويُحدد العمود الذي يحتاج إلى تصحيح فقط.</p>{message && <p className="mb-4 rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-800">{message}</p>}{isLoading && <p className="py-5 text-sm text-slate-500">جارٍ تحميل سجلات المراجعة…</p>}{isError && <p className="py-5 text-sm text-red-600">تعذر تحميل سجلات المراجعة.</p>}{editing && <form onSubmit={save} className="mb-5 grid gap-3 rounded-xl border border-brand/30 bg-brand/5 p-4 sm:grid-cols-2"><p className="sm:col-span-2 text-sm"><strong>نوع المشكلة:</strong> {labels[editing.field_name ?? ""] ?? editing.exception_type} — {editing.error_message}</p><p className="sm:col-span-2 text-sm text-amber-700 dark:text-amber-300">{editing.suggested_action ?? "صحح الخانة المحددة ثم أعد إدراج الصف."}</p><label>رقم المهمة<input name="task_number" required defaultValue={editing.task_number} className={fieldClass("task_number")} /></label><label>الفني<input name="technician_name" defaultValue={editing.technician_name} className={fieldClass("technician_name")} /></label><label>رقم الاشتراك<input name="subscription_number" defaultValue={editing.subscription_number} className={fieldClass("subscription_number")} /></label><label>نوع المهمة<input name="task_type" defaultValue={editing.task_type} className={fieldClass("task_type")} /></label><label>الحالة<input name="task_status" defaultValue={editing.task_status} className={fieldClass("task_status")} /></label><label>المدينة<input name="city" defaultValue={editing.city} className={fieldClass("city")} /></label><label>تاريخ التنفيذ<input name="execution_date" type="date" defaultValue={editing.execution_date} className={fieldClass("execution_date")} /></label><label className="sm:col-span-2">الملاحظات<textarea name="notes" defaultValue={editing.notes} className={fieldClass("notes")} /></label><div className="flex gap-2 sm:col-span-2"><button type="submit" className="rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white">حفظ التصحيح</button><button type="submit" name="reinsert" className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white">تصحيح وإعادة الإدراج</button><button type="button" onClick={() => setEditing(undefined)} className="rounded-lg px-3 py-2 text-sm">إلغاء</button></div></form>} {!isLoading && !isError && <table className="w-full text-right text-sm"><thead><tr className="text-slate-500"><th>الصف</th><th>المهمة</th><th>الفني</th><th>الاشتراك</th><th>النوع</th><th>الحالة</th><th>المدينة</th><th>المشكلة</th><th>الإجراء</th></tr></thead><tbody>{data?.items.map(row => <tr className="border-t" key={row.id}><td className="py-3">{row.source_row}</td><td>{row.task_number || "—"}</td><td>{row.technician_name || "—"}</td><td>{row.subscription_number || "—"}</td><td>{row.task_type || "—"}</td><td>{row.task_status || "—"}</td><td>{row.city || "—"}</td><td title={row.error_message}><span className="font-semibold text-red-600">{labels[row.field_name ?? ""] ?? row.exception_type}</span><br /><span className="text-xs">{row.suggested_action || row.error_message}</span></td><td><button type="button" onClick={() => setEditing(row)} className="rounded-lg bg-indigo-100 px-2 py-1 text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">تصحيح العمود</button></td></tr>)}</tbody></table>}</div>;
}
