/**
 * Organizations API functions.
 * Endpoints live under /api/organizations/.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

export interface Organization {
  id: number;
  name: string;
  type: "corporate" | "corp_exclusive" | "channel_partner";
  status: "active" | "inactive" | "suspended";
  description: string;
  contact_email: string;
  contact_phone: string;
  website: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  member_count: number;
  group_count: number;
  groups: Group[];
  created_at: string;
  updated_at: string;
}

export interface OrganizationListItem {
  id: number;
  name: string;
  type: string;
  status: string;
  contact_email: string;
  member_count: number;
  group_count: number;
  created_at: string;
}

export interface Group {
  id: number;
  organization: number;
  name: string;
  description: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMember {
  id: number;
  organization: number;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string | null;
  };
  group: number | null;
  is_admin: boolean;
  joined_at: string;
}

export interface CreateOrganizationPayload {
  name: string;
  type: string;
  status?: string;
  description?: string;
  contact_email?: string;
  contact_phone?: string;
  website?: string;
  address_line1?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
}

export interface ListParams {
  page?: number;
  search?: string;
}

const BASE = "/organizations";

export function listOrganizations(params: ListParams = {}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: OrganizationListItem[];
}> {
  return apiGetPaged<OrganizationListItem>(BASE, {
    params: {
      page: params.page ?? 1,
      ...(params.search ? { search: params.search } : {}),
    },
  });
}

export function retrieveOrganization(id: number): Promise<Organization> {
  return apiGet<Organization>(`${BASE}/${id}/`);
}

export function createOrganization(payload: CreateOrganizationPayload): Promise<Organization> {
  return apiPost<Organization>(BASE, payload);
}

export function updateOrganization(
  id: number,
  payload: Partial<CreateOrganizationPayload>,
): Promise<Organization> {
  return apiPatch<Organization>(`${BASE}/${id}/`, payload);
}

export function deleteOrganization(id: number): Promise<void> {
  return apiDelete(`${BASE}/${id}/`);
}

// Groups
export function listGroups(orgId: number): Promise<Group[]> {
  return apiGetPaged<Group>(`${BASE}/${orgId}/groups`).then((r) => r.results);
}

export function createGroup(
  orgId: number,
  payload: { name: string; description?: string },
): Promise<Group> {
  return apiPost<Group>(`${BASE}/${orgId}/groups`, payload);
}

export function deleteGroup(orgId: number, groupId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/groups/${groupId}`);
}

// Members
export function listMembers(orgId: number): Promise<OrganizationMember[]> {
  return apiGetPaged<OrganizationMember>(`${BASE}/${orgId}/members`).then((r) => r.results);
}

export function addMember(
  orgId: number,
  payload: { user_email: string; group_id?: number | null },
): Promise<OrganizationMember> {
  return apiPost<OrganizationMember>(`${BASE}/${orgId}/members`, payload);
}

export function updateMember(
  orgId: number,
  memberId: number,
  payload: { group_id?: number | null; is_admin?: boolean },
): Promise<OrganizationMember> {
  return apiPatch<OrganizationMember>(`${BASE}/${orgId}/members/${memberId}`, payload);
}

export function removeMember(orgId: number, memberId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/members/${memberId}`);
}
