import { Shell } from "@/components/shell";
import { OperationsAnalytics } from "@/components/operations-analytics";

export default function AnalyticsPage() { return <Shell><div className="mb-6"><h1 className="text-2xl font-bold">الذكاء التشغيلي</h1><p className="mt-1 text-slate-500">مؤشرات الإنجاز، التأخير، ضغط الفنيين ورضا العملاء.</p></div><OperationsAnalytics /></Shell>; }
