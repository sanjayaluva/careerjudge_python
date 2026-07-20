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
