const key = "fieldapp.access_token";
const refreshKey = "fieldapp.refresh_token";
export const token = () => typeof window === "undefined" ? null : window.localStorage.getItem(key);
export const refreshToken = () => typeof window === "undefined" ? null : window.localStorage.getItem(refreshKey);
export const authHeaders = (): Record<string, string> => {
  const accessToken = token();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};
export const saveToken = (value: string) => window.localStorage.setItem(key, value);
export const saveSession = (accessToken: string, nextRefreshToken: string) => {
  window.localStorage.setItem(key, accessToken);
  window.localStorage.setItem(refreshKey, nextRefreshToken);
};
export const clearToken = () => {
  window.localStorage.removeItem(key);
  window.localStorage.removeItem(refreshKey);
};
