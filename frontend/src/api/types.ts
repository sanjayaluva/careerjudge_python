/**
 * Shared TypeScript types for the CareerJudge API.
 * Mirrors the backend serializers in apps/accounts/serializers.py.
 */

import type { ModuleKey, RoleName } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Envelope
// ---------------------------------------------------------------------------

export interface ApiSuccessEnvelope<T> {
  message: string;
  data: T;
}

export interface ApiPaginatedEnvelope<T> {
  message: string;
  data: {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
  };
}

export type ApiErrorCode =
  "validation_error" | "unauthorized" | "forbidden" | "server_error" | "not_found" | "throttled";

export interface ApiErrorEnvelope {
  error: {
    code: ApiErrorCode;
    message: string;
    details?: Record<string, unknown>;
  };
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: RoleName | null;
  is_email_verified: boolean;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: AuthUser;
}

export interface SignupResponse {
  email: string;
  user_id: number;
}

export interface TokenRefreshResponse {
  access: string;
  refresh: string;
}

// ---------------------------------------------------------------------------
// User profile (current user — GET /api/me/)
// ---------------------------------------------------------------------------

export type Gender = "" | "male" | "female" | "other" | "prefer_not_to_say";

export interface UserProfile {
  gender: Gender;
  date_of_birth: string | null;
  mobile: string;
  avatar: string | null;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  bio: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  is_active: boolean;
  is_email_verified: boolean;
  is_trial_user: boolean;
  role: RoleName | null;
  profile: UserProfile | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateMePayload {
  full_name?: string;
  phone?: string;
  profile?: Partial<UserProfile>;
}

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
}

// ---------------------------------------------------------------------------
// Admin user management (accounts)
// ---------------------------------------------------------------------------

export interface AdminUserListParams {
  page?: number;
  search?: string;
}

export interface AdminCreateUserPayload {
  email: string;
  full_name: string;
  is_active: boolean;
  is_email_verified: boolean;
  is_trial_user: boolean;
  role: number; // role id
  password?: string;
}

export interface AdminUpdateUserPayload {
  email?: string;
  full_name?: string;
  phone?: string;
  is_active?: boolean;
  is_email_verified?: boolean;
  is_trial_user?: boolean;
  role?: number;
  password?: string;
}

// ---------------------------------------------------------------------------
// Roles & ModuleRights
// ---------------------------------------------------------------------------

export type ModuleAction =
  | "view"
  | "add"
  | "change"
  | "delete"
  | "approve"
  | "reject"
  | "review"
  | "assign"
  | "export"
  | "generate_report"
  | "request_delete";

export interface ModuleRight {
  id: number;
  role: number;
  module: string; // accounts, organizations, etc.
  action: ModuleAction;
  is_inherited?: boolean; // true if inherited from base_role (cannot be removed)
  created_at: string;
}

export interface Role {
  id: number;
  name: string; // system role code OR custom role name
  description: string;
  is_system: boolean; // true for the 10 built-in roles
  is_frozen: boolean; // true for system roles (permissions can't change)
  base_role: number | null; // for custom roles: the system role they inherit from
  base_role_name: string | null;
  rights: ModuleRight[]; // direct rights only
  effective_rights: ModuleRight[]; // direct + inherited
  user_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCustomRolePayload {
  name: string;
  description?: string;
  base_role?: number | null; // system role id to inherit from
}

export interface AssignRolePayload {
  role_id?: number;
  role_name?: string;
}

export interface AssignPermissionPayload {
  module: string;
  action: ModuleAction;
}

export interface RemovePermissionPayload {
  module: string;
  action: ModuleAction;
}

/** All permission tuples known to the system (module, action). */
export interface PermissionCatalogEntry {
  module: ModuleKey;
  label: string;
  actions: ModuleAction[];
}

// ---------------------------------------------------------------------------
// Toast / notification (used by UI)
// ---------------------------------------------------------------------------

export type ToastVariant = "default" | "success" | "error" | "warning";

export interface ToastMessage {
  id: string;
  title?: string;
  description: string;
  variant: ToastVariant;
}
