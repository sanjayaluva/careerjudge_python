/**
 * axios instance with JWT interceptors.
 *
 *  - Request interceptor: attaches `Authorization: Bearer <access>` if a token
 *    is present in the auth store.
 *  - Response interceptor: extracts the standard envelope error shape, and
 *    handles 401s by attempting a single refresh, then re-running the request.
 *    If refresh fails, the user is redirected to /login and the store cleared.
 *
 * The store is imported dynamically to avoid a circular dependency:
 * auth.ts -> client.ts -> auth store -> ...
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

import { API_BASE_URL } from "@/lib/constants";
import type { ApiErrorEnvelope, ApiSuccessEnvelope, TokenRefreshResponse } from "./types";

const STORAGE_KEY = "cj_auth_v1";

interface StoredAuth {
  accessToken: string;
  refreshToken: string;
  user: unknown;
}

function readStoredAuth(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

/** Lazily-imported store accessor — avoids circular imports with the Zustand store. */
async function getStore() {
  const mod = await import("@/stores/auth");
  return mod.useAuthStore.getState();
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  // 120s timeout — matches the Caddy reverse_proxy transport timeout.
  // The previous 30s was too short for question saves with large base64
  // images in the JSON payload (bulk options save can take 30-60s).
  timeout: 120_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ---------------------------------------------------------------------------
// Shared refresh state (used by both request + response interceptors)
// ---------------------------------------------------------------------------

let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];

function subscribeTokenRefresh(cb: (token: string | null) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

// ---------------------------------------------------------------------------
// Request: attach Authorization header + proactive token refresh
// ---------------------------------------------------------------------------

/**
 * Decode a JWT payload (without verification — verification happens server-side).
 * Returns null if the token is malformed.
 */
function decodeJwtPayload(token: string): { exp?: number } | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(payload) as { exp?: number };
  } catch {
    return null;
  }
}

/**
 * Check if the current access token will expire within the next 5 minutes.
 * If so, proactively refresh it BEFORE the request goes out — this avoids
 * the 401 → refresh → retry cycle that can cause mid-activity session expiry
 * during long operations like question editing.
 */
const REFRESH_BUFFER_MS = 5 * 60 * 1000; // 5 minutes before expiry

async function ensureFreshAccessToken(): Promise<string | null> {
  const stored = readStoredAuth();
  if (!stored?.accessToken || !stored?.refreshToken) return null;

  const payload = decodeJwtPayload(stored.accessToken);
  if (!payload?.exp) return stored.accessToken; // can't decode — let the request try

  const expiresAt = payload.exp * 1000;
  const now = Date.now();
  const willExpireSoon = expiresAt - now < REFRESH_BUFFER_MS;

  if (!willExpireSoon) return stored.accessToken;

  // Token will expire soon — proactively refresh it.
  // Guard against concurrent refreshes with the same isRefreshing flag
  // used by the response interceptor.
  if (isRefreshing) {
    // Wait for the in-flight refresh to complete, then return the new token.
    return new Promise((resolve) => {
      subscribeTokenRefresh((newToken) => resolve(newToken));
    });
  }

  isRefreshing = true;
  try {
    const refreshRes = await axios.post<TokenRefreshResponse>(
      `${API_BASE_URL}/auth/token/refresh`,
      { refresh: stored.refreshToken },
      { headers: { "Content-Type": "application/json" } },
    );
    const { access, refresh } = refreshRes.data;
    // Update store + localStorage
    try {
      const store = await getStore();
      store.setTokens(access, refresh);
    } catch {
      const cur = readStoredAuth();
      if (cur) {
        cur.accessToken = access;
        cur.refreshToken = refresh;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cur));
      }
    }
    onRefreshed(access);
    return access;
  } catch {
    onRefreshed(null);
    return stored.accessToken; // let the request try with the old token; 401 handler will redirect
  } finally {
    isRefreshing = false;
  }
}

apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Skip proactive refresh for auth endpoints (login, refresh, signup)
    if (!config.url?.includes("/auth/")) {
      const freshToken = await ensureFreshAccessToken();
      if (freshToken && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${freshToken}`;
      }
    } else {
      // For auth endpoints, just attach the stored token if present
      const stored = readStoredAuth();
      const token = stored?.accessToken;
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response: envelope-aware error + 401 auto-refresh (reactive fallback)
// ---------------------------------------------------------------------------

function isApiErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof (payload as { error: unknown }).error === "object"
  );
}

/** Extract a human-readable error message from an axios error. */
export function extractApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (isApiErrorEnvelope(data)) {
      const { message, details } = data.error;
      // If there are field-specific details, include them for clarity
      if (details && typeof details === "object" && Object.keys(details).length > 0) {
        const parts: string[] = [message];
        for (const [field, msgs] of Object.entries(details)) {
          if (Array.isArray(msgs)) {
            parts.push(`${field}: ${(msgs as string[]).join(", ")}`);
          } else if (typeof msgs === "string") {
            parts.push(`${field}: ${msgs}`);
          }
        }
        return parts.join(" — ");
      }
      return message;
    }
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
    if (typeof data === "object" && data !== null) {
      // DRF validation error shape: { field: ["msg", ...] }
      const parts: string[] = [];
      for (const [key, value] of Object.entries(data)) {
        if (Array.isArray(value)) {
          parts.push(`${key}: ${(value as string[]).join(", ")}`);
        } else if (typeof value === "string") {
          parts.push(`${key}: ${value}`);
        }
      }
      if (parts.length > 0) return parts.join("; ");
    }
    // No response received (Network Error / DNS failure) — provide a
    // helpful message. This covers ERR_NAME_NOT_RESOLVED, ERR_NETWORK,
    // ERR_CONNECTION_RESET, etc.
    if (!err.response) {
      const code = (err as { code?: string }).code;
      if (code === "ERR_NAME_NOT_RESOLVED" || err.message === "Network Error") {
        return (
          "Network error — couldn't reach the server (DNS or connection issue). " +
          "Your answers are saved locally. Please check your internet connection " +
          "and try again in a moment."
        );
      }
      return err.message || "Network error — please try again.";
    }
    if (err.message) return err.message;
    return `Request failed with status ${err.response?.status ?? "?"}`;
  }
  if (err instanceof Error) return err.message;
  return "Unknown error";
}

/** Returns the structured error code from the envelope, or null. */
export function extractApiErrorCode(err: unknown): string | null {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (isApiErrorEnvelope(data)) return data.error.code;
  }
  return null;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
      _skipAuthRefresh?: boolean;
      _networkRetryCount?: number;
    };

    // ─── Network-error retry (ERR_NAME_NOT_RESOLVED, ERR_NETWORK, etc.) ───
    // These are transient client-side DNS/connection issues. Retry up to 2
    // times with a short backoff before failing — critical for assessment
    // answer/submit calls where losing data mid-test is unacceptable.
    const isNetworkError =
      !error.response && Boolean(error.request) && error.code !== "ECONNABORTED";
    if (isNetworkError && originalRequest && (originalRequest._networkRetryCount ?? 0) < 2) {
      originalRequest._networkRetryCount = (originalRequest._networkRetryCount ?? 0) + 1;
      // Backoff: 1s, then 2s
      const delayMs = originalRequest._networkRetryCount * 1000;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      return apiClient(originalRequest);
    }

    // 401 -> try to refresh once
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest._skipAuthRefresh &&
      !originalRequest.url?.includes("/auth/")
    ) {
      if (isRefreshing) {
        // Wait for the in-flight refresh to finish, then retry.
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken) => {
            if (!newToken) {
              reject(error);
              return;
            }
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(apiClient(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const stored = readStoredAuth();
        if (!stored?.refreshToken) throw new Error("No refresh token");

        const refreshRes = await axios.post<TokenRefreshResponse>(
          `${API_BASE_URL}/auth/token/refresh`,
          { refresh: stored.refreshToken },
          { headers: { "Content-Type": "application/json" } },
        );

        const { access, refresh } = refreshRes.data;

        // Update store + localStorage
        try {
          const store = await getStore();
          store.setTokens(access, refresh);
        } catch {
          // store unavailable (e.g. during SSR) — patch localStorage directly
          const cur = readStoredAuth();
          if (cur) {
            cur.accessToken = access;
            cur.refreshToken = refresh;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cur));
          }
        }

        onRefreshed(access);
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        onRefreshed(null);
        // Clear store and redirect to /login
        try {
          const store = await getStore();
          store.clear();
        } catch {
          localStorage.removeItem(STORAGE_KEY);
        }
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          window.location.assign("/login?reason=session_expired");
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

// ---------------------------------------------------------------------------
// Helpers — typed request/response wrappers
// ---------------------------------------------------------------------------

/**
 * GET — returns the unwrapped `data` field of the success envelope.
 */
export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await apiClient.get<ApiSuccessEnvelope<T>>(url, config);
  return res.data.data;
}

/** GET that returns a paginated envelope. */
export async function apiGetPaged<T>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<{ count: number; next: string | null; previous: string | null; results: T[] }> {
  const res = await apiClient.get<
    ApiSuccessEnvelope<{
      count: number;
      next: string | null;
      previous: string | null;
      results: T[];
    }>
  >(url, config);
  return res.data.data;
}

/** POST — returns the unwrapped `data`. */
export async function apiPost<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await apiClient.post<ApiSuccessEnvelope<T>>(url, body, config);
  return res.data.data;
}

/** PATCH — returns the unwrapped `data`. */
export async function apiPatch<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await apiClient.patch<ApiSuccessEnvelope<T>>(url, body, config);
  return res.data.data;
}

/** PUT — returns the unwrapped `data`. */
export async function apiPut<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await apiClient.put<ApiSuccessEnvelope<T>>(url, body, config);
  return res.data.data;
}

/** DELETE — returns void (backend sends 200/204). */
export async function apiDelete(url: string, config?: AxiosRequestConfig): Promise<void> {
  await apiClient.delete(url, config);
}

/** Mark a request to skip the auto-refresh (used by login/refresh themselves). */
export function skipAuthRefresh<T extends AxiosRequestConfig>(config: T): T {
  return { ...config, _skipAuthRefresh: true } as T & { _skipAuthRefresh: boolean };
}
