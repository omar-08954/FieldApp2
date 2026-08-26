const key = "fieldapp.access_token";
const refreshKey = "fieldapp.refresh_token";
const storage = () => window.sessionStorage;
export const token = () => {
  if (typeof window === "undefined") return null;
  // Remove tokens created by older releases so reopening the app cannot reuse them.
  window.localStorage.removeItem(key);
  return storage().getItem(key);
};
export const refreshToken = () => {
  if (typeof window === "undefined") return null;
  window.localStorage.removeItem(refreshKey);
  return storage().getItem(refreshKey);
};
export const authHeaders = (): Record<string, string> => {
  const accessToken = token();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};
export const saveToken = (value: string) => storage().setItem(key, value);
export const saveSession = (accessToken: string, nextRefreshToken: string) => {
  storage().setItem(key, accessToken);
  storage().setItem(refreshKey, nextRefreshToken);
};
export const clearToken = () => {
  storage().removeItem(key);
  storage().removeItem(refreshKey);
  window.localStorage.removeItem(key);
  window.localStorage.removeItem(refreshKey);
};
