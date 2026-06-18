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

export interface AuthOrganization {
  id?: string;
  name?: string;
  [k: string]: unknown;
}

type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
  organization?: AuthOrganization;
};

type RefreshResponse = {
  access_token: string;
  token_type: string;
};

interface AuthCtx {
  user: AuthUser | null;
  organization: AuthOrganization | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | undefined>(undefined);

type RegisterPayload = {
  email: string;
  password: string;
  display_name: string;
  organization_name?: string;
  organization_id?: string;
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [organization, setOrganization] = useState<AuthOrganization | null>(null);
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
      setOrganization(me.organization ?? null);
      authStore.set({ user: me.user, organization: me.organization });
    } catch {
      setUser(null);
      setOrganization(null);
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
        organization: res.organization,
      });
      setUser(res.user);
      setOrganization(res.organization ?? null);
      await fetchMe();
    },
    [fetchMe],
  );

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const body: RegisterPayload = {
        email: payload.email,
        password: payload.password,
        display_name: payload.display_name.trim(),
      };
      const organizationName = payload.organization_name?.trim();
      const organizationId = payload.organization_id?.trim();
      if (organizationName) body.organization_name = organizationName;
      if (organizationId) body.organization_id = organizationId;

      const res = await api.post<AuthResponse>("/api/auth/register", body, {
        auth: false,
        silent: true,
      });
      if (res?.access_token) {
        authStore.set({
          access_token: res.access_token,
          refresh_token: res.refresh_token,
          user: res.user,
          organization: res.organization,
        });
        setUser(res.user);
        setOrganization(res.organization ?? null);
        await fetchMe();
      }
    },
    [fetchMe],
  );

  const refresh = useCallback(async () => {
    const refreshToken = authStore.getRefresh();
    if (!refreshToken) {
      authStore.clear();
      setUser(null);
      setOrganization(null);
      return;
    }
    const res = await api.post<RefreshResponse>(
      "/api/auth/refresh",
      { refresh_token: refreshToken },
      { auth: false },
    );
    authStore.set({ access_token: res.access_token });
    await fetchMe();
  }, [fetchMe]);

  const logout = useCallback(async () => {
    try {
      await api.post("/api/auth/logout", {}, { silent: true });
    } catch {
      // ignore
    }
    authStore.clear();
    setUser(null);
    setOrganization(null);
    if (typeof window !== "undefined") window.location.href = "/login";
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      organization,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      refresh,
    }),
    [user, organization, loading, login, register, logout, refresh],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
