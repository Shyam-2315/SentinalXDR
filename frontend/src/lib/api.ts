import { toast } from "sonner";
import { authStore } from "./auth";

const RAW_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

function normalizeBaseUrl(value: string) {
  const url = new URL(value);
  url.pathname = url.pathname.replace(/\/+$/, "").replace(/\/api\/v1$/, "").replace(/\/api$/, "");
  return url.toString().replace(/\/$/, "");
}

const BASE_URL = normalizeBaseUrl(RAW_BASE_URL);

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

type RequestOpts = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  auth?: boolean;
  silent?: boolean;
  headers?: Record<string, string>;
};

function buildUrl(path: string, query?: RequestOpts["query"]) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(path.startsWith("http") ? path : `${BASE_URL}${normalizedPath}`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null || v === "") continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

function onUnauthorized() {
  authStore.clear();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

export async function apiRequest<T = unknown>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { method = "GET", body, query, auth = true, silent, headers = {} } = opts;
  const finalHeaders: Record<string, string> = { Accept: "application/json", ...headers };
  if (body !== undefined && !(body instanceof FormData)) {
    finalHeaders["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = authStore.getAccess();
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }
  let res: Response;
  try {
    res = await fetch(buildUrl(path, query), {
      method,
      headers: finalHeaders,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
  } catch (err) {
    if (!silent) toast.error("Network error: unable to reach API");
    throw new ApiError(0, "Network error", err);
  }

  if (res.status === 401 && auth) {
    onUnauthorized();
    throw new ApiError(401, "Unauthorized");
  }

  const ct = res.headers.get("content-type") ?? "";
  const data: unknown = ct.includes("application/json")
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);

  if (!res.ok) {
    const msg =
      (data && typeof data === "object" && "detail" in (data as Record<string, unknown>)
        ? String((data as Record<string, unknown>).detail)
        : null) ?? `Request failed (${res.status})`;
    if (!silent) toast.error(msg);
    throw new ApiError(res.status, msg, data);
  }
  return data as T;
}

export const api = {
  get: <T = unknown>(path: string, opts: Omit<RequestOpts, "method" | "body"> = {}) =>
    apiRequest<T>(path, { ...opts, method: "GET" }),
  post: <T = unknown>(path: string, body?: unknown, opts: Omit<RequestOpts, "method"> = {}) =>
    apiRequest<T>(path, { ...opts, method: "POST", body }),
  patch: <T = unknown>(path: string, body?: unknown, opts: Omit<RequestOpts, "method"> = {}) =>
    apiRequest<T>(path, { ...opts, method: "PATCH", body }),
  put: <T = unknown>(path: string, body?: unknown, opts: Omit<RequestOpts, "method"> = {}) =>
    apiRequest<T>(path, { ...opts, method: "PUT", body }),
  del: <T = unknown>(path: string, opts: Omit<RequestOpts, "method" | "body"> = {}) =>
    apiRequest<T>(path, { ...opts, method: "DELETE" }),
};

export { BASE_URL };
