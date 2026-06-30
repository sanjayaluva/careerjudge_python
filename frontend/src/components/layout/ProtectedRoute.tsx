import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "@/stores/auth";
import { Spinner } from "@/components/ui";

export interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * Wraps a route that requires authentication.
 * If the user has no access token, redirect to /login (preserving the
 * original target as `?from=`).
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }

  return <>{children}</>;
}

export interface PublicRouteProps {
  children: ReactNode;
}

/**
 * Wraps a public route (login/signup). If the user is already authenticated,
 * redirect them to /dashboard.
 */
export function PublicRoute({ children }: PublicRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

/** Loading fallback used by <ProtectedRoute> while /me/ resolves. */
export function FullScreenSpinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center gap-3">
        <Spinner size="lg" />
        <p className="text-sm text-slate-500">{label}</p>
      </div>
    </div>
  );
}
