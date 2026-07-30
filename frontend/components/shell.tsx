"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, Bot, ChevronLeft, ClipboardList, Code2, FileSpreadsheet, LayoutDashboard, Menu, Moon, Package, Settings, Sun, UserCog, Users, Wrench, X } from "lucide-react";
import { useTheme } from "next-themes";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Assistant } from "./assistant";
import { api } from "@/lib/api";
import { token } from "@/lib/auth";

const links = [
  ["لوحة التحكم", "/dashboard", LayoutDashboard], ["المهام", "/tasks", ClipboardList],
  ["الفنيون", "/technician", Wrench], ["المستخدمون", "/users", Users],
  ["التقارير", "/reports", FileSpreadsheet], ["استيراد Excel", "/imports", FileSpreadsheet], ["المخزون", "/inventory", Package],
  ["مراجعة الاستيراد", "/admin", UserCog], ["الإشعارات", "/notifications", Bell],
  ["الإعدادات", "/settings", Settings], ["مركز المطور", "/developer", Code2],
] as const;

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const { resolvedTheme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false);
  const { data: notifications = [] } = useQuery({ queryKey: ["notifications"], queryFn: () => api<{ id:number; is_read:boolean }[]>("/notifications"), enabled: Boolean(token()) });
  const unreadCount = notifications.filter(notification => !notification.is_read).length;
  const sidebar = (mobile = false) => <aside className={`flex h-full flex-col border-l border-slate-200 bg-white/80 p-3 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/80 ${collapsed && !mobile ? "w-[76px]" : "w-64"}`}>
    <div className="mb-7 flex items-center justify-between px-1"><Link href="/" className="flex items-center gap-2 overflow-hidden font-bold"><span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand text-white">F</span>{(!collapsed || mobile) && <span>FieldApp</span>}</Link>{!mobile && <button onClick={() => setCollapsed(!collapsed)} className="hidden rounded-lg p-2 hover:bg-slate-100 md:block dark:hover:bg-slate-800" aria-label="طي الشريط"><ChevronLeft className={collapsed ? "rotate-180" : ""} size={18}/></button>}<button onClick={() => setMobileOpen(false)} className="rounded-lg p-2 lg:hidden" aria-label="إغلاق القائمة"><X size={18}/></button></div>
    <nav className="space-y-1">{links.map(([label, href, Icon]) => { const active = pathname === href || (href === "/dashboard" && pathname === "/"); return <Link title={label} onClick={() => setMobileOpen(false)} key={href} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${active ? "bg-brand text-white shadow-lg shadow-indigo-500/20" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}><Icon className="shrink-0" size={18}/>{(!collapsed || mobile) && <span className="truncate">{label}</span>}</Link>; })}</nav>
    <div className="mt-auto rounded-xl bg-slate-100/80 p-3 text-xs text-slate-500 dark:bg-slate-900">{(!collapsed || mobile) && <>متصل الآن<br/><span className="text-emerald-600">● النظام يعمل</span></>}</div>
  </aside>;
  return <div className="min-h-screen lg:flex"><div className="sticky top-0 hidden h-screen lg:block">{sidebar()}</div><AnimatePresence>{mobileOpen && <><motion.button aria-label="إغلاق القائمة" className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden" onClick={() => setMobileOpen(false)} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}/><motion.div className="fixed inset-y-0 right-0 z-50 lg:hidden" initial={{x:300}} animate={{x:0}} exit={{x:300}} transition={{type:"spring", damping:28, stiffness:280}}>{sidebar(true)}</motion.div></>}</AnimatePresence><div className="min-w-0 flex-1"><header className="sticky top-0 z-30 border-b bg-white/75 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/75"><div className="flex h-16 items-center gap-3 px-4 sm:px-7"><button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 lg:hidden" aria-label="فتح القائمة"><Menu size={20}/></button><div className="hidden flex-1 md:block"><p className="text-sm text-slate-500">إدارة العمليات الميدانية</p></div><div className="mr-auto flex items-center gap-1"><Assistant/><button onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="تبديل المظهر">{resolvedTheme === "dark" ? <Sun size={19}/> : <Moon size={19}/>}</button><Link href="/notifications" className="relative rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="الإشعارات"><Bell size={19}/>{unreadCount>0&&<span className="absolute -left-1 -top-1 grid min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] leading-4 text-white">{unreadCount>9?"9+":unreadCount}</span>}</Link></div></div></header><main className="mx-auto w-full max-w-[1680px] p-4 sm:p-7">{children}</main></div></div>;
}
