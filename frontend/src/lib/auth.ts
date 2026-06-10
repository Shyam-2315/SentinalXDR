const ACCESS = "sxdr.access_token";
const REFRESH = "sxdr.refresh_token";
const USER = "sxdr.user";

export const authStore = {
  getAccess(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS);
  },
  getRefresh(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH);
  },
  getUser<T = unknown>(): T | null {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(USER);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      localStorage.removeItem(USER);
      return null;
    }
  },
  set(tokens: { access_token?: string; refresh_token?: string; user?: unknown }) {
    if (typeof window === "undefined") return;
    if (tokens.access_token) localStorage.setItem(ACCESS, tokens.access_token);
    if (tokens.refresh_token) localStorage.setItem(REFRESH, tokens.refresh_token);
    if (tokens.user) localStorage.setItem(USER, JSON.stringify(tokens.user));
  },
  clear() {
    if (typeof window === "undefined") return;
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
    localStorage.removeItem(USER);
  },
};
