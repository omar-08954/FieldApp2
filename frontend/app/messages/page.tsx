import { Shell } from "@/components/shell";
import { MessagesPage } from "@/components/messages-page";

export default function MessagesRoute() { return <Shell><div className="mb-6"><h1 className="text-2xl font-bold">الرسائل والتقارير اليومية</h1><p className="mt-1 text-slate-500">محادثة مباشرة بين الفني والمدير مع تقرير مهام يومي تلقائي.</p></div><MessagesPage /></Shell>; }
