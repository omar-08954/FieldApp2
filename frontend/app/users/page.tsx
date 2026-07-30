import { Shell } from "@/components/shell"; import { UsersPanel } from "@/components/operations-panels";
export default function UsersPage() { return <Shell><div className="mb-6"><h1 className="text-2xl font-bold">إدارة المستخدمين</h1><p className="mt-1 text-slate-500">إضافة وتعديل وتعطيل الحسابات من مساحة واحدة.</p></div><UsersPanel/></Shell>; }
