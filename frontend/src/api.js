const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "micromanus_token";
const REFRESH_KEY = "micromanus_refresh";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const setRefreshToken = (token) => localStorage.setItem(REFRESH_KEY, token);
export function consumeAuthHash() {
  const hash = window.location.hash || "";
  if (!hash.startsWith("#token=")) return false;
  const params = new URLSearchParams(hash.slice(1));
  const token = params.get("token");
  if (!token) return false;

  setToken(token);
  const refreshToken = params.get("refresh");
  if (refreshToken) setRefreshToken(refreshToken);
  // Remove sensitive tokens from the address bar/history entry.
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  return true;
}
export const clearToken = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
};

export function oauthUrl(provider) {
  return `${API_URL}/auth/${provider}/login`;
}

async function tryRefresh() {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return false;
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  setToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return true;
}

export async function apiFetch(path, options = {}, retried = false) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    if (!retried && (await tryRefresh())) return apiFetch(path, options, true);
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const err = new Error(body.detail || "Request failed");
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export function apiStream(path, body) {
  const token = getToken();
  return fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}

export async function downloadPdf(threadId, messageId) {
  const res = await fetch(`${API_URL}/threads/${threadId}/messages/${messageId}/pdf`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("PDF export failed");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = "micromanus-report.pdf";
  a.click();
  URL.revokeObjectURL(url);
}

export { API_URL };
