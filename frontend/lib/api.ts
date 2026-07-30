import { authHeaders } from "./auth";
const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export type Summary = { total_tasks: number; completion_rate: number; delayed_tasks: number; needs_review: number; by_status: { label: string; value: number }[]; daily_trend: { label: string; value: number }[] };
export async function api<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(`${base}${path}`, { ...init, headers: { "Content-Type": "application/json", ...authHeaders(), ...init?.headers } }); if (!response.ok) throw new Error("تعذر إتمام الطلب. حاول مرة أخرى."); return response.json() as Promise<T>; }
