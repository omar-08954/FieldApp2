import { authHeaders, clearToken, refreshToken, saveSession } from "./auth";
const configuredBase = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
export const apiBase = configuredBase.endsWith("/api/v1") ? configuredBase : `${configuredBase.replace(/\/$/, "")}/api/v1`;
export type Summary = { total_tasks: number; completion_rate: number; delayed_tasks: number; needs_review: number; by_status: { label: string; value: number }[]; daily_trend: { label: string; value: number }[]; latest_tasks: { id:number; task_number:string; technician_name:string; task_status:string; execution_date:string }[]; top_technicians: { label:string; value:number }[] };
type ApiError = { detail?: string };

async function responseError(response: Response): Promise<Error> {
  const payload = await response.json().catch(() => null) as ApiError | null;
  return new Error(payload?.detail || "تعذر إتمام الطلب. حاول مرة أخرى.");
}

async function renewSession(): Promise<boolean> {
  const currentRefreshToken = refreshToken();
  if (!currentRefreshToken) return false;
  const response = await fetch(`${apiBase}/auth/refresh`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: currentRefreshToken }),
  });
  if (!response.ok) return false;
  const session = await response.json() as { access_token: string; refresh_token: string };
  saveSession(session.access_token, session.refresh_token);
  return true;
}

export async function api<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && init?.body) headers.set("Content-Type", "application/json");
  for (const [name, value] of Object.entries(authHeaders())) headers.set(name, value);
  const response = await fetch(`${apiBase}${path}`, { ...init, headers });
  if (response.status === 401 && !retried && await renewSession()) return api<T>(path, init, true);
  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") window.location.assign("/login");
  }
  if (!response.ok) throw await responseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
