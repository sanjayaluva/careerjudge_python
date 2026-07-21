/**
 * Counseling API client.
 */
import { apiGet, apiGetPaged, apiPost } from "./client";

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
  fee: string;
  booked_at: string;
  confirmed_at: string | null;
  completed_at: string | null;
}

export interface SessionCancellation {
  id: number;
  session: number;
  cancelled_by: string;
  reason: string;
  refund_tier: "full" | "half" | "none";
  refund_amount: string;
  cancelled_at: string;
}

export interface SessionSummary {
  id: number;
  session: number;
  counsellor: number | null;
  summary: string;
  recommendations: string;
  followup_recommended: boolean;
  created_at: string;
}

export interface SessionFeedback {
  id: number;
  session: number;
  counselee: number;
  rating: number;
  experience_text: string;
  counsellor_effectiveness: string;
  created_at: string;
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
}): Promise<CounselingSession> {
  return apiPost<CounselingSession>(`${BASE}/sessions/`, {
    ...payload,
    terms_accepted: true,
  });
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
  payload: { summary: string; recommendations?: string; followup_recommended?: boolean },
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
  payload: { rating: number; experience_text: string; counsellor_effectiveness?: string },
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
