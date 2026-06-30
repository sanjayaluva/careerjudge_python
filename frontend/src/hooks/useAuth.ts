/**
 * useAuth — convenience hook wrapping the Zustand auth store +
 * TanStack Query for /me/. Returns the current user (from the store),
 * plus loading/error flags for the /me/ fetch, and helper actions.
 */
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { getMe } from "@/api/me";
import type { AuthUser, User } from "@/api/types";
import { useAuthStore } from "@/stores/auth";

export interface UseAuthResult {
  /** The slim auth user from the login response (always present when authed). */
  user: AuthUser | null;
  /** The full /me/ payload (null while loading). */
  me: User | null;
  isAuthenticated: boolean;
  isLoadingMe: boolean;
  meError: unknown;
  refresh: () => void;
}

export function useAuth(): UseAuthResult {
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const query = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: Boolean(accessToken),
    staleTime: 60_000,
    retry: false,
  });

  // Sync the full user back into the store whenever /me/ succeeds.
  useEffect(() => {
    if (query.data) {
      const next: AuthUser = {
        id: query.data.id,
        email: query.data.email,
        full_name: query.data.full_name,
        role: query.data.role,
        is_email_verified: query.data.is_email_verified,
      };
      // Only update if the snapshot changed (avoid render loop).
      const cur = useAuthStore.getState().user;
      if (
        !cur ||
        cur.id !== next.id ||
        cur.full_name !== next.full_name ||
        cur.role !== next.role ||
        cur.is_email_verified !== next.is_email_verified
      ) {
        setUser(next);
      }
    }
  }, [query.data, setUser]);

  return {
    user,
    me: query.data ?? null,
    isAuthenticated,
    isLoadingMe: query.isLoading,
    meError: query.error,
    refresh: () => query.refetch(),
  };
}
