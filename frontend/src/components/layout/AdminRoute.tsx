import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { canAccessModule } from "@/hooks/usePermissions";
import { useAuthStore } from "@/stores/auth";
import type { ModuleKey } from "@/lib/constants";

export interface AdminRouteProps {
  /** Module the user must be able to access; defaults to "users". */
  module?: ModuleKey;
  children: ReactNode;
}

/**
 * Wraps a route that requires the current user to have access to a specific
 * module (typically "users" or "roles"). If the user lacks the role, redirect
 * to /dashboard with a denied reason.
 */
export function AdminRoute({ module = "users", children }: AdminRouteProps) {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const role = user?.role ?? null;

  if (!role) {
    return <Navigate to="/dashboard" replace state={{ reason: "no_role" }} />;
  }

  if (!canAccessModule(role, module)) {
    const from = encodeURIComponent(location.pathname);
    return <Navigate to={`/dashboard?denied=${from}`} replace />;
  }

  return <>{children}</>;
}
