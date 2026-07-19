/**
 * Reporting API client.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/reporting";

export interface Report {
  id: number;
  title: string;
  objective: string;
  description: string;
  report_type: string;
  scope: string;
  status: string;
  assessment: number | null;
  assessment_title: string | null;
  profiling_solution: number | null;
  profiling_solution_title: string | null;
  include_score_summary: boolean;
  include_section_breakdown: boolean;
  include_question_analysis: boolean;
  include_charts: boolean;
  include_recommendations: boolean;
  header_text: string;
  footer_text: string;
  logo: string | null;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedReport {
  id: number;
  report: number;
  report_title: string;
  session: number;
  candidate: number;
  candidate_name: string | null;
  assessment_title: string | null;
  rendered_data: Record<string, unknown> | null;
  status: string;
  error_message: string;
  generated_at: string;
}

export function listReports(params?: {
  page?: number;
  search?: string;
  status?: string;
}): Promise<{ count: number; next: string | null; previous: string | null; results: Report[] }> {
  return apiGetPaged<Report>(`${BASE}/reports/`, {
    params: {
      page: params?.page ?? 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.status ? { status: params.status } : {}),
    },
  });
}

export function retrieveReport(id: number): Promise<Report> {
  return apiGet<Report>(`${BASE}/reports/${id}/`);
}

export function createReport(payload: Record<string, unknown>): Promise<Report> {
  return apiPost<Report>(`${BASE}/reports/`, payload);
}

export function updateReport(id: number, payload: Record<string, unknown>): Promise<Report> {
  return apiPatch<Report>(`${BASE}/reports/${id}/`, payload);
}

export function deleteReport(id: number): Promise<void> {
  return apiDelete(`${BASE}/reports/${id}/`);
}

export function publishReport(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`${BASE}/reports/${id}/publish/`);
}

export function generateReport(reportId: number, sessionId: number): Promise<GeneratedReport> {
  return apiPost<GeneratedReport>(`${BASE}/reports/${reportId}/generate/`, {
    session_id: sessionId,
  });
}

export function listGeneratedReports(reportId: number): Promise<GeneratedReport[]> {
  return apiGet<GeneratedReport[]>(`${BASE}/reports/${reportId}/generated/`);
}

export function retrieveGeneratedReport(id: number): Promise<GeneratedReport> {
  return apiGet<GeneratedReport>(`${BASE}/generated/${id}/`);
}

export const REPORT_TYPES = [
  { value: "descriptive", label: "Descriptive Report" },
  { value: "typological", label: "Typological Report" },
  { value: "interpretative", label: "Interpretative Report" },
];

export const REPORT_SCOPES = [
  { value: "general", label: "General (single assessment)" },
  { value: "profiling", label: "Profiling (multiple assessments)" },
];

export const REPORT_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];
