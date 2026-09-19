/**
 * usePermissions — knows whether the current user can see a given module /
 * perform a given action, derived from the effective `module_rights` the
 * backend returns on /api/me (the RBAC single source of truth — see
 * ModuleRight in apps/accounts/models.py).
 *
 * A module is visible when EITHER:
 *   - the static MODULE_VISIBILITY map says so for the user's role name
 *     (keeps today's behavior for every seeded role, and is the only signal
 *     available for "dashboard" / "profile" / "roles", which have no direct
 *     backend module), OR
 *   - the user's module_rights include a grant for that module's backend
 *     equivalent (MODULE_KEY_BACKEND_MODULE) — this is what makes custom
 *     roles and admin-granted ModuleRights (that aren't in the static map)
 *     actually show up in the UI.
 *
 * When module_rights is absent (e.g. /api/me hasn't resolved yet), this
 * degrades to the old purely-static behavior — nothing crashes.
 */
import { useMemo } from "react";

import type { ModuleAction, ModuleRightGrant } from "@/api/types";
import {
  ADMIN_ONLY_MODULES,
  MODULE_KEY_BACKEND_MODULE,
  MODULE_VISIBILITY,
  type ModuleKey,
  type RoleName,
} from "@/lib/constants";
import { useAuthStore } from "@/stores/auth";

export interface UsePermissionsResult {
  role: RoleName | null;
  /** True if the current user can see the given module. */
  can: (module: ModuleKey) => boolean;
  /** True if the current user's role grants a specific action on a module. */
  canPerform: (module: ModuleKey, action: ModuleAction) => boolean;
  /** True if the current user is a cj_admin. */
  isSuperAdmin: boolean;
  /** List of modules visible to the current user. */
  visibleModules: ModuleKey[];
  /** Raw effective module_rights from /api/me, if loaded yet. */
  moduleRights: ModuleRightGrant[] | undefined;
}

// cj_admin is seeded with every module — reuse its static list as the
// canonical "all module keys" set for iteration below.
const EVERY_MODULE_KEY: ModuleKey[] = MODULE_VISIBILITY.cj_admin;

// Every authenticated user sees these regardless of role/grants — they have
// no backend ModuleRight equivalent to derive from.
// dashboard/profile are universal; "concerns" (Contact Admin) and "messaging"
// (Send Message) are signed universal user capabilities (User Details.pdf p.1),
// available to every authenticated role including the Individual User.
const ALWAYS_VISIBLE_MODULES: ModuleKey[] = ["dashboard", "profile", "concerns", "messaging"];

function isModuleVisible(
  module: ModuleKey,
  role: RoleName,
  moduleRights: ModuleRightGrant[] | undefined,
): boolean {
  if (ALWAYS_VISIBLE_MODULES.includes(module)) return true;
  if ((MODULE_VISIBILITY[role] ?? []).includes(module)) return true;
  if (!moduleRights) return false;
  // "roles" has no backend module (role management rides on "accounts", same
  // as "users") — it's cj_admin-only by product decision, not by grant, so
  // the static map above is the only source of truth for it.
  const backendModule = MODULE_KEY_BACKEND_MODULE[module];
  if (!backendModule) return false;
  return moduleRights.some((right) => right.module === backendModule);
}

export function usePermissions(): UsePermissionsResult {
  const user = useAuthStore((s) => s.user);
  const role = user?.role ?? null;
  const moduleRights = user?.module_rights;

  return useMemo(() => {
    if (!role) {
      return {
        role: null,
        can: () => false,
        canPerform: () => false,
        isSuperAdmin: false,
        visibleModules: [],
        moduleRights,
      };
    }
    const visible = EVERY_MODULE_KEY.filter((m) => isModuleVisible(m, role, moduleRights));
    return {
      role,
      can: (module: ModuleKey) => isModuleVisible(module, role, moduleRights),
      canPerform: (module: ModuleKey, action: ModuleAction) => {
        if (!moduleRights) return isModuleVisible(module, role, moduleRights);
        const backendModule = MODULE_KEY_BACKEND_MODULE[module];
        if (!backendModule) return isModuleVisible(module, role, moduleRights);
        return moduleRights.some(
          (right) => right.module === backendModule && right.action === action,
        );
      },
      isSuperAdmin: role === "cj_admin",
      visibleModules: visible,
      moduleRights,
    };
  }, [role, moduleRights]);
}

/** Module-level helpers — convenient for protecting entire routes. */
export function canAccessModule(
  role: RoleName | null,
  module: ModuleKey,
  moduleRights?: ModuleRightGrant[],
): boolean {
  if (!role) return false;
  return isModuleVisible(module, role, moduleRights);
}

export function isAdminOnly(module: ModuleKey): boolean {
  return ADMIN_ONLY_MODULES.includes(module);
}
