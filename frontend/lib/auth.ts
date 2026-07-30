const key = "fieldapp.access_token";
export const token = () => typeof window === "undefined" ? null : window.localStorage.getItem(key);
export const authHeaders = (): Record<string, string> => {
  const accessToken = token();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};
export const saveToken = (value: string) => window.localStorage.setItem(key, value);
export const clearToken = () => window.localStorage.removeItem(key);
