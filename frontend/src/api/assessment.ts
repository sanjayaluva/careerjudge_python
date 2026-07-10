/**
 * Assessment API functions.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/assessments";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Assessment {
  id: number;
  title: string;
  objective: string;
  description: string;
  instructions: string;
  status: string;
  total_duration_seconds: number | null;
  timer_level: string;
  display_order: string;
  navigation_rule: string;
  attempt_rule: string;
  created_by: number | null;
  created_by_name: string | null;
  section_count: number;
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
  duration_seconds: number | null;
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
  return apiGetPaged<Assessment>(`${BASE}/assessments/`, {
    params: {
      page: params?.page ?? 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.status ? { status: params.status } : {}),
    },
  });
}

export function retrieveAssessment(id: number): Promise<AssessmentDetail> {
  return apiGet<AssessmentDetail>(`${BASE}/assessments/${id}/`);
}

export function createAssessment(payload: Record<string, unknown>): Promise<AssessmentDetail> {
  return apiPost<AssessmentDetail>(`${BASE}/assessments/`, payload);
}

export function updateAssessment(
  id: number,
  payload: Record<string, unknown>,
): Promise<AssessmentDetail> {
  return apiPatch<AssessmentDetail>(`${BASE}/assessments/${id}/`, payload);
}

export function deleteAssessment(id: number): Promise<void> {
  return apiDelete(`${BASE}/assessments/${id}/`);
}

export function publishAssessment(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`${BASE}/assessments/${id}/publish/`);
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

export function listSections(assessmentId: number): Promise<AssessmentSection[]> {
  return apiGetPaged<AssessmentSection>(`${BASE}/assessments/${assessmentId}/sections/`).then(
    (r) => r.results,
  );
}

export function createSection(
  assessmentId: number,
  payload: { title: string; parent?: number | null; description?: string; level?: number },
): Promise<AssessmentSection> {
  return apiPost<AssessmentSection>(`${BASE}/assessments/${assessmentId}/sections/`, payload);
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
    `${BASE}/assessments/${assessmentId}/sections/${sectionId}/questions/`,
  ).then((r) => r.results);
}

export function assignQuestion(
  assessmentId: number,
  sectionId: number,
  payload: { question: number; order?: number; sub_question_index?: number },
): Promise<AssessmentQuestion> {
  return apiPost<AssessmentQuestion>(
    `${BASE}/assessments/${assessmentId}/sections/${sectionId}/questions/`,
    payload,
  );
}

export function removeQuestion(
  assessmentId: number,
  sectionId: number,
  questionId: number,
): Promise<void> {
  return apiDelete(
    `${BASE}/assessments/${assessmentId}/sections/${sectionId}/questions/${questionId}/`,
  );
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export function listSessions(assessmentId: number): Promise<AssessmentSession[]> {
  return apiGet<AssessmentSession[]>(`${BASE}/assessments/${assessmentId}/sessions/`);
}

export function startSession(assessmentId: number): Promise<AssessmentSession> {
  return apiPost<AssessmentSession>(`${BASE}/assessments/${assessmentId}/start_session/`);
}

export function submitSession(sessionId: number): Promise<AssessmentSession> {
  return apiPost<AssessmentSession>(`${BASE}/assessments/sessions/${sessionId}/submit/`);
}

export function suspendSession(sessionId: number): Promise<AssessmentSession> {
  return apiPost<AssessmentSession>(`${BASE}/assessments/sessions/${sessionId}/suspend/`);
}

export function listMySessions(): Promise<AssessmentSession[]> {
  return apiGetPaged<AssessmentSession>(`${BASE}/assessments/sessions/`).then((r) => r.results);
}

export function retrieveSession(sessionId: number): Promise<AssessmentSession> {
  return apiGet<AssessmentSession>(`${BASE}/assessments/sessions/${sessionId}/`);
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
      order: number;
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
    flash_interval_ms: number | null;
    flash_display_count: number | null;
    flash_order: string;
    passage_title: string;
    passage_body: string;
    display_duration_seconds: number | null;
    grid_rows: number | null;
    grid_cols: number | null;
    rating_scale_points: number | null;
    rating_direction: string | null;
  };
}

export function getSessionQuestions(sessionId: number): Promise<SessionQuestion[]> {
  return apiGet<SessionQuestion[]>(`${BASE}/assessments/sessions/${sessionId}/questions/`);
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
  return apiPost<SessionQuestion>(`${BASE}/assessments/sessions/${sessionId}/answer/`, payload);
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
  return apiPost(`${BASE}/assessments/sessions/${sessionId}/submit/`);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const ASSESSMENT_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

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
