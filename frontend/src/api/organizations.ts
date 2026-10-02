/**
 * Organizations API functions.
 * Endpoints live under /api/organizations/.
 */
import { API_BASE_URL } from "@/lib/constants";

import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";
import type { CounselingSession, CounsellorProfile, TimeSlot } from "./counseling";
import type { LearnerProgress } from "./training";

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
  /** Report 9 #96: modules this organization may use; null = all. */
  enabled_modules: string[] | null;
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
  /** Report 9 #23: parent group (null = top-level group). */
  parent: number | null;
  parent_name: string | null;
  region_division: string;
  description: string;
  member_count: number;
  /** Whether the viewer may edit/delete this group (a Group Admin: only the
   * sub-groups inside his own group). */
  can_manage: boolean;
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
  group_name: string | null;
  employee_id: string;
  is_admin: boolean;
  /** Report 9 #21/#37: the member holds the Group Admin role. */
  is_group_admin: boolean;
  /** Report 9 #4/#13/#38: Group Admin may view & download members' reports. */
  can_view_member_reports: boolean;
  joined_at: string;
}

export interface OrganizationAssignment {
  id: number;
  organization: number;
  item_type: "assessment" | "training_course" | "counseling";
  item_id: number;
  /** Report 9: the licensed item's title ("Counselling services" for counselling). */
  item_title: string;
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

/** Report 9 #96: CJ Admin sets the modules an organization may use (null = all). */
export function setOrganizationModules(
  id: number,
  enabledModules: string[] | null,
): Promise<Organization> {
  return apiPatch<Organization>(`${BASE}/${id}/`, { enabled_modules: enabledModules });
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

export interface GroupPayload {
  name: string;
  region_division?: string;
  description?: string;
  parent?: number | null;
}

export function createGroup(orgId: number, payload: GroupPayload): Promise<Group> {
  return apiPost<Group>(`${BASE}/${orgId}/groups/`, payload);
}

/** Report 9 #23: edit a group (name, region/division, parent). */
export function updateGroup(
  orgId: number,
  groupId: number,
  payload: Partial<GroupPayload>,
): Promise<Group> {
  return apiPatch<Group>(`${BASE}/${orgId}/groups/${groupId}/`, payload);
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
  payload: UpdateMemberPayload,
): Promise<OrganizationMember> {
  return apiPatch<OrganizationMember>(`${BASE}/${orgId}/members/${memberId}/`, payload);
}

export interface UpdateMemberPayload {
  group_id?: number | null;
  is_admin?: boolean;
  /** Report 9 #37: tag (or untag) the member as Group Admin of his group. */
  is_group_admin?: boolean;
  /** Report 9 #4: Group Admin's "Can view & download members' reports". */
  can_view_member_reports?: boolean;
}

export interface CreateGroupAdminPayload {
  full_name: string;
  email: string;
  employee_id?: string;
  group_id: number;
  can_view_member_reports: boolean;
}

/** Report 9 #21: the Corp Admin defines a Group Admin (user + invite email). */
export function createGroupAdmin(
  orgId: number,
  payload: CreateGroupAdminPayload,
): Promise<OrganizationMember & { invite_email_sent: boolean | null }> {
  return apiPost<OrganizationMember & { invite_email_sent: boolean | null }>(
    `${BASE}/${orgId}/group-admins/`,
    payload,
  );
}

/** Report 9 #27: the viewer's own Group Admin set-up. */
export interface MyOrgAccess {
  is_group_admin: boolean;
  organization_ids: number[];
  group_ids: number[];
  can_view_member_reports: boolean;
}

export function getMyOrgAccess(): Promise<MyOrgAccess> {
  return apiGet<MyOrgAccess>(`${BASE}/my-access/`);
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
  // Counselling is licensed as a whole service: no item_id.
  payload: { item_type: "assessment" | "training_course" | "counseling"; item_id?: number },
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

// ---------------------------------------------------------------------------
// Report 9: licensed courses and counselling used by a manager on behalf of
// his members (Corp Admin, Corp Exclusive, Group Admin, Channel Partner).
// ---------------------------------------------------------------------------

export interface LicensedCourseMember {
  registration_id: number;
  user_id: number;
  full_name: string;
  email: string;
  completion_status: string;
  /** True when the registration was made by the organization. */
  assigned_by_organization: boolean;
  /** Only organization-made registrations not yet started can be withdrawn. */
  can_unassign: boolean;
}

export interface LicensedCourse {
  id: number;
  title: string;
  course_type: string;
  schedule_type: string;
  duration_days: number | null;
  members: LicensedCourseMember[];
}

export function listLicensedCourses(orgId: number): Promise<LicensedCourse[]> {
  return apiGet<LicensedCourse[]>(`${BASE}/${orgId}/courses/`);
}

/** Report 9 #17: the members' progress in a licensed course. */
export function getLicensedCourseProgress(
  orgId: number,
  courseId: number,
): Promise<{ course: { id: number; title: string }; learners: LearnerProgress[] }> {
  return apiGet(`${BASE}/${orgId}/courses/${courseId}/progress/`);
}

export function assignCourse(orgId: number, courseId: number, userIds: number[]): Promise<unknown> {
  return apiPost(`${BASE}/${orgId}/courses/${courseId}/assign/`, { user_ids: userIds });
}

export function unassignCourse(orgId: number, courseId: number, userId: number): Promise<unknown> {
  return apiPost(`${BASE}/${orgId}/courses/${courseId}/unassign/`, { user_id: userId });
}

export interface CourseSchedule {
  id: number;
  organization: number;
  group: number | null;
  course: number;
  course_title: string;
  group_name: string | null;
  scheduled_at: string;
  created_by: number | null;
  notified: boolean;
  created_at: string;
}

export function listCourseSchedules(orgId: number): Promise<CourseSchedule[]> {
  return apiGetPaged<CourseSchedule>(`${BASE}/${orgId}/course-schedules/`).then((r) => r.results);
}

export function createCourseSchedule(
  orgId: number,
  payload: { course: number; scheduled_at: string; group?: number | null },
): Promise<CourseSchedule> {
  return apiPost<CourseSchedule>(`${BASE}/${orgId}/course-schedules/`, payload);
}

export function rescheduleCourseSchedule(
  orgId: number,
  scheduleId: number,
  payload: { scheduled_at: string },
): Promise<CourseSchedule> {
  return apiPatch<CourseSchedule>(`${BASE}/${orgId}/course-schedules/${scheduleId}/`, payload);
}

/** Cancel a course schedule — the members are notified. */
export function cancelCourseSchedule(orgId: number, scheduleId: number): Promise<void> {
  return apiDelete(`${BASE}/${orgId}/course-schedules/${scheduleId}/`);
}

export function listOrgCounsellors(orgId: number): Promise<CounsellorProfile[]> {
  return apiGet<CounsellorProfile[]>(`${BASE}/${orgId}/counsellors/`);
}

export function listOrgCounsellorSlots(orgId: number, counsellorId: number): Promise<TimeSlot[]> {
  return apiGet<TimeSlot[]>(`${BASE}/${orgId}/counsellors/${counsellorId}/timeslots/`);
}

export function listOrgCounselingSessions(orgId: number): Promise<CounselingSession[]> {
  return apiGet<CounselingSession[]>(`${BASE}/${orgId}/counseling-sessions/`);
}

export function bookCounselingForMember(
  orgId: number,
  payload: {
    counselee: number;
    counsellor: number;
    timeslot: number;
    topic: string;
    description?: string;
    mode?: "online" | "offline";
  },
): Promise<CounselingSession> {
  return apiPost<CounselingSession>(`${BASE}/${orgId}/counseling-sessions/`, payload);
}

export function rescheduleMemberCounseling(
  orgId: number,
  sessionId: number,
  timeslot: number,
): Promise<CounselingSession> {
  return apiPost<CounselingSession>(
    `${BASE}/${orgId}/counseling-sessions/${sessionId}/reschedule/`,
    { timeslot },
  );
}

export function cancelMemberCounseling(
  orgId: number,
  sessionId: number,
  reason: string,
): Promise<CounselingSession> {
  return apiPost<CounselingSession>(`${BASE}/${orgId}/counseling-sessions/${sessionId}/cancel/`, {
    reason,
  });
}
