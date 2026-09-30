"use client";

import { MessageCircle, Send, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { currentUser } from "@/lib/auth";

type Person = { id: number; full_name: string; role: string };
type Message = { id: number; technician_id: number; sender_id: number | null; sender_name: string; body: string; message_type: string; report_date: string | null; created_at: string };

export function MessagesPage() {
  const me = currentUser();
  const client = useQueryClient();
  const [technicianId, setTechnicianId] = useState<number>();
  const [body, setBody] = useState("");
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => api<Person[]>("/users"), enabled: me?.role === "admin" });
  const technicians = users.filter(user => user.role === "technician");
  useEffect(() => { if (me?.role === "admin" && !technicianId && technicians[0]) setTechnicianId(technicians[0].id); }, [me?.role, technicianId, technicians]);
  const selectedId = me?.role === "technician" ? me.id : technicianId;
  const { data: messages = [], isLoading } = useQuery({ queryKey: ["messages", selectedId], queryFn: () => api<Message[]>(`/messages${selectedId ? `?technician_id=${selectedId}` : ""}`), enabled: Boolean(selectedId), refetchInterval: 30_000 });
  const send = useMutation({ mutationFn: () => api<Message>("/messages", { method: "POST", body: JSON.stringify({ technician_id: technicianId, body }) }), onSuccess: () => { setBody(""); client.invalidateQueries({ queryKey: ["messages", selectedId] }); } });

  return <section className="grid gap-5 lg:grid-cols-[280px_1fr]">
    <div className="panel h-fit"><div className="mb-4 flex items-center gap-2"><MessageCircle className="text-brand" size={20}/><div><h1 className="font-bold">الرسائل</h1><p className="text-xs text-slate-500">تواصل مع المدير</p></div></div>{me?.role === "admin" ? <div className="space-y-2">{technicians.map(person => <button key={person.id} onClick={() => setTechnicianId(person.id)} className={`w-full rounded-xl p-3 text-right text-sm ${selectedId === person.id ? "bg-brand text-white" : "bg-slate-50 hover:bg-slate-100 dark:bg-slate-800"}`}>{person.full_name}</button>)}{!technicians.length && <p className="text-sm text-slate-500">لا يوجد فنيون.</p>}</div> : <div className="rounded-xl bg-brand/5 p-3 text-sm">المحادثة مع مدير النظام</div>}</div>
    <div className="panel flex min-h-[560px] flex-col p-0"><div className="border-b p-5"><h2 className="font-bold">محادثة العمل</h2><p className="mt-1 text-xs text-slate-500">يظهر هنا تقرير المهام اليومي تلقائيًا من بيانات صفحة التقارير.</p></div><div className="flex-1 space-y-3 overflow-y-auto p-5">{isLoading ? <p className="text-sm text-slate-500">جارٍ تحميل الرسائل…</p> : messages.length ? messages.map(message => <div key={message.id} className={`max-w-[88%] rounded-2xl p-3 text-sm ${message.message_type === "daily_report" ? "mx-auto w-full border border-brand/20 bg-brand/5" : message.sender_id === me?.id ? "mr-auto bg-brand text-white" : "ml-auto bg-slate-100 dark:bg-slate-800"}`}><div className="mb-1 flex items-center gap-2 text-xs opacity-70">{message.message_type === "daily_report" && <FileText size={14}/>}<span>{message.message_type === "daily_report" ? "تقرير يومي تلقائي" : message.sender_name}</span><span>{new Date(message.created_at).toLocaleString("ar-SA")}</span></div><p className="whitespace-pre-wrap">{message.body}</p></div>) : <p className="py-16 text-center text-sm text-slate-500">ابدأ المحادثة بإرسال رسالة.</p>}</div><form onSubmit={event => { event.preventDefault(); if (body.trim() && !send.isPending) send.mutate(); }} className="flex gap-2 border-t p-4"><textarea value={body} onChange={event => setBody(event.target.value)} placeholder="اكتب رسالتك…" rows={2} className="min-w-0 flex-1 resize-none rounded-xl border bg-transparent p-3 text-sm"/><button disabled={!selectedId || !body.trim() || send.isPending} className="self-end rounded-xl bg-brand p-3 text-white disabled:opacity-50" aria-label="إرسال"><Send size={18}/></button></form></div>
  </section>;
}
