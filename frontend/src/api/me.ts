/**
 * Current-user API functions — GET/PATCH /api/me/ and POST /api/me/change-password.
 */
import { apiGet, apiPatch, apiPost } from "./client";
import type { ChangePasswordPayload, UpdateMePayload, User } from "./types";

export function getMe(): Promise<User> {
  return apiGet<User>("/me/");
}

export function updateMe(payload: UpdateMePayload): Promise<User> {
  return apiPatch<User>("/me/", payload);
}

export function changePassword(payload: ChangePasswordPayload): Promise<void> {
  return apiPost<void>("/me/change-password/", payload);
}
