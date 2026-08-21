"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, Bot, ChevronLeft, ClipboardList, Code2, FileSpreadsheet, LayoutDashboard, LogOut, Menu, Moon, Package, Settings, ShieldCheck, Sun, UserCog, Users, Wrench, X } from "lucide-react";
import { useTheme } from "next-themes";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Assistant } from "./assistant";
import { ApiError, api } from "@/lib/api";
import { clearToken, token } from "@/lib/auth";

const links = [
  ["لوحة التحكم", "/dashboard", LayoutDashboard, "admin"], ["لوحة المدير", "/admin", ShieldCheck, "admin"],
  ["المهام", "/tasks", ClipboardList, "admin"], ["صفحة الفني", "/technician", Wrench, "all"],
  ["التقارير", "/reports", FileSpreadsheet, "admin"], ["المستودع", "/inventory", Package, "admin"],
  ["إدارة المستخدمين", "/users", Users, "admin"], ["مركز المطور", "/developer", Code2, "admin"],
  ["مراجعة الاستيراد", "/imports", UserCog, "admin"], ["الإعدادات", "/settings", Settings, "all"],
] as const;

type CurrentUser = { full_name: string; role: string };

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter(); const { resolvedTheme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false);
  const accessToken = token();
  const { data: notifications = [] } = useQuery({ queryKey: ["notifications"], queryFn: () => api<{ id:number; is_read:boolean }[]>("/notifications"), enabled: Boolean(token()) });
  const { data: user, isLoading: userLoading, isError: userError, error: userQueryError } = useQuery({ queryKey: ["current-user"], queryFn: () => api<CurrentUser>("/auth/me"), enabled: Boolean(accessToken), retry: false });
  const adminOnlyPaths = ["/", "/dashboard", "/tasks", "/admin", "/reports", "/inventory", "/users", "/developer", "/imports"];
  useEffect(() => {
    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (userError && userQueryError instanceof ApiError && userQueryError.status === 401) {
      clearToken();
      router.replace("/login");
      return;
    }
    if (user?.role === "technician" && adminOnlyPaths.some(path => pathname === path || pathname.startsWith(`${path}/`))) {
      router.replace("/technician");
    }
  }, [accessToken, pathname, router, user?.role, userError, userQueryError]);
  const unreadCount = notifications.filter(notification => !notification.is_read).length;
  const logout = () => { clearToken(); router.replace("/login"); };
  if (!accessToken || userLoading) return <main className="grid min-h-screen place-items-center p-6 text-sm text-slate-500">جارٍ التحقق من الجلسة…</main>;
  if (userError && !(userQueryError instanceof ApiError && userQueryError.status === 401)) return <main className="grid min-h-screen place-items-center p-6"><div className="panel max-w-md text-center"><h1 className="font-bold">الخدمة غير متاحة مؤقتًا</h1><p className="mt-2 text-sm text-slate-500">لم يتم تسجيل خروجك. أعد المحاولة بعد عودة خدمة API.</p><button onClick={() => window.location.reload()} className="mt-4 rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white">إعادة المحاولة</button></div></main>;
  if (!user || (user.role === "technician" && adminOnlyPaths.some(path => pathname === path || pathname.startsWith(`${path}/`)))) return <main className="grid min-h-screen place-items-center p-6 text-sm text-slate-500">جارٍ التحقق من الصلاحيات…</main>;
  const visibleLinks = links.filter(([, , , access]) => access === "all" || user.role === "admin");
  const sidebar = (mobile = false) => <aside className={`flex h-full flex-col border-l border-slate-200/80 bg-white/85 p-3 shadow-2xl shadow-slate-900/5 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85 ${collapsed && !mobile ? "w-[76px]" : "w-64"}`}>
    <div className="mb-6 flex items-center justify-between px-1"><Link href="/" className="flex items-center gap-2 overflow-hidden font-bold"><span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand text-white shadow-lg shadow-indigo-500/30">F</span>{(!collapsed || mobile) && <span>FieldApp</span>}</Link>{!mobile && <button onClick={() => setCollapsed(!collapsed)} className="hidden rounded-lg p-2 hover:bg-slate-100 md:block dark:hover:bg-slate-800" aria-label="طي الشريط"><ChevronLeft className={collapsed ? "rotate-180" : ""} size={18}/></button>}<button onClick={() => setMobileOpen(false)} className="rounded-lg p-2 lg:hidden" aria-label="إغلاق القائمة"><X size={18}/></button></div>
    {user && (!collapsed || mobile) && <div className="mb-4 rounded-xl bg-brand/5 px-3 py-2 text-xs"><p className="font-semibold text-slate-700 dark:text-slate-200">{user.full_name}</p><p className="mt-0.5 text-slate-500">{user.role === "technician" ? "فني" : "مدير النظام"}</p></div>}
    <nav className="space-y-1">{visibleLinks.map(([label, href, Icon]) => { const active = pathname === href || (href === "/dashboard" && pathname === "/"); return <Link title={label} onClick={() => setMobileOpen(false)} key={href} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${active ? "bg-brand text-white shadow-lg shadow-indigo-500/20" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}><Icon className="shrink-0" size={18}/>{(!collapsed || mobile) && <span className="truncate">{label}</span>}</Link>; })}</nav>
    <div className="mt-auto space-y-2 border-t border-slate-200 pt-3 dark:border-slate-800">
      <Link href="/notifications" title="الإشعارات" className="relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"><Bell size={18}/>{(!collapsed || mobile) && <span>الإشعارات</span>}{unreadCount > 0 && <span className="mr-auto grid min-w-5 place-items-center rounded-full bg-red-500 px-1 text-[10px] leading-5 text-white">{unreadCount > 9 ? "9+" : unreadCount}</span>}</Link>
      <Assistant compact={collapsed && !mobile}/>
      <button onClick={logout} title="تسجيل الخروج" className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-red-600 transition hover:bg-red-50 dark:hover:bg-red-950/30"><LogOut size={18}/>{(!collapsed || mobile) && "تسجيل الخروج"}</button>
      {(!collapsed || mobile) && <p className="px-2 pt-1 text-[11px] text-slate-400">● النظام متصل</p>}
    </div>
  </aside>;
  return <div className="min-h-screen lg:flex"><div className="sticky top-0 hidden h-screen lg:block">{sidebar()}</div><AnimatePresence>{mobileOpen && <><motion.button aria-label="إغلاق القائمة" className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden" onClick={() => setMobileOpen(false)} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}/><motion.div className="fixed inset-y-0 right-0 z-50 lg:hidden" initial={{x:300}} animate={{x:0}} exit={{x:300}} transition={{type:"spring", damping:28, stiffness:280}}>{sidebar(true)}</motion.div></>}</AnimatePresence><div className="min-w-0 flex-1"><header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/75 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/75"><div className="flex h-16 items-center gap-3 px-4 sm:px-7"><button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 lg:hidden" aria-label="فتح القائمة"><Menu size={20}/></button><div className="hidden flex-1 md:block"><p className="text-sm text-slate-500">إدارة العمليات الميدانية</p></div><div className="mr-auto flex items-center gap-1"><button onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="تبديل المظهر">{resolvedTheme === "dark" ? <Sun size={19}/> : <Moon size={19}/>}</button><Link href="/notifications" className="relative rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="الإشعارات"><Bell size={19}/>{unreadCount>0&&<span className="absolute -left-1 -top-1 grid min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] leading-4 text-white">{unreadCount>9?"9+":unreadCount}</span>}</Link><button onClick={() => document.getElementById("fieldapp-assistant-trigger")?.click()} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="المساعد الذكي"><Bot size={19}/></button></div></div></header><main className="mx-auto w-full max-w-[1680px] p-4 sm:p-7">{children}</main></div></div>;
}
