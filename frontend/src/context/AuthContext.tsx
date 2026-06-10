import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import { authStore } from "@/lib/auth";

export interface AuthUser {
  id?: string;
  email?: string;
  username?: string;
  full_name?: string;
  display_name?: string;
  role?: string;
  [k: string]: unknown;
}

type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
  organization?: Record<string, unknown>;
};

interface AuthCtx {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: Record<string, unknown>) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    if (!authStore.getAccess()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.get<{ user: AuthUser; organization?: Record<string, unknown> }>(
        "/api/auth/me",
        { silent: true },
      );
      setUser(me.user);
      authStore.set({ user: me.user });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchMe();
  }, [fetchMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.post<AuthResponse>(
        "/api/auth/login",
        { email, password },
        { auth: false },
      );
      authStore.set({
        access_token: res.access_token,
        refresh_token: res.refresh_token,
        user: res.user,
      });
      setUser(res.user);
      await fetchMe();
    },
    [fetchMe],
  );

  const register = useCallback(
    async (payload: Record<string, unknown>) => {
      const displayName = String(
        payload.display_name ?? payload.full_name ?? payload.username ?? payload.email ?? "",
      ).trim();
      const res = await api.post<AuthResponse>(
        "/api/auth/register",
        {
          email: payload.email,
          password: payload.password,
          display_name: displayName || "SentinelXDR User",
          organization_name: payload.organization_name ?? "SentinelXDR Organization",
        },
        { auth: false },
      );
      if (res?.access_token) {
        authStore.set({
          access_token: res.access_token,
          refresh_token: res.refresh_token,
          user: res.user,
        });
        setUser(res.user);
        await fetchMe();
      }
    },
    [fetchMe],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/api/auth/logout", {}, { silent: true });
    } catch {
      // ignore
    }
    authStore.clear();
    setUser(null);
    if (typeof window !== "undefined") window.location.href = "/login";
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      refresh: fetchMe,
    }),
    [user, loading, login, register, logout, fetchMe],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
