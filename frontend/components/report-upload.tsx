"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function ReportUpload() {
  const [file, setFile] = useState<File>(); const [date, setDate] = useState(new Date().toISOString().slice(0, 10)); const [busy, setBusy] = useState(false); const [result, setResult] = useState("");
  async function upload() { if (!file || busy) return; setBusy(true); setResult("جارٍ رفع التقرير…"); try { const body = new FormData(); body.append("image", file); await api(`/daily-reports?report_date=${date}`, { method: "POST", body }); setResult("تم حفظ التقرير بنجاح."); setFile(undefined); } catch (error) { setResult(error instanceof Error ? error.message : "تعذر حفظ التقرير. تحقق من إعدادات التخزين."); } finally { setBusy(false); } }
  return <section className="panel max-w-xl"><h2 className="font-bold">إضافة تقرير يومي</h2><p className="mt-1 text-sm text-slate-500">JPEG أو PNG، بحد أقصى 25 MB.</p><div className="mt-5 grid gap-3"><input type="date" value={date} onChange={e => setDate(e.target.value)} className="rounded-xl border bg-transparent p-3" /><input type="file" accept="image/jpeg,image/png" onChange={e => setFile(e.target.files?.[0])} className="rounded-xl border bg-transparent p-3" /></div><button type="button" onClick={upload} disabled={!file || busy} className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-brand px-5 py-3 font-semibold text-white disabled:cursor-wait disabled:opacity-50">{busy && <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}{busy ? "جارٍ الرفع…" : "حفظ التقرير"}</button>{result && <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{result}</p>}</section>;
}
