/**
 * Admin roles & permissions API functions.
 */
import { apiDelete, apiGet, apiGetPaged, apiPost } from "./client";
import type {
  AssignPermissionPayload,
  CreateCustomRolePayload,
  RemovePermissionPayload,
  Role,
} from "./types";

export function listRoles(): Promise<Role[]> {
  // Roles are typically a small list — backend returns paginated; we flatten.
  return apiGetPaged<Role>("/accounts/roles/").then((r) => r.results);
}

export function createCustomRole(payload: CreateCustomRolePayload): Promise<Role> {
  return apiPost<Role>("/accounts/roles/", payload);
}

export function retrieveRole(id: number): Promise<Role> {
  return apiGet<Role>(`/accounts/roles/${id}/`);
}

export function updateRoleDescription(id: number, description: string): Promise<Role> {
  // Only description is editable on custom roles
  return apiGet<Role>(`/accounts/roles/${id}/`).then(() =>
    apiPost<Role>(`/accounts/roles/${id}/`, { description }),
  );
}

export function deleteCustomRole(id: number): Promise<void> {
  return apiDelete(`/accounts/roles/${id}/`);
}

export function assignPermission(
  id: number,
  payload: AssignPermissionPayload,
): Promise<{ id: number; module: string; action: string; is_inherited: boolean }> {
  return apiPost(`/accounts/roles/${id}/assign-permission`, payload);
}

export function removePermission(id: number, payload: RemovePermissionPayload): Promise<void> {
  return apiPost(`/accounts/roles/${id}/remove-permission`, payload);
}

/**
 * Static catalog of (module, action) pairs known to the system.
 * Used by the permission selector UI in role create/edit forms.
 */
export const PERMISSION_CATALOG: {
  module: string;
  label: string;
  actions: string[];
}[] = [
  {
    module: "accounts",
    label: "Accounts",
    actions: ["view", "add", "change", "delete", "assign"],
  },
  {
    module: "organizations",
    label: "Organizations",
    actions: ["view", "add", "change", "delete"],
  },
  {
    module: "question_bank",
    label: "Question Bank",
    actions: ["view", "add", "change", "delete", "approve", "reject", "review", "request_delete"],
  },
  {
    module: "assessment",
    label: "Assessment",
    actions: ["view", "add", "change", "delete", "assign"],
  },
  {
    module: "career_profiling",
    label: "Career Profiling",
    actions: ["view", "add", "change", "export"],
  },
  {
    module: "reporting",
    label: "Reporting",
    actions: ["view", "generate_report", "export"],
  },
  {
    module: "training",
    label: "Training",
    actions: ["view", "add", "change", "delete"],
  },
  {
    module: "counseling",
    label: "Counseling",
    actions: ["view", "add", "change"],
  },
  {
    module: "cms",
    label: "CMS",
    actions: ["view", "add", "change", "delete"],
  },
  {
    module: "notifications",
    label: "Notifications",
    actions: ["view", "add", "change"],
  },
];
