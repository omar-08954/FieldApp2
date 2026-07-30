import { Shell } from "@/components/shell"; import { LegacyTabs, TabPlaceholder } from "@/components/legacy-tabs";
const tabs=["📊 لوحة الحالة","👥 المستخدمون","📋 المهام","📦 المستودع","📜 سجل العمليات","⚠️ سجل الأخطاء","🧹 الصيانة","📈 الأداء","⚙️ إعدادات المطور","🤖 مساعد المطور"];
export default function DeveloperPage() { return <Shell><h1 className="mb-6 text-2xl font-bold">مركز المطور</h1><LegacyTabs tabs={tabs.map(label=>({label,content:<TabPlaceholder title={label} description="أدوات وتشخيصات النظام للمدير فقط."/>}))}/></Shell>; }
