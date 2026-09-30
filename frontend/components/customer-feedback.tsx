"use client";

import { Eraser } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

function SignaturePad({ onChange }: { onChange: (value: string) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null); const drawing = useRef(false);
  useEffect(() => { const element = canvas.current; if (!element) return; const context = element.getContext("2d"); if (!context) return; context.lineWidth = 2; context.lineCap = "round"; context.strokeStyle = "#111827"; }, []);
  function point(event: React.PointerEvent<HTMLCanvasElement>) { const element = canvas.current!; const box = element.getBoundingClientRect(); return { x: (event.clientX - box.left) * (element.width / box.width), y: (event.clientY - box.top) * (element.height / box.height) }; }
  function start(event: React.PointerEvent<HTMLCanvasElement>) { drawing.current = true; event.currentTarget.setPointerCapture(event.pointerId); const context = canvas.current!.getContext("2d")!; const position = point(event); context.beginPath(); context.moveTo(position.x, position.y); }
  function move(event: React.PointerEvent<HTMLCanvasElement>) { if (!drawing.current) return; const context = canvas.current!.getContext("2d")!; const position = point(event); context.lineTo(position.x, position.y); context.stroke(); onChange(canvas.current!.toDataURL("image/png")); }
  function clear() { const element = canvas.current!; element.getContext("2d")!.clearRect(0, 0, element.width, element.height); onChange(""); }
  return <div><div className="flex items-center justify-between"><label className="text-sm text-slate-500">التوقيع الإلكتروني</label><button type="button" onClick={clear} className="inline-flex items-center gap-1 text-xs text-slate-500"><Eraser size={14}/>مسح</button></div><canvas ref={canvas} width={720} height={180} onPointerDown={start} onPointerMove={move} onPointerUp={() => { drawing.current = false; }} className="mt-1 h-36 w-full touch-none rounded-xl border bg-white" /></div>;
}

export function CustomerFeedback() {
  const [form, setForm] = useState({ task_number: "", customer_phone: "", rating: "5", feedback: "", signature: "" }); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { const taskNumber = new URLSearchParams(window.location.search).get("task_number"); if (taskNumber) setForm(current => ({ ...current, task_number: taskNumber })); }, []);
  async function submit(event: React.FormEvent) { event.preventDefault(); setBusy(true); setMessage(""); try { await api("/public/tasks/customer-feedback", { method: "POST", body: JSON.stringify({ ...form, rating: Number(form.rating) }) }); setMessage("شكرًا لك، تم تسجيل تقييمك وتوقيعك."); } catch (error) { setMessage(error instanceof Error ? error.message : "تعذر تسجيل التقييم."); } finally { setBusy(false); } }
  const update = (key: keyof typeof form, value: string) => setForm(current => ({ ...current, [key]: value }));
  return <form onSubmit={submit} className="panel mx-auto max-w-xl"><h1 className="text-2xl font-bold">تقييم الخدمة</h1><p className="mt-1 text-sm text-slate-500">أدخل رقم المهمة ورقم الجوال المرتبط بها.</p><div className="mt-5 grid gap-3"><input required placeholder="رقم المهمة" value={form.task_number} onChange={e => update("task_number", e.target.value)} className="rounded-xl border bg-transparent p-3"/><input required placeholder="رقم الجوال" value={form.customer_phone} onChange={e => update("customer_phone", e.target.value)} className="rounded-xl border bg-transparent p-3"/><label className="grid gap-1 text-sm">التقييم<select value={form.rating} onChange={e => update("rating", e.target.value)} className="rounded-xl border bg-transparent p-3"><option value="5">★★★★★ ممتاز</option><option value="4">★★★★ جيد جدًا</option><option value="3">★★★ جيد</option><option value="2">★★ يحتاج تحسين</option><option value="1">★ ضعيف</option></select></label><textarea placeholder="ملاحظاتك" value={form.feedback} onChange={e => update("feedback", e.target.value)} className="rounded-xl border bg-transparent p-3"/><SignaturePad onChange={value => update("signature", value)}/></div><button disabled={busy} className="mt-4 rounded-xl bg-brand px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? "جارٍ الإرسال…" : "إرسال التقييم"}</button>{message && <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{message}</p>}</form>;
}
