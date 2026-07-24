/**
 * Task Management API client.
 * SRS 09 §3 — Admin assigns + monitors tasks for SME / Reviewer / Psychometrician / Trainer / Counsellor.
 */
import { apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/tasks";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type TaskStatus =
  "pending" | "in_progress" | "awaiting_review" | "completed" | "cancelled" | "overdue";

export type TaskPriority = "low" | "medium" | "high" | "urgent";

export type AssigneeRole = "sme" | "reviewer" | "psychometrician" | "trainer" | "counsellor";

export interface TaskSpec {
  qb_category?: string;
  qb_subcategory?: string;
  question_type?: string;
  num_questions?: number | null;
  num_options?: number | null;
  num_correct_options?: number | null;
  difficulty_level?: "" | "easy" | "medium" | "hard" | "expert";
  cognitive_level?: "" | "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
}

export interface TaskProgressUpdate {
  id: number;
  task: number;
  author: number | null;
  author_name: string;
  author_role: "assignee" | "admin" | "system";
  message: string;
  is_admin_request: boolean;
  created_at: string;
}

export interface TaskExtensionRequest {
  id: number;
  task: number;
  requested_by: number;
  requested_by_name: string;
  current_due_date: string;
  requested_due_date: string;
  reason: string;
  status: "pending" | "approved" | "declined";
  reviewed_by: number | null;
  review_comment: string;
  reviewed_at: string | null;
  created_at: string;
}

export interface Task {
  id: number;
  task_id: string;
  title: string;
  description: string;
  assigned_by: number;
  assigned_by_name: string;
  assigned_to: number;
  assigned_to_name: string;
  assignee_role: AssigneeRole;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  is_overdue: boolean;
  created_at: string;
  completed_at: string | null;
  cancelled_at: string | null;
  started_at: string | null;
  approval_comment: string;
  cancellation_reason: string;
  spec?: TaskSpec;
  progress_updates?: TaskProgressUpdate[];
  extension_requests?: TaskExtensionRequest[];
  parent_task?: number | null;
  parent_task_id?: string | null;
}

export interface TaskCreateInput {
  title: string;
  description: string;
  assigned_to: number;
  assignee_role: AssigneeRole;
  priority?: TaskPriority;
  due_date?: string | null;
  parent_task_id?: string;
  spec?: TaskSpec;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const tasksApi = {
  list: () => apiGetPaged<Task>(`${BASE}/`),
  retrieve: (id: number) => apiGet<Task>(`${BASE}/${id}/`),
  create: (input: TaskCreateInput) => apiPost<Task>(`${BASE}/`, input),
  update: (id: number, input: Partial<TaskCreateInput>) => apiPatch<Task>(`${BASE}/${id}/`, input),

  start: (id: number) => apiPost<Task>(`${BASE}/${id}/start/`),
  submit: (id: number, message: string) => apiPost<Task>(`${BASE}/${id}/submit/`, { message }),
  approve: (id: number, comment: string) => apiPost<Task>(`${BASE}/${id}/approve/`, { comment }),
  cancel: (id: number, reason: string) => apiPost<Task>(`${BASE}/${id}/cancel/`, { reason }),
  requestUpdate: (id: number, message: string) =>
    apiPost<Task>(`${BASE}/${id}/request_update/`, { message }),

  // Progress updates
  listProgress: (id: number) =>
    apiGet<{ message: string; data: TaskProgressUpdate[] }>(`${BASE}/${id}/progress/`),
  postProgress: (id: number, message: string) =>
    apiPost<TaskProgressUpdate>(`${BASE}/${id}/progress/`, { message }),

  // Extension requests
  listExtensions: (id: number) =>
    apiGet<{ message: string; data: TaskExtensionRequest[] }>(`${BASE}/${id}/extensions/`),
  requestExtension: (id: number, requested_due_date: string, reason: string) =>
    apiPost<TaskExtensionRequest>(`${BASE}/${id}/extensions/`, {
      requested_due_date,
      reason,
    }),
  approveExtension: (extId: number, comment: string) =>
    apiPost<TaskExtensionRequest>(`${BASE}/extensions/${extId}/approve/`, { comment }),
  declineExtension: (extId: number, comment: string) =>
    apiPost<TaskExtensionRequest>(`${BASE}/extensions/${extId}/decline/`, { comment }),

  // Filters
  myTasks: () => apiGetPaged<Task>(`${BASE}/my_tasks/`),
  assigned: () => apiGetPaged<Task>(`${BASE}/assigned/`),
};
