"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

type Material = { id: number; name: string; quantity: number; unit: string; notes?: string };

export function MaterialsManagerPanel({ mode }: { mode: "create" | "list" | "manage" }) {
  const client = useQueryClient();
  const { data = [], isLoading, isError } = useQuery({ queryKey: ["materials"], queryFn: () => api<Material[]>("/materials") });
  const [form, setForm] = useState({ name: "", quantity: 0, unit: "قطعة", notes: "" });
  const [message, setMessage] = useState("");
  const refresh = () => client.invalidateQueries({ queryKey: ["materials"] });

  async function createMaterial(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await api("/materials", { method: "POST", body: JSON.stringify(form) });
      setForm({ name: "", quantity: 0, unit: "قطعة", notes: "" });
      setMessage("تمت إضافة المادة.");
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "تعذر إضافة المادة.");
    }
  }

  async function changeQuantity(id: number, delta: number) {
    try {
      await api(`/materials/${id}/quantity?delta=${delta}`, { method: "PATCH" });
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "تعذر تعديل الكمية.");
    }
  }

  return <div className="space-y-5">
    {mode === "create" && <form onSubmit={createMaterial} className="panel max-w-2xl">
      <h2 className="font-bold">إضافة مادة جديدة</h2>
      <div className="mt-4 grid gap-3">
        <input required placeholder="اسم المادة" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="rounded-xl border bg-transparent p-3" />
        <input required min="0" type="number" placeholder="الكمية" value={form.quantity} onChange={e => setForm({ ...form, quantity: +e.target.value })} className="rounded-xl border bg-transparent p-3" />
        <input required placeholder="الوحدة" value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} className="rounded-xl border bg-transparent p-3" />
        <textarea placeholder="ملاحظات" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="rounded-xl border bg-transparent p-3" />
      </div>
      <button className="mt-4 w-full rounded-xl bg-brand p-3 font-semibold text-white">حفظ المادة</button>
      {message && <p className="mt-3 text-sm text-slate-500">{message}</p>}
    </form>}

    {mode !== "create" && <div className="panel overflow-x-auto">
      <h2 className="mb-4 font-bold">{mode === "manage" ? "إدارة المخزون" : "عرض المواد"}</h2>
      {message && <p className="mb-3 rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-800">{message}</p>}
      {isLoading && <p className="py-5 text-sm text-slate-500">جارٍ تحميل المواد…</p>}
      {isError && <p className="py-5 text-sm text-red-600">تعذر تحميل المواد. تأكد من اتصال API وصلاحيات المدير.</p>}
      {!isLoading && !isError && <table className="w-full text-right text-sm"><thead><tr className="text-slate-500"><th>المادة</th><th>الكمية</th><th>الوحدة</th>{mode === "manage" && <th>الإجراء</th>}</tr></thead><tbody>{data.map(item => <tr className="border-t" key={item.id}><td className="py-3">{item.name}</td><td>{item.quantity}</td><td>{item.unit}</td>{mode === "manage" && <td className="space-x-2 space-x-reverse"><button type="button" onClick={() => changeQuantity(item.id, 1)} className="rounded bg-emerald-100 px-2 py-1 text-emerald-700">+1</button><button type="button" onClick={() => changeQuantity(item.id, -1)} className="rounded bg-red-100 px-2 py-1 text-red-700">-1</button></td>}</tr>)}</tbody></table>}
    </div>}
  </div>;
}
