const key = "fieldapp.access_token";
const refreshKey = "fieldapp.refresh_token";
const userKey = "fieldapp.current_user";
// Keep the session available when the installed PWA is reopened offline.
const storage = () => window.localStorage;
export type CachedUser = { id: number; username: string; full_name: string; role: string; city?: string | null };
export const token = () => {
  if (typeof window === "undefined") return null;
  return storage().getItem(key);
};
export const refreshToken = () => {
  if (typeof window === "undefined") return null;
  return storage().getItem(refreshKey);
};
export const authHeaders = (): Record<string, string> => {
  const accessToken = token();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};
export const saveToken = (value: string) => storage().setItem(key, value);
export const saveSession = (accessToken: string, nextRefreshToken: string, user?: CachedUser) => {
  storage().setItem(key, accessToken);
  storage().setItem(refreshKey, nextRefreshToken);
  if (user) storage().setItem(userKey, JSON.stringify(user));
};
export const currentUser = (): CachedUser | null => {
  if (typeof window === "undefined") return null;
  try { const value = storage().getItem(userKey); return value ? JSON.parse(value) as CachedUser : null; } catch { return null; }
};
export const clearToken = () => {
  storage().removeItem(key);
  storage().removeItem(refreshKey);
  storage().removeItem(userKey);
  window.localStorage.removeItem(key);
  window.localStorage.removeItem(refreshKey);
};
