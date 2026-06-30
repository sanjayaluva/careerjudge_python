/**
 * Zustand auth store — persists tokens + user to localStorage.
 *
 * Persists to localStorage manually (instead of `persist` middleware) so that
 * the api/client.ts interceptor can read it via the same key (cj_auth_v1)
 * without dragging in the whole store bundle.
 */
import { create } from "zustand";

import type { AuthUser, LoginResponse } from "@/api/types";

const STORAGE_KEY = "cj_auth_v1";

interface PersistedShape {
  accessToken: string;
  refreshToken: string;
  user: AuthUser | null;
}

function loadPersisted(): PersistedShape {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { accessToken: "", refreshToken: "", user: null };
    const parsed = JSON.parse(raw) as Partial<PersistedShape>;
    return {
      accessToken: parsed.accessToken ?? "",
      refreshToken: parsed.refreshToken ?? "",
      user: parsed.user ?? null,
    };
  } catch {
    return { accessToken: "", refreshToken: "", user: null };
  }
}

function persist(state: PersistedShape) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota errors */
  }
}

function clearPersisted() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export interface AuthState {
  user: AuthUser | null;
  accessToken: string;
  refreshToken: string;
  isAuthenticated: boolean;

  /** Store the tokens + user from a successful login response. */
  login: (response: LoginResponse) => void;
  /** Replace tokens only (used by the auto-refresh interceptor). */
  setTokens: (access: string, refresh: string) => void;
  /** Replace just the user object (used after /me/ fetch). */
  setUser: (user: AuthUser) => void;
  /** Clear all auth state + localStorage. */
  clear: () => void;
  /** Re-hydrate from localStorage (call on app boot). */
  hydrate: () => void;
}

const initial = loadPersisted();

export const useAuthStore = create<AuthState>((set) => ({
  user: initial.user,
  accessToken: initial.accessToken,
  refreshToken: initial.refreshToken,
  isAuthenticated: Boolean(initial.accessToken),

  login: (response) => {
    const next: PersistedShape = {
      accessToken: response.access,
      refreshToken: response.refresh,
      user: response.user,
    };
    persist(next);
    set({
      accessToken: response.access,
      refreshToken: response.refresh,
      user: response.user,
      isAuthenticated: true,
    });
  },

  setTokens: (access, refresh) => {
    const cur = loadPersisted();
    const next: PersistedShape = { ...cur, accessToken: access, refreshToken: refresh };
    persist(next);
    set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
  },

  setUser: (user) => {
    const cur = loadPersisted();
    const next: PersistedShape = { ...cur, user };
    persist(next);
    set({ user });
  },

  clear: () => {
    clearPersisted();
    set({ user: null, accessToken: "", refreshToken: "", isAuthenticated: false });
  },

  hydrate: () => {
    const p = loadPersisted();
    set({
      user: p.user,
      accessToken: p.accessToken,
      refreshToken: p.refreshToken,
      isAuthenticated: Boolean(p.accessToken),
    });
  },
}));
