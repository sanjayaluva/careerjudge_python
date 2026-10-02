/**
 * Organizations API functions.
 * Endpoints live under /api/organizations/.
 */
import { API_BASE_URL } from "@/lib/constants";

import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

export interface Organization {
  id: number;
  name: string;
  type: "corporate" | "corp_exclusive" | "channel_partner";
  status: "active" | "inactive" | "suspended";
  description: string;
  manager_name: string;
  tax_id: string;
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
  region_division: string;
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
  employee_id: string;
  is_admin: boolean;
  joined_at: string;
}

export interface OrganizationAssignment {
  id: number;
  organization: number;
  item_type: "assessment" | "training_course" | "counseling";
  item_id: number;
  assigned_by: number | null;
  assigned_by_name: string | null;
  assigned_at: string;
}

export interface CreateOrganizationPayload {
  name: string;
  type: string;
  status?: string;
  description?: string;
  manager_name?: string;
  tax_id?: string;
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
  return apiGetPaged<OrganizationListItem>(`${BASE}/`, {
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
  return apiPost<Organization>(`${BASE}/`, payload);
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
  return apiGetPaged<Group>(`${BASE}/${orgId}/groups/`).then((r) => r.results);
}

export function createGroup(
  orgId: number,
  payload: { name: string; region_division?: string; description?: string },
): Promise<Group> {
  return apiPost<Group>(`${BASE}/${orgId}/groups/`, payload);
}

export function deleteGroup(orgId: number, groupId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/groups/${groupId}/`);
}

// Members
export function listMembers(orgId: number): Promise<OrganizationMember[]> {
  return apiGetPaged<OrganizationMember>(`${BASE}/${orgId}/members/`).then((r) => r.results);
}

export function addMember(
  orgId: number,
  payload: {
    user_email: string;
    full_name?: string;
    employee_id?: string;
    group_id?: number | null;
  },
): Promise<OrganizationMember> {
  return apiPost<OrganizationMember>(`${BASE}/${orgId}/members/`, payload);
}

export function updateMember(
  orgId: number,
  memberId: number,
  payload: { group_id?: number | null; is_admin?: boolean },
): Promise<OrganizationMember> {
  return apiPatch<OrganizationMember>(`${BASE}/${orgId}/members/${memberId}/`, payload);
}

export function removeMember(orgId: number, memberId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/members/${memberId}/`);
}

// Assignments — CJ Admin assigns published content to an organization so its
// corporate individuals see only what was assigned (CJ_UC030, Doc 4).
export function listAssignments(orgId: number): Promise<OrganizationAssignment[]> {
  return apiGetPaged<OrganizationAssignment>(`${BASE}/${orgId}/assignments/`).then(
    (r) => r.results,
  );
}

export function createAssignment(
  orgId: number,
  payload: { item_type: "assessment" | "training_course" | "counseling"; item_id: number },
): Promise<OrganizationAssignment> {
  return apiPost<OrganizationAssignment>(`${BASE}/${orgId}/assignments/`, payload);
}

export function deleteAssignment(orgId: number, assignmentId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/assignments/${assignmentId}/`);
}

// Schedules (CJ_UC053) — schedule an assessment for employees + notify.
export interface AssessmentSchedule {
  id: number;
  organization: number;
  group: number | null;
  assessment: number;
  assessment_title: string;
  group_name: string | null;
  scheduled_at: string;
  created_by: number | null;
  notified: boolean;
  created_at: string;
}

export function listSchedules(orgId: number): Promise<AssessmentSchedule[]> {
  return apiGetPaged<AssessmentSchedule>(`${BASE}/${orgId}/schedules/`).then((r) => r.results);
}

export function createSchedule(
  orgId: number,
  payload: { assessment: number; scheduled_at: string; group?: number | null },
): Promise<AssessmentSchedule> {
  return apiPost<AssessmentSchedule>(`${BASE}/${orgId}/schedules/`, payload);
}

/** Report 9 #11: reschedule — members are notified again. */
export function rescheduleSchedule(
  orgId: number,
  scheduleId: number,
  payload: { scheduled_at: string },
): Promise<AssessmentSchedule> {
  return apiPatch<AssessmentSchedule>(`${BASE}/${orgId}/schedules/${scheduleId}/`, payload);
}

export function deleteSchedule(orgId: number, scheduleId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/schedules/${scheduleId}/`);
}

// Website (CJ_UC054/UC055) — a corporate's branded portal.
export interface CorporateWebsite {
  id: number;
  organization: number;
  slug: string;
  company_name: string;
  logo_url: string;
  /** Report 9 #49: where the logo shows from — the uploaded file (an
   * `/api/...` path) or the typed URL. Resolve with `resolveLogoSrc`. */
  logo_src: string;
  layout: "classic" | "modern" | "minimal";
  primary_color: string;
  admin_user: number | null;
  admin_email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  generated_credentials?: { email: string; temporary_password: string };
}

/** Public branding of a corporate portal (`/site/<slug>`, Report 9 #48/#95). */
export interface PublicSite {
  organization_id: number;
  slug: string;
  company_name: string;
  /** Uploaded logo (`/api/...` path) or a typed URL; "" when none. */
  logo_url: string;
  layout: "classic" | "modern" | "minimal";
  primary_color: string;
}

/** Turn a logo path served by the API (`/api/organizations/site/<slug>/logo/`)
 * into a URL the browser can load, wherever the API is hosted. Absolute URLs
 * (typed logo links) pass through unchanged. */
export function resolveLogoSrc(src: string | null | undefined): string {
  if (!src) return "";
  if (!src.startsWith("/api/")) return src;
  return API_BASE_URL.replace(/\/api\/?$/, "") + src;
}

export function getWebsite(orgId: number): Promise<CorporateWebsite | null> {
  return apiGet<CorporateWebsite | null>(`${BASE}/${orgId}/website/`);
}

type WebsiteFields = {
  company_name: string;
  layout: string;
  primary_color: string;
  logo_url: string;
  is_active: boolean;
};

/** Build a multipart body when a logo file is included, else plain JSON. */
function websiteBody(payload: Partial<WebsiteFields> & { admin_email?: string; logo?: File }) {
  if (!payload.logo) return payload;
  const form = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    form.append(key, value instanceof File ? value : String(value));
  });
  return form;
}

export function createWebsite(
  orgId: number,
  payload: {
    company_name: string;
    layout?: string;
    primary_color?: string;
    logo_url?: string;
    admin_email?: string;
    logo?: File;
  },
): Promise<CorporateWebsite> {
  return apiPost<CorporateWebsite>(`${BASE}/${orgId}/website/`, websiteBody(payload));
}

export function updateWebsite(
  orgId: number,
  payload: Partial<WebsiteFields> & { logo?: File },
): Promise<CorporateWebsite> {
  return apiPatch<CorporateWebsite>(`${BASE}/${orgId}/website/`, websiteBody(payload));
}

/** Public, no login: the branding of an active portal by its slug. */
export function getPublicSite(slug: string): Promise<PublicSite> {
  return apiGet<PublicSite>(`${BASE}/site/${encodeURIComponent(slug)}/`);
}

/** The signed-in member's own organization portal branding, or null. */
export function getMySite(): Promise<PublicSite | null> {
  return apiGet<PublicSite | null>(`${BASE}/my-site/`);
}
