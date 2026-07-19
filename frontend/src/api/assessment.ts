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
  /** Assessment-level total duration (seconds) — exposed via session API for the player timer. */
  total_duration_seconds: number | null;
  /** Assessment-level navigation rule — exposed via session API for the player. */
  navigation_rule: string;
  /** Assessment-level display order — exposed via session API for the player. */
  display_order: string;
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

export function deleteAssessment(id: number): Promise<void> {
  return apiDelete(`${BASE}/${id}/`);
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
  payload: { title: string; parent?: number | null; description?: string; level?: number },
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
    duration_seconds: number | null;
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
    media_files: {
      id: number;
      media_type: string;
      file_url: string;
      order: number;
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
