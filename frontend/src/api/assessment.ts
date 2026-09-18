/**
 * Assessment API functions.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/assessments";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AssessmentType = "normal" | "psychometric";

export interface Assessment {
  id: number;
  title: string;
  objective: string;
  description: string;
  instructions: string;
  status: string;
  assessment_type: AssessmentType;
  assessment_type_label: string;
  total_duration_seconds: number | null;
  timer_level: string;
  display_order: string;
  navigation_rule: string;
  attempt_rule: string;
  /** PLT-3 pay-for-test: price to attempt (as a decimal string). "0.00" = free. */
  price: string;
  created_by: number | null;
  created_by_name: string | null;
  section_count: number;
  question_count: number;
  session_count: number;
  created_at: string;
  updated_at: string;
}

export interface AssessmentDetail extends Assessment {
  sections: AssessmentSection[];
}

export interface AssessmentSection {
  id: number;
  assessment: number;
  parent: number | null;
  title: string;
  description: string;
  level: number;
  order: number;
  order_mode: "STATIC" | "RANDOM";
  duration_seconds: number | null;
  delivery_count: number | null;
  subsections: AssessmentSection[];
}

export interface AssessmentSession {
  id: number;
  assessment: number;
  assessment_title: string;
  candidate: number;
  candidate_name: string | null;
  status: string;
  started_at: string;
  suspended_at: string | null;
  resumed_at: string | null;
  completed_at: string | null;
  total_score: number | null;
  max_score: number | null;
  percentage: number | null;
  /** Assessment-level total duration (seconds) — exposed via session API for the player timer. */
  total_duration_seconds: number | null;
  /**
   * Effective time budget (seconds): the assessment-level timer, or the sum
   * of the per-level (section/question) timers when the timer is set lower
   * down (SRS §5.2). Null when no timer is set.
   */
  aggregate_duration_seconds: number | null;
  /** Assessment-level navigation rule — exposed via session API for the player. */
  navigation_rule: string;
  /** Assessment-level display order — exposed via session API for the player. */
  display_order: string;
  /** Assessment-level timer level — exposed via session API for the player. */
  timer_level: string;
}

// ---------------------------------------------------------------------------
// Assessment CRUD
// ---------------------------------------------------------------------------

export function listAssessments(params?: {
  page?: number;
  search?: string;
  status?: string;
}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: Assessment[];
}> {
  return apiGetPaged<Assessment>(`${BASE}/`, {
    params: {
      page: params?.page ?? 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.status ? { status: params.status } : {}),
    },
  });
}

export function retrieveAssessment(id: number): Promise<AssessmentDetail> {
  return apiGet<AssessmentDetail>(`${BASE}/${id}/`);
}

export function createAssessment(payload: Record<string, unknown>): Promise<AssessmentDetail> {
  return apiPost<AssessmentDetail>(`${BASE}/`, payload);
}

export function updateAssessment(
  id: number,
  payload: Record<string, unknown>,
): Promise<AssessmentDetail> {
  return apiPatch<AssessmentDetail>(`${BASE}/${id}/`, payload);
}

export function deleteAssessment(id: number, reason?: string): Promise<void> {
  // A non-admin deleting a PUBLISHED assessment creates a modification
  // request (the backend requires a reason); admins/drafts delete directly.
  return apiDelete(`${BASE}/${id}/`, reason ? { data: { reason } } : undefined);
}

// ---------------------------------------------------------------------------
// Modification Requests (ASM-2 / SRS §2.2/§2.3) — a non-admin's edit/delete of
// a PUBLISHED assessment is routed to an admin for approval.
// ---------------------------------------------------------------------------

const MR_BASE = "/assessment-modification-requests";

export interface AssessmentModificationRequest {
  id: number;
  assessment: number;
  assessment_title: string;
  requester: number;
  requester_name: string | null;
  action: "edit" | "delete";
  proposed_title: string | null;
  reason: string;
  status: "pending" | "approved" | "rejected";
  review_comment: string;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export function listModificationRequests(): Promise<AssessmentModificationRequest[]> {
  return apiGetPaged<AssessmentModificationRequest>(`${MR_BASE}/`).then((r) => r.results);
}

/** Request an admin-approved title change on a published assessment. */
export function requestAssessmentTitleChange(
  id: number,
  title: string,
  reason: string,
): Promise<AssessmentModificationRequest> {
  return apiPatch<AssessmentModificationRequest>(`${BASE}/${id}/`, { title, reason });
}

export function approveModificationRequest(
  id: number,
  adminNote?: string,
): Promise<AssessmentModificationRequest> {
  return apiPost<AssessmentModificationRequest>(`${MR_BASE}/${id}/approve/`, {
    admin_note: adminNote ?? "",
  });
}

export function declineModificationRequest(
  id: number,
  adminNote?: string,
): Promise<AssessmentModificationRequest> {
  return apiPost<AssessmentModificationRequest>(`${MR_BASE}/${id}/decline/`, {
    admin_note: adminNote ?? "",
  });
}

export function publishAssessment(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`${BASE}/${id}/publish/`);
}

export interface AssessmentReadiness {
  ready: boolean;
  errors: string[];
  section_count: number;
  question_count: number;
  has_title: boolean;
  has_objective: boolean;
  has_instructions: boolean;
}

export function getAssessmentReadiness(id: number): Promise<AssessmentReadiness> {
  return apiGet<AssessmentReadiness>(`${BASE}/${id}/readiness/`);
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

export function listSections(assessmentId: number): Promise<AssessmentSection[]> {
  return apiGetPaged<AssessmentSection>(`${BASE}/${assessmentId}/sections/`).then((r) => r.results);
}

export function createSection(
  assessmentId: number,
  payload: {
    title: string;
    parent?: number | null;
    description?: string;
    level?: number;
    order_mode?: "STATIC" | "RANDOM";
    duration_seconds?: number | null;
    delivery_count?: number | null;
  },
): Promise<AssessmentSection> {
  return apiPost<AssessmentSection>(`${BASE}/${assessmentId}/sections/`, payload);
}

export function updateSection(
  assessmentId: number,
  sectionId: number,
  payload: Partial<{
    title: string;
    description: string;
    level: number;
    order: number;
    parent: number | null;
    order_mode: "STATIC" | "RANDOM";
    duration_seconds: number | null;
    delivery_count: number | null;
  }>,
): Promise<AssessmentSection> {
  return apiPatch<AssessmentSection>(`${BASE}/${assessmentId}/sections/${sectionId}/`, payload);
}

export function deleteSection(assessmentId: number, sectionId: number): Promise<void> {
  return apiDelete(`${BASE}/${assessmentId}/sections/${sectionId}/`);
}

// ---------------------------------------------------------------------------
// Question Assignment
// ---------------------------------------------------------------------------

export interface AssessmentQuestion {
  id: number;
  section: number;
  question: number;
  order: number;
  sub_question_index: number;
  score_override: number | null;
  duration_seconds: number | null;
  question_detail?: {
    id: number;
    question_title: string;
    question_type: string;
    question_type_label: string;
    status: string;
    difficulty_level: string;
  };
}

export function listSectionQuestions(
  assessmentId: number,
  sectionId: number,
): Promise<AssessmentQuestion[]> {
  return apiGetPaged<AssessmentQuestion>(
    `${BASE}/${assessmentId}/sections/${sectionId}/questions/`,
  ).then((r) => r.results);
}

export function assignQuestion(
  assessmentId: number,
  sectionId: number,
  payload: { question: number; order?: number; sub_question_index?: number },
): Promise<AssessmentQuestion> {
  return apiPost<AssessmentQuestion>(
    `${BASE}/${assessmentId}/sections/${sectionId}/questions/`,
    payload,
  );
}

export function removeQuestion(
  assessmentId: number,
  sectionId: number,
  questionId: number,
): Promise<void> {
  return apiDelete(`${BASE}/${assessmentId}/sections/${sectionId}/questions/${questionId}/`);
}

/**
 * ASM-7: set a per-assessment score override (and/or per-question timer) on an
 * assigned question. `assessmentQuestionId` is the AssessmentQuestion row id.
 */
export function updateAssignedQuestion(
  assessmentId: number,
  sectionId: number,
  assessmentQuestionId: number,
  payload: Partial<{ score_override: number | null; duration_seconds: number | null }>,
): Promise<AssessmentQuestion> {
  return apiPatch<AssessmentQuestion>(
    `${BASE}/${assessmentId}/sections/${sectionId}/questions/${assessmentQuestionId}/`,
    payload,
  );
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export function listSessions(assessmentId: number): Promise<AssessmentSession[]> {
  return apiGet<AssessmentSession[]>(`${BASE}/${assessmentId}/sessions/`);
}

export function startSession(assessmentId: number): Promise<AssessmentSession> {
  return apiPost<AssessmentSession>(`${BASE}/${assessmentId}/start_session/`);
}

export function submitSession(sessionId: number): Promise<AssessmentSession> {
  return apiPost<AssessmentSession>(`${BASE}/sessions/${sessionId}/submit/`);
}

export function suspendSession(sessionId: number): Promise<AssessmentSession> {
  return apiPost<AssessmentSession>(`${BASE}/sessions/${sessionId}/suspend/`);
}

export function listMySessions(): Promise<AssessmentSession[]> {
  return apiGetPaged<AssessmentSession>(`${BASE}/sessions/`).then((r) => r.results);
}

export function retrieveSession(sessionId: number): Promise<AssessmentSession> {
  return apiGet<AssessmentSession>(`${BASE}/sessions/${sessionId}/`);
}

export interface SessionQuestion {
  id: number;
  session: number;
  question: number;
  section: number | null;
  sub_question_index: number;
  status: string;
  raw_answer: Record<string, unknown> | null;
  score: number | null;
  max_score: number | null;
  answered_at: string | null;
  time_spent_seconds: number | null;
  /**
   * Per-level timer metadata (SRS §5.2). ``section_duration_seconds`` is the
   * duration of the section that governs this question's section-level timer
   * (the ancestor at the configured timer level); ``timer_section_id`` is
   * that section's id — both null unless a section-level timer is configured.
   * ``question_duration_seconds`` is this question's own per-question timer.
   */
  section_duration_seconds: number | null;
  timer_section_id: number | null;
  question_duration_seconds: number | null;
  /** ASM-5 (§5.1): this question's section delivery order mode. */
  section_order_mode: "STATIC" | "RANDOM";
  question_detail: {
    id: number;
    question_title: string;
    question_type: string;
    question_type_label: string;
    question_text_1: string;
    question_text_2: string;
    image: string | null;
    scoring_type: string;
    scoring_type_label: string;
    difficulty_level: string;
    cognitive_level: string;
    status: string;
    options: {
      id: number;
      option_type: string;
      label: string;
      text_value: string;
      image_file: string | null;
      is_correct: boolean;
      match_pair_id: number | null;
      predefined_score: number;
      section_tag: string;
      selection_score: number;
      non_selection_score: number;
      order: number;
      sub_question_index: number;
    }[];
    flash_items: {
      id: number;
      item_type: string;
      text_value: string;
      image_file: string | null;
      order: number;
      is_in_display_pool: boolean;
    }[];
    hotspot_areas: {
      id: number;
      x: number;
      y: number;
      width_px: number;
      height_px: number;
      shape_type: string;
      is_correct: boolean;
      radius: number | null;
      points: { x: number; y: number }[] | null;
    }[];
    media_files: {
      id: number;
      media_type: string;
      file: string;
      created_at: string;
    }[];
    flash_interval_ms: number | null;
    flash_display_count: number | null;
    flash_order: string;
    passage_title: string;
    passage_body: string;
    display_duration_seconds: number | null;
    display_mode: "timed" | "unlimited";
    replay_mode: "permitted" | "not_permitted";
    option_layout: "1" | "2" | "3";
    hotspot_visibility: "transparent" | "visible";
    sub_question_count: number;
    sub_question_texts: string[];
    sub_question_text_2_list: string[];
    grid_rows: number | null;
    grid_cols: number | null;
    rating_scale_points: number | null;
    rating_direction: string | null;
    image_width: number | null;
    image_height: number | null;
  };
}

export function getSessionQuestions(sessionId: number): Promise<SessionQuestion[]> {
  return apiGet<SessionQuestion[]>(`${BASE}/sessions/${sessionId}/questions/`);
}

export function submitAnswer(
  sessionId: number,
  payload: {
    question_id: number;
    sub_question_index?: number;
    raw_answer?: Record<string, unknown>;
    bookmark?: boolean;
  },
): Promise<SessionQuestion> {
  return apiPost<SessionQuestion>(`${BASE}/sessions/${sessionId}/answer/`, payload);
}

export function submitSessionResult(sessionId: number): Promise<{
  session: AssessmentSession;
  section_scores: {
    id: number;
    session: number;
    section: number;
    section_title: string;
    raw_score: number;
    max_score: number;
    percentage: number;
  }[];
}> {
  return apiPost(`${BASE}/sessions/${sessionId}/submit/`);
}

export interface SectionScore {
  id: number;
  session: number;
  section: number;
  section_title: string;
  raw_score: number;
  max_score: number;
  percentage: number;
}

export function getSessionSectionScores(sessionId: number): Promise<SectionScore[]> {
  return apiGet<SectionScore[]>(`${BASE}/sessions/${sessionId}/section_scores/`);
}

// ---------------------------------------------------------------------------
// Debug endpoint (cj_admin only)
// ---------------------------------------------------------------------------

export interface SessionDebugData {
  session: {
    id: number;
    assessment_id: number;
    assessment_title: string;
    assessment_type: string;
    candidate_id: number;
    candidate_email: string;
    status: string;
    started_at: string;
    completed_at: string | null;
    total_score: number | null;
    max_score: number | null;
    percentage: number | null;
    total_duration_seconds: number | null;
    question_count: number;
    attempted_count: number;
    unattempted_count: number;
    bookmarked_count: number;
  };
  sections: {
    id: number;
    title: string;
    level: number;
    order: number;
    parent_id: number | null;
    parent_title: string | null;
    duration_seconds: number | null;
  }[];
  section_scores: {
    section_id: number;
    title: string;
    level: number;
    parent_id: number | null;
    raw_score: number;
    max_score: number;
    percentage: number;
    has_direct_questions: boolean;
  }[];
  attempts: {
    attempt_id: number;
    question_id: number;
    question_title: string;
    question_type: string;
    question_type_label: string;
    scoring_type: string;
    scoring_type_label: string;
    section_id: number | null;
    section_title: string | null;
    section_level: number | null;
    sub_question_index: number;
    status: string;
    raw_answer: Record<string, unknown> | null;
    correct_answer: Record<string, unknown> | null;
    score: number | null;
    max_score: number | null;
    calculated_score: number;
    calculated_max: number;
    default_max: number;
    score_matches: boolean | null;
    answered_at: string | null;
    time_spent_seconds: number | null;
  }[];
}

export function getSessionDebug(sessionId: number): Promise<SessionDebugData> {
  return apiGet<SessionDebugData>(`${BASE}/sessions/${sessionId}/debug/`);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const ASSESSMENT_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

export const ASSESSMENT_TYPES = [
  {
    value: "normal",
    label: "Normal Assessment",
    description: "Aptitude / ability questions (MCQ, FITB, Match, Grid, Hotspot)",
  },
  {
    value: "psychometric",
    label: "Psychometric Assessment",
    description: "Rating, Rank, Rank-then-Rate, Forced-Choice questions",
  },
] as const;

export const NAVIGATION_RULES = [
  { value: "FREE", label: "Free Navigation" },
  { value: "PREV_SECTION", label: "Only Previous Section" },
  { value: "NO_BACKWARD_SECTION", label: "No Backward (Section Level)" },
  { value: "NO_BACKWARD_QUESTION", label: "No Backward (Question Level)" },
];

export const ATTEMPT_RULES = [
  { value: "MULTIPLE_RETAKE", label: "Multiple Retakes Allowed" },
  { value: "SINGLE_RETAKE", label: "Single Retake Only" },
  { value: "MULTIPLE_SESSION", label: "Multiple Sessions Allowed" },
  { value: "SINGLE_SESSION", label: "Single Session Only" },
];

export const TIMER_LEVELS = [
  { value: "assessment", label: "Assessment Level" },
  { value: "level1", label: "Level 1 (Section)" },
  { value: "level2", label: "Level 2 (Sub-section)" },
  { value: "level3", label: "Level 3" },
  { value: "level4", label: "Level 4" },
  { value: "question", label: "Question Level" },
];
