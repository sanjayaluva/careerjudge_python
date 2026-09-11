/**
 * Counseling API client.
 */
import { apiClient, apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/counseling";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CounselingCategory {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
}

export interface CounsellorProfile {
  id: number;
  user: number;
  user_email: string;
  full_name: string;
  bio: string;
  qualifications: string;
  /** Report 3 §1.7: profile details shown to candidates when browsing. */
  gender: string;
  avatar: string | null;
  language: string;
  location: string;
  hourly_rate: string;
  meeting_url: string;
  categories: number[];
  category_names: string[];
  is_available: boolean;
  cancellation_count: number;
  upcoming_slot_count: number;
  created_at: string;
  updated_at: string;
}

export interface TimeSlot {
  id: number;
  counsellor: number;
  counsellor_name: string;
  start_time: string;
  end_time: string;
  status: "available" | "booked" | "blocked";
  created_at: string;
}

export interface CounselingSession {
  id: number;
  counselee: number;
  counselee_name: string | null;
  counselee_email: string;
  counsellor: number;
  counsellor_name: string;
  category: number | null;
  category_name: string | null;
  timeslot: number;
  timeslot_detail: TimeSlot | null;
  topic: string;
  description: string;
  terms_accepted: boolean;
  status: "pending" | "confirmed" | "completed" | "cancelled";
  payment_status: string;
  mode: "online" | "offline";
  /** H16/D8 §2.3: per-session meeting link, set by the counsellor. */
  meeting_link: string;
  fee: string;
  booked_at: string;
  confirmed_at: string | null;
  completed_at: string | null;
  /** D8: actual live-delivery start/end, distinct from the scheduled timeslot. */
  actual_start_at: string | null;
  actual_end_at: string | null;
}

export interface SessionCancellation {
  id: number;
  session: number;
  cancelled_by: string;
  reason: string;
  refund_tier: "full" | "half" | "none";
  refund_amount: string;
  /** D8: whether the refund was executed against the payments module. */
  refund_executed: boolean;
  cancelled_at: string;
}

export interface SessionSummary {
  id: number;
  session: number;
  counsellor: number | null;
  /** Report 3 §2.4 (6 fields) */
  client_details: string;
  summary: string;
  provisional_diagnosis: string;
  case_prognosis: string;
  session_smoothness: "" | "yes" | "somewhat" | "no";
  smoothly_reason: string;
  followup_recommended: boolean;
  /** legacy */
  recommendations: string;
  created_at: string;
}

export interface SessionFeedback {
  id: number;
  session: number;
  counselee: number;
  /** Report 3 §2.2 (8 fields) */
  session_usefulness: "" | "very_useful" | "useful" | "somewhat_useful" | "not_useful";
  usefulness_text: string;
  counsellor_empathy: "" | "very_much" | "somewhat" | "not_much";
  session_ending: "" | "on_time" | "before_time" | "late";
  would_rechoose: "" | "yes" | "maybe" | "no";
  rechoose_text: string;
  improvement_suggestions: string;
  /** 1-10 scale (10 = excellent) */
  rating: number;
  /** legacy */
  experience_text: string;
  counsellor_effectiveness: string;
  created_at: string;
}

/** Report 3 §1.9/§1.11/§1.2/§1.12 — admin-managed counseling settings. */
export interface CounselingSettings {
  terms_and_conditions: string;
  cancellation_policy: string;
  max_weeks_ahead: number;
  confirm_window_hours: number;
  full_refund_within_hours: number;
  half_refund_within_hours: number;
}

export function getCounselingSettings(): Promise<CounselingSettings> {
  return apiGet<CounselingSettings>(`${BASE}/settings/`);
}

export function updateCounselingSettings(
  payload: Partial<CounselingSettings>,
): Promise<CounselingSettings> {
  return apiPatch<CounselingSettings>(`${BASE}/settings/1/`, payload);
}

export interface FollowupSession {
  id: number;
  original_session: number;
  counsellor: number;
  counsellor_name: string;
  counselee_name: string | null;
  proposed_time: string;
  status: "proposed" | "confirmed" | "declined";
  confirmed_session: number | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Category API
// ---------------------------------------------------------------------------

export function listCategories(): Promise<CounselingCategory[]> {
  return apiGetPaged<CounselingCategory>(`${BASE}/categories/`).then((r) => r.results);
}

// ---------------------------------------------------------------------------
// Counsellor API
// ---------------------------------------------------------------------------

export function listCounsellors(params?: {
  search?: string;
  category?: string;
  available?: boolean;
}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: CounsellorProfile[];
}> {
  return apiGetPaged<CounsellorProfile>(`${BASE}/counsellors/`, {
    params: {
      page: 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.category ? { category: params.category } : {}),
      ...(params?.available !== undefined ? { available: String(params.available) } : {}),
    },
  });
}

export function retrieveCounsellor(id: number): Promise<CounsellorProfile> {
  return apiGet<CounsellorProfile>(`${BASE}/counsellors/${id}/`);
}

export function createCounsellorProfile(
  payload: Record<string, unknown>,
): Promise<CounsellorProfile> {
  return apiPost<CounsellorProfile>(`${BASE}/counsellors/`, payload);
}

export function listCounsellorTimeslots(counsellorId: number, weeks?: number): Promise<TimeSlot[]> {
  return apiGet<TimeSlot[]>(
    `${BASE}/counsellors/${counsellorId}/timeslots/${weeks ? `?weeks=${weeks}` : ""}`,
  );
}

/**
 * D8 "browse future weeks": a single calendar week of a counsellor's
 * timeslots, N weeks from now (0 = this week, 1 = next week, ...) — for
 * paging forward/backward through future weeks instead of only ever seeing
 * the cumulative "next N weeks" list.
 */
export async function listCounsellorTimeslotsForWeek(
  counsellorId: number,
  weekOffset: number,
): Promise<{ slots: TimeSlot[]; weekStart: string; weekEnd: string }> {
  const res = await apiClient.get<{
    message: string;
    data: TimeSlot[];
    week_start: string;
    week_end: string;
  }>(`${BASE}/counsellors/${counsellorId}/timeslots/?week_offset=${weekOffset}`);
  return { slots: res.data.data, weekStart: res.data.week_start, weekEnd: res.data.week_end };
}

// ---------------------------------------------------------------------------
// TimeSlot API
// ---------------------------------------------------------------------------

export function createTimeSlot(
  counsellorId: number,
  startTime: string,
  endTime: string,
): Promise<TimeSlot> {
  return apiPost<TimeSlot>(`${BASE}/timeslots/`, {
    counsellor: counsellorId,
    start_time: startTime,
    end_time: endTime,
  });
}

/** Report 3 §1.1: counsellor edits one of their own timeslots. */
export function updateTimeSlot(
  timeslotId: number,
  payload: { start_time?: string; end_time?: string; status?: string },
): Promise<TimeSlot> {
  return apiPatch<TimeSlot>(`${BASE}/timeslots/${timeslotId}/`, payload);
}

/** Report 3 §1.1: counsellor deletes one of their own (unbooked) timeslots. */
export function deleteTimeSlot(timeslotId: number): Promise<void> {
  return apiDelete(`${BASE}/timeslots/${timeslotId}/`);
}

// ---------------------------------------------------------------------------
// Session API
// ---------------------------------------------------------------------------

export function listSessions(): Promise<CounselingSession[]> {
  return apiGetPaged<CounselingSession>(`${BASE}/sessions/`).then((r) => r.results);
}

export function retrieveSession(id: number): Promise<CounselingSession> {
  return apiGet<CounselingSession>(`${BASE}/sessions/${id}/`);
}

export function bookSession(payload: {
  counsellor: number;
  timeslot: number;
  topic: string;
  description?: string;
  mode?: string;
  category?: number;
  /** Report 3 §1.8: the user must explicitly accept the terms. */
  terms_accepted?: boolean;
}): Promise<CounselingSession & { checkout_url: string | null }> {
  return apiPost<CounselingSession & { checkout_url: string | null }>(
    `${BASE}/sessions/`,
    payload,
  );
}

/** H16/D8 §2.3: counsellor sets/updates the per-session meeting link. */
export function setSessionMeetingLink(
  sessionId: number,
  meetingLink: string,
): Promise<CounselingSession> {
  return apiPost<CounselingSession>(`${BASE}/sessions/${sessionId}/meeting-link/`, {
    meeting_link: meetingLink,
  });
}

/**
 * D8: join a session within its join window. The backend enforces the
 * window server-side (not just the frontend countdown), records
 * `actual_start_at` on first join, and returns the meeting_link to redirect
 * to — this is the authoritative source for the third-party redirect.
 */
export function joinSession(
  sessionId: number,
): Promise<{ meeting_link: string; actual_start_at: string }> {
  return apiPost(`${BASE}/sessions/${sessionId}/join/`);
}

export function confirmSession(sessionId: number): Promise<CounselingSession> {
  return apiPost<CounselingSession>(`${BASE}/sessions/${sessionId}/confirm/`);
}

export function cancelSession(
  sessionId: number,
  cancelledBy: string,
  reason?: string,
): Promise<{ session: CounselingSession; cancellation: SessionCancellation }> {
  return apiPost(`${BASE}/sessions/${sessionId}/cancel/`, {
    cancelled_by: cancelledBy,
    reason: reason || "",
  });
}

export function completeSession(sessionId: number): Promise<CounselingSession> {
  return apiPost<CounselingSession>(`${BASE}/sessions/${sessionId}/complete/`);
}

export function listMySessions(): Promise<CounselingSession[]> {
  return apiGet<CounselingSession[]>(`${BASE}/sessions/my_sessions/`);
}

// ---------------------------------------------------------------------------
// Summary API (SRS §3.3)
// ---------------------------------------------------------------------------

export function getSessionSummary(sessionId: number): Promise<SessionSummary | null> {
  return apiGet<SessionSummary | null>(`${BASE}/sessions/${sessionId}/summary/`);
}

export function saveSessionSummary(
  sessionId: number,
  payload: Partial<Omit<SessionSummary, "id" | "session" | "counsellor" | "created_at">> & {
    summary: string;
  },
): Promise<SessionSummary> {
  return apiPost<SessionSummary>(`${BASE}/sessions/${sessionId}/summary/`, payload);
}

// ---------------------------------------------------------------------------
// Feedback API (SRS §2.3)
// ---------------------------------------------------------------------------

export function getSessionFeedback(sessionId: number): Promise<SessionFeedback | null> {
  return apiGet<SessionFeedback | null>(`${BASE}/sessions/${sessionId}/feedback/`);
}

export function submitSessionFeedback(
  sessionId: number,
  payload: Partial<Omit<SessionFeedback, "id" | "session" | "counselee" | "created_at">> & {
    rating: number;
  },
): Promise<SessionFeedback> {
  return apiPost<SessionFeedback>(`${BASE}/sessions/${sessionId}/feedback/`, payload);
}

// ---------------------------------------------------------------------------
// Followup API (SRS §3.3)
// ---------------------------------------------------------------------------

export function listFollowups(sessionId: number): Promise<FollowupSession[]> {
  return apiGet<FollowupSession[]>(`${BASE}/sessions/${sessionId}/followups/`);
}

export function proposeFollowup(sessionId: number, proposedTime: string): Promise<FollowupSession> {
  return apiPost<FollowupSession>(`${BASE}/sessions/${sessionId}/followups/`, {
    proposed_time: proposedTime,
  });
}

export function confirmFollowup(followupId: number): Promise<{
  followup: FollowupSession;
  session: CounselingSession;
  checkout_url: string | null;
}> {
  return apiPost(`${BASE}/followups/${followupId}/confirm/`);
}

export function declineFollowup(followupId: number): Promise<FollowupSession> {
  return apiPost<FollowupSession>(`${BASE}/followups/${followupId}/decline/`);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const COUNSELING_CATEGORIES = [
  { value: "career", label: "Career counselling" },
  { value: "learning", label: "Learning difficulties" },
  { value: "emotional", label: "Emotional problems" },
  { value: "relationship", label: "Relationship problems" },
  { value: "marital", label: "Marital problems" },
  { value: "clinical", label: "Clinical problems" },
  { value: "health", label: "Health counselling" },
];

export const SESSION_STATUSES = [
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];
