/**
 * Training API client.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/training";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TrainingCategory {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  course_count: number;
  created_at: string;
}

export interface SessionContent {
  id: number;
  session: number;
  title: string;
  content_format: "video" | "audio" | "text";
  content_url: string;
  text_content: string;
  duration_seconds: number | null;
  order: number;
  sequence_order: number | null;
  interactive_questions: InteractiveQuestion[];
}

export interface Assignment {
  id: number;
  session: number;
  title: string;
  description: string;
  resource_url: string;
  report_submission_enabled: boolean;
  report_instructions: string;
  order: number;
}

export interface TopicSession {
  id: number;
  topic: number;
  title: string;
  description: string;
  order: number;
  contents: SessionContent[];
  assignments: Assignment[];
}

export interface LessonTopic {
  id: number;
  lesson: number;
  title: string;
  description: string;
  order: number;
  sessions: TopicSession[];
}

export interface CourseLesson {
  id: number;
  course: number;
  title: string;
  description: string;
  order: number;
  week_number: number;
  topics: LessonTopic[];
}

export interface CourseAssessment {
  id: number;
  course: number;
  assessment: number;
  assessment_detail?: {
    id: number;
    title: string;
    status: string;
  };
  level: string;
  session: number | null;
  title: string;
  is_scored: boolean;
  order: number;
}

export interface LiveSession {
  id: number;
  course: number;
  title: string;
  description: string;
  mode: "online" | "offline";
  meeting_url: string;
  venue: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  created_at: string;
}

export interface TrainingCourse {
  id: number;
  title: string;
  objective: string;
  description: string;
  image: string;
  category: number | null;
  category_name: string | null;
  course_type: "online_standard" | "online_live" | "offline_live";
  schedule_type: "scheduled" | "non_scheduled";
  duration_days: number | null;
  price: string;
  status: "draft" | "published" | "archived";
  created_by: number | null;
  created_by_name: string | null;
  registration_count: number;
  lessons: CourseLesson[];
  live_sessions: LiveSession[];
  assessments: CourseAssessment[];
  created_at: string;
  updated_at: string;
}

export interface TrainingCourseListItem {
  id: number;
  title: string;
  objective: string;
  image: string;
  category: number | null;
  category_name: string | null;
  course_type: string;
  schedule_type: string;
  duration_days: number | null;
  price: string;
  status: string;
  created_by: number | null;
  created_by_name: string | null;
  registration_count: number;
  created_at: string;
  updated_at: string;
}

export interface CourseRegistration {
  id: number;
  course: number;
  course_title: string;
  student: number;
  student_name: string | null;
  student_email: string;
  payment_status: string;
  completion_status: string;
  started_at: string | null;
  completed_at: string | null;
  registered_at: string;
}

export interface CourseProgress {
  id: number;
  registration: number;
  content_type: string;
  content_id: number;
  is_completed: boolean;
  time_spent_seconds: number;
  last_accessed_at: string | null;
}

export interface ProgressSummary {
  completion_percentage: number;
  completed_count: number;
  total_count: number;
  total_time_spent_seconds: number;
  total_time_allowed_seconds: number | null;
  time_left_seconds: number | null;
  is_expired: boolean;
  last_accessed_at: string | null;
  last_content: { content_type: string; content_id: number } | null;
  completion_status: string;
  started_at: string | null;
}

export interface CourseMessage {
  id: number;
  registration: number;
  course_title: string;
  sender: number;
  sender_name: string | null;
  sender_email: string;
  body: string;
  is_read: boolean;
  sent_at: string;
}

export interface AssignmentReport {
  id: number;
  assignment: number;
  assignment_title: string;
  student: number;
  student_name: string | null;
  student_email: string;
  report_text: string;
  report_file_url: string;
  status: string;
  trainer_score: number | null;
  trainer_feedback: string;
  reviewed_at: string | null;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  submitted_at: string;
  updated_at: string;
}

export interface LiveSessionConsent {
  id: number;
  live_session: number;
  live_session_title: string;
  student: number;
  student_name: string | null;
  student_email: string;
  status: "consented" | "declined";
  consented_at: string;
}

export interface InteractiveQuestionOption {
  id: number;
  text: string;
  is_correct: boolean;
}

export interface InteractiveQuestion {
  id: number;
  session_content: number;
  question_text: string;
  trigger_timestamp: number;
  options: InteractiveQuestionOption[];
  correct_jump_to: number;
  incorrect_jump_to: number;
  order: number;
}

// ---------------------------------------------------------------------------
// Category API
// ---------------------------------------------------------------------------

export function listCategories(): Promise<TrainingCategory[]> {
  return apiGetPaged<TrainingCategory>(`${BASE}/categories/`).then((r) => r.results);
}

export function createCategory(payload: {
  name: string;
  description?: string;
}): Promise<TrainingCategory> {
  return apiPost<TrainingCategory>(`${BASE}/categories/`, payload);
}

// ---------------------------------------------------------------------------
// Course API
// ---------------------------------------------------------------------------

export function listCourses(params?: {
  page?: number;
  search?: string;
  status?: string;
  category?: number;
  course_type?: string;
}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: TrainingCourseListItem[];
}> {
  return apiGetPaged<TrainingCourseListItem>(`${BASE}/courses/`, {
    params: {
      page: params?.page ?? 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.category ? { category: params.category } : {}),
      ...(params?.course_type ? { course_type: params.course_type } : {}),
    },
  });
}

export function retrieveCourse(id: number): Promise<TrainingCourse> {
  return apiGet<TrainingCourse>(`${BASE}/courses/${id}/`);
}

export function createCourse(payload: Record<string, unknown>): Promise<TrainingCourse> {
  return apiPost<TrainingCourse>(`${BASE}/courses/`, payload);
}

export function updateCourse(
  id: number,
  payload: Record<string, unknown>,
): Promise<TrainingCourse> {
  return apiPatch<TrainingCourse>(`${BASE}/courses/${id}/`, payload);
}

export function deleteCourse(id: number): Promise<void> {
  return apiDelete(`${BASE}/courses/${id}/`);
}

export function publishCourse(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`${BASE}/courses/${id}/publish/`);
}

export function registerForCourse(courseId: number): Promise<CourseRegistration> {
  return apiPost<CourseRegistration>(`${BASE}/courses/${courseId}/register/`);
}

export function listCourseRegistrations(courseId: number): Promise<CourseRegistration[]> {
  return apiGet<CourseRegistration[]>(`${BASE}/courses/${courseId}/registrations/`);
}

export function listMyCourses(): Promise<CourseRegistration[]> {
  return apiGet<CourseRegistration[]>(`${BASE}/courses/my_courses/`);
}

// ---------------------------------------------------------------------------
// Course structure API (lessons, live sessions, assessments)
// ---------------------------------------------------------------------------

export function listLessons(courseId: number): Promise<CourseLesson[]> {
  return apiGet<CourseLesson[]>(`${BASE}/courses/${courseId}/lessons/`);
}

export function addLesson(
  courseId: number,
  payload: { title: string; week_number?: number; order?: number; description?: string },
): Promise<CourseLesson> {
  return apiPost<CourseLesson>(`${BASE}/courses/${courseId}/lessons/`, payload);
}

// ---------------------------------------------------------------------------
// Nested structure: topics, sessions, contents, assignments
// ---------------------------------------------------------------------------

export function addTopic(
  lessonId: number,
  payload: { title: string; order?: number; description?: string },
): Promise<LessonTopic> {
  return apiPost<LessonTopic>(`${BASE}/lessons/${lessonId}/topics/`, payload);
}

export function addSession(
  topicId: number,
  payload: { title: string; order?: number; description?: string },
): Promise<TopicSession> {
  return apiPost<TopicSession>(`${BASE}/topics/${topicId}/sessions/`, payload);
}

export function addContent(
  sessionId: number,
  payload: {
    title: string;
    content_format: "video" | "audio" | "text";
    content_url?: string;
    text_content?: string;
    duration_seconds?: number;
    order?: number;
  },
): Promise<SessionContent> {
  return apiPost<SessionContent>(`${BASE}/sessions/${sessionId}/contents/`, payload);
}

export function addAssignment(
  sessionId: number,
  payload: {
    title: string;
    description?: string;
    resource_url?: string;
    report_submission_enabled?: boolean;
    report_instructions?: string;
    order?: number;
  },
): Promise<Assignment> {
  return apiPost<Assignment>(`${BASE}/sessions/${sessionId}/assignments/`, payload);
}

// ---------------------------------------------------------------------------
// Edit / Delete nested resources
// ---------------------------------------------------------------------------

export function updateLesson(
  lessonId: number,
  payload: Record<string, unknown>,
): Promise<CourseLesson> {
  return apiPatch<CourseLesson>(`${BASE}/lessons/${lessonId}/`, payload);
}

export function deleteLesson(lessonId: number): Promise<void> {
  return apiDelete(`${BASE}/lessons/${lessonId}/`);
}

export function updateTopic(
  topicId: number,
  payload: Record<string, unknown>,
): Promise<LessonTopic> {
  return apiPatch<LessonTopic>(`${BASE}/topics/${topicId}/`, payload);
}

export function deleteTopic(topicId: number): Promise<void> {
  return apiDelete(`${BASE}/topics/${topicId}/`);
}

export function updateSession(
  sessionId: number,
  payload: Record<string, unknown>,
): Promise<TopicSession> {
  return apiPatch<TopicSession>(`${BASE}/sessions/${sessionId}/`, payload);
}

export function deleteSession(sessionId: number): Promise<void> {
  return apiDelete(`${BASE}/sessions/${sessionId}/`);
}

export function updateContent(
  contentId: number,
  payload: Record<string, unknown>,
): Promise<SessionContent> {
  return apiPatch<SessionContent>(`${BASE}/contents/${contentId}/`, payload);
}

export function deleteContent(contentId: number): Promise<void> {
  return apiDelete(`${BASE}/contents/${contentId}/`);
}

export function updateAssignment(
  assignmentId: number,
  payload: Record<string, unknown>,
): Promise<Assignment> {
  return apiPatch<Assignment>(
    `${BASE}/sessions/${assignmentId}/assignments/${assignmentId}/`,
    payload,
  );
}

export function deleteAssignment(assignmentId: number): Promise<void> {
  return apiDelete(`${BASE}/sessions/${assignmentId}/assignments/${assignmentId}/`);
}

export function updateLiveSession(
  liveSessionId: number,
  payload: Record<string, unknown>,
): Promise<LiveSession> {
  return apiPatch<LiveSession>(`${BASE}/live-sessions/${liveSessionId}/`, payload);
}

export function deleteLiveSession(liveSessionId: number): Promise<void> {
  return apiDelete(`${BASE}/live-sessions/${liveSessionId}/`);
}

export function deleteCategory(categoryId: number): Promise<void> {
  return apiDelete(`${BASE}/categories/${categoryId}/`);
}

// ---------------------------------------------------------------------------
// Zoom API (optional auto-create meetings)
// ---------------------------------------------------------------------------

export function getZoomConfig(): Promise<{ is_configured: boolean }> {
  return apiGet<{ is_configured: boolean }>(`${BASE}/zoom_config/`);
}

export function createZoomMeeting(payload: {
  topic: string;
  start_time: string;
  duration_minutes?: number;
}): Promise<{ join_url: string; meeting_id: string; password: string }> {
  return apiPost(`${BASE}/zoom_create_meeting/`, payload);
}

export function listLiveSessions(courseId: number): Promise<LiveSession[]> {
  return apiGet<LiveSession[]>(`${BASE}/courses/${courseId}/live_sessions/`);
}

export function addLiveSession(
  courseId: number,
  payload: {
    title: string;
    mode: "online" | "offline";
    meeting_url?: string;
    venue?: string;
    scheduled_at: string;
    duration_minutes?: number;
    description?: string;
  },
): Promise<LiveSession> {
  return apiPost<LiveSession>(`${BASE}/courses/${courseId}/live_sessions/`, payload);
}

export function addCourseAssessment(
  courseId: number,
  payload: {
    assessment: number;
    level: string;
    title: string;
    is_scored?: boolean;
    session?: number;
  },
): Promise<CourseAssessment> {
  return apiPost<CourseAssessment>(`${BASE}/courses/${courseId}/assessments/`, payload);
}

export function updateCourseAssessment(
  assessmentId: number,
  payload: Record<string, unknown>,
): Promise<CourseAssessment> {
  return apiPatch<CourseAssessment>(`${BASE}/course-assessments/${assessmentId}/`, payload);
}

export function deleteCourseAssessment(assessmentId: number): Promise<void> {
  return apiDelete(`${BASE}/course-assessments/${assessmentId}/`);
}

// ---------------------------------------------------------------------------
// Progress API
// ---------------------------------------------------------------------------

export function listProgress(registrationId: number): Promise<CourseProgress[]> {
  return apiGet<CourseProgress[]>(`${BASE}/registrations/${registrationId}/progress/`);
}

export function updateProgress(
  registrationId: number,
  payload: {
    content_type: string;
    content_id: number;
    is_completed?: boolean;
    time_spent_seconds?: number;
  },
): Promise<CourseProgress> {
  return apiPost<CourseProgress>(`${BASE}/registrations/${registrationId}/progress/`, payload);
}

export function getProgressSummary(registrationId: number): Promise<ProgressSummary> {
  return apiGet<ProgressSummary>(`${BASE}/registrations/${registrationId}/progress_summary/`);
}

// ---------------------------------------------------------------------------
// Messaging API (SRS §5)
// ---------------------------------------------------------------------------

export function listMessages(registrationId: number): Promise<CourseMessage[]> {
  return apiGet<CourseMessage[]>(`${BASE}/registrations/${registrationId}/messages/`);
}

export function sendMessage(registrationId: number, body: string): Promise<CourseMessage> {
  return apiPost<CourseMessage>(`${BASE}/registrations/${registrationId}/messages/`, { body });
}

// ---------------------------------------------------------------------------
// Assignment Reports API (SRS §2.3.2)
// ---------------------------------------------------------------------------

export function listAssignmentReports(registrationId: number): Promise<AssignmentReport[]> {
  return apiGet<AssignmentReport[]>(`${BASE}/registrations/${registrationId}/assignment_reports/`);
}

export function submitAssignmentReport(
  registrationId: number,
  payload: { assignment: number; report_text?: string; report_file_url?: string },
): Promise<AssignmentReport> {
  return apiPost<AssignmentReport>(
    `${BASE}/registrations/${registrationId}/assignment_reports/`,
    payload,
  );
}

export function reviewAssignmentReport(
  registrationId: number,
  payload: { report_id: number; trainer_score?: number; trainer_feedback?: string },
): Promise<AssignmentReport> {
  return apiPost<AssignmentReport>(
    `${BASE}/registrations/${registrationId}/review-report/`,
    payload,
  );
}

// ---------------------------------------------------------------------------
// Live Session Consent API (SRS §5)
// ---------------------------------------------------------------------------

export function consentToLiveSession(
  liveSessionId: number,
  status: "consented" | "declined",
): Promise<LiveSessionConsent> {
  return apiPost<LiveSessionConsent>(`${BASE}/live-sessions/${liveSessionId}/consent/`, {
    status,
  });
}

export function listLiveSessionConsents(liveSessionId: number): Promise<LiveSessionConsent[]> {
  return apiGet<LiveSessionConsent[]>(`${BASE}/live-sessions/${liveSessionId}/consents/`);
}

export function notifyLiveSessionStudents(
  liveSessionId: number,
): Promise<{ notified_count: number }> {
  return apiPost<{ notified_count: number }>(
    `${BASE}/live-sessions/${liveSessionId}/notify_students/`,
  );
}

// ---------------------------------------------------------------------------
// Interactive Questions API (SRS §2.3.1 Timeliner)
// ---------------------------------------------------------------------------

export function listInteractiveQuestions(contentId: number): Promise<InteractiveQuestion[]> {
  return apiGet<InteractiveQuestion[]>(`${BASE}/contents/${contentId}/interactive_questions/`);
}

export function createInteractiveQuestion(
  contentId: number,
  payload: {
    question_text: string;
    trigger_timestamp: number;
    options: InteractiveQuestionOption[];
    correct_jump_to: number;
    incorrect_jump_to: number;
  },
): Promise<InteractiveQuestion> {
  return apiPost<InteractiveQuestion>(
    `${BASE}/contents/${contentId}/interactive_questions/`,
    payload,
  );
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const COURSE_TYPES = [
  { value: "online_standard", label: "Online Standard (media-based)" },
  { value: "online_live", label: "Online Live (Zoom classroom)" },
  { value: "offline_live", label: "Offline Live (classroom)" },
];

export const SCHEDULE_TYPES = [
  { value: "non_scheduled", label: "Non-Scheduled (self-paced)" },
  { value: "scheduled", label: "Scheduled (fixed duration)" },
];

export const COURSE_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

export const LIVE_SESSION_MODES = [
  { value: "online", label: "Online (Zoom)" },
  { value: "offline", label: "Offline (Classroom)" },
];
