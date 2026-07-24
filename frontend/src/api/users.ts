/**
 * Admin user-management API functions.
 * Endpoints live under /api/accounts/.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";
import type {
  AdminCreateUserPayload,
  AdminUpdateUserPayload,
  AdminUserListParams,
  AssignRolePayload,
  User,
} from "./types";

export function listUsers(params: AdminUserListParams = {}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: User[];
}> {
  return apiGetPaged<User>("/accounts/users/", {
    params: {
      page: params.page ?? 1,
      ...(params.search ? { search: params.search } : {}),
      ...(params.role ? { role: params.role } : {}),
      ...(params.page_size ? { page_size: params.page_size } : {}),
    },
  });
}

export function createUser(payload: AdminCreateUserPayload): Promise<User> {
  return apiPost<User>("/accounts/users/", payload);
}

export function retrieveUser(id: number): Promise<User> {
  return apiGet<User>(`/accounts/users/${id}/`);
}

export function updateUser(id: number, payload: AdminUpdateUserPayload): Promise<User> {
  return apiPatch<User>(`/accounts/users/${id}/`, payload);
}

export function deleteUser(id: number): Promise<void> {
  return apiDelete(`/accounts/users/${id}/`);
}

export function assignRole(id: number, payload: AssignRolePayload): Promise<User> {
  return apiPost<User>(`/accounts/users/${id}/assign-role/`, payload);
}
