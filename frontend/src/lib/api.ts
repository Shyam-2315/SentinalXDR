import { toast } from "sonner";
import { authStore } from "./auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8010";

function normalizeBaseUrl(value: string) {
  const url = new URL(value);
  url.pathname = url.pathname
    .replace(/\/+$/, "")
    .replace(/\/api\/v1$/, "")
    .replace(/\/api$/, "");
  return url.toString().replace(/\/$/, "");
}

const BASE_URL = normalizeBaseUrl(API_BASE_URL);

export class ApiError extends Error {
  status: number;
  data: unknown;
  endpoint?: string;
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

function extractErrorMessage(data: unknown, fallback: string) {
  if (!data || typeof data !== "object") return fallback;
  const obj = data as Record<string, unknown>;
  const detail = obj.detail ?? obj.message ?? obj.error;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as Record<string, unknown>).msg);
        }
        return "";
      })
      .filter(Boolean)
      .join("; ");
  }
  return fallback;
}

function onUnauthorized() {
  authStore.clear();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

export async function apiRequest<T = unknown>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { method = "GET", body, query, auth = true, silent, headers = {} } = opts;
  const finalUrl = buildUrl(path, query);
  console.log("[API]", method, finalUrl);
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
    res = await fetch(finalUrl, {
      method,
      headers: finalHeaders,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
  } catch (err) {
    console.error("SentinelXDR API network error", { endpoint: finalUrl, err });
    if (!silent) toast.error("Network error: unable to reach API");
    const apiError = new ApiError(0, "Network error: unable to reach API", err);
    apiError.endpoint = finalUrl;
    throw apiError;
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
    const msg = extractErrorMessage(data, `Request failed (${res.status})`);
    console.error("SentinelXDR API request failed", {
      endpoint: finalUrl,
      status: res.status,
      data,
    });
    if (!silent) toast.error(msg);
    const apiError = new ApiError(res.status, msg, data);
    apiError.endpoint = finalUrl;
    throw apiError;
  }
  if (res.status === 204 || data === "") return undefined as T;
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
