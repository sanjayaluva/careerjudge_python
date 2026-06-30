/**
 * usePermissions — small helper that knows whether the current user can see
 * a given module, based on the static MODULE_VISIBILITY map in constants.ts.
 */
import { useMemo } from "react";

import {
  ADMIN_ONLY_MODULES,
  MODULE_VISIBILITY,
  type ModuleKey,
  type RoleName,
} from "@/lib/constants";
import { useAuthStore } from "@/stores/auth";

export interface UsePermissionsResult {
  role: RoleName | null;
  /** True if the current user can see the given module. */
  can: (module: ModuleKey) => boolean;
  /** True if the current user is a cj_admin. */
  isSuperAdmin: boolean;
  /** List of modules visible to the current user. */
  visibleModules: ModuleKey[];
}

export function usePermissions(): UsePermissionsResult {
  const user = useAuthStore((s) => s.user);
  const role = user?.role ?? null;

  return useMemo(() => {
    if (!role) {
      return { role: null, can: () => false, isSuperAdmin: false, visibleModules: [] };
    }
    const visible = MODULE_VISIBILITY[role] ?? [];
    return {
      role,
      can: (module: ModuleKey) => visible.includes(module),
      isSuperAdmin: role === "cj_admin",
      visibleModules: visible,
    };
  }, [role]);
}

/** Module-level helpers — convenient for protecting entire routes. */
export function canAccessModule(role: RoleName | null, module: ModuleKey): boolean {
  if (!role) return false;
  return (MODULE_VISIBILITY[role] ?? []).includes(module);
}

export function isAdminOnly(module: ModuleKey): boolean {
  return ADMIN_ONLY_MODULES.includes(module);
}
