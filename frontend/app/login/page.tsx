"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiBase } from "@/lib/api";
import { saveSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter(); const [username, setUsername] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) { event.preventDefault(); if (busy) return; setBusy(true); setError(""); try { const response = await fetch(`${apiBase}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) }); if (!response.ok) { setError(response.status === 401 ? "اسم المستخدم أو كلمة المرور غير صحيحة." : "تعذر تسجيل الدخول حاليًا."); return; } const result = await response.json() as { access_token: string; refresh_token: string }; saveSession(result.access_token, result.refresh_token); router.replace("/"); } catch { setError("تعذر الاتصال بالخدمة. حاول مرة أخرى."); } finally { setBusy(false); } }
  return <main className="grid min-h-screen place-items-center p-4"><form onSubmit={submit} className="panel w-full max-w-md"><div className="mb-7"><img src="/logo.png" alt="شعار شركة الفكر الصاعد" className="size-10 rounded-xl bg-white object-contain" /><h1 className="mt-4 text-2xl font-bold">تسجيل الدخول</h1><p className="mt-1 text-sm text-slate-500">FieldApp لإدارة العمليات الميدانية</p></div><label className="block text-sm">اسم المستخدم<input value={username} onChange={e => setUsername(e.target.value)} className="mt-1 w-full rounded-xl border bg-transparent p-3" required /></label><label className="mt-4 block text-sm">كلمة المرور<input value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-xl border bg-transparent p-3" type="password" required /></label>{error && <p className="mt-3 text-sm text-red-600">{error}</p>}<button type="submit" disabled={busy} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-brand p-3 font-semibold text-white disabled:cursor-wait disabled:opacity-60">{busy && <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}{busy ? "جارٍ التحقق…" : "دخول"}</button></form></main>;
}
