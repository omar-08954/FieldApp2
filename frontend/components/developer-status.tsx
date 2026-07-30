"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, BellRing, Bot, Database, Users } from "lucide-react";
import { api } from "@/lib/api";

type Status={environment:string;total_users:number;total_tasks:number;pending_import_reviews:number;unread_notifications:number;ai_enabled:boolean};
export function DeveloperStatusPanel(){const {data,isLoading,isError}=useQuery({queryKey:["developer-status"],queryFn:()=>api<Status>("/developer/status")});if(isLoading)return <section className="panel text-sm text-slate-500">جارٍ فحص حالة النظام…</section>;if(isError||!data)return <section className="panel text-sm text-red-600">لا تملك صلاحية الوصول إلى مركز المطور أو تعذر الاتصال بالخدمة.</section>;const cards=[["البيئة",data.environment,Activity],["المستخدمون",data.total_users,Users],["المهام",data.total_tasks,Database],["إشعارات غير مقروءة",data.unread_notifications,BellRing],["الاستيراد المعلّق",data.pending_import_reviews,Activity],["المساعد الذكي",data.ai_enabled?"مفعل":"غير مفعل",Bot]] as const;return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(([label,value,Icon])=><article className="metric" key={label}><div className="flex items-start justify-between"><div><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-2xl font-bold">{value}</p></div><Icon className="text-brand" size={20}/></div></article>)}</div>}
