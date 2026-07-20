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
  data_input_level: string;
  stat_conversion: string;
  include_score_summary: boolean;
  include_section_breakdown: boolean;
  include_question_analysis: boolean;
  include_charts: boolean;
  include_recommendations: boolean;
  include_raw_summary: boolean;
  include_fmi: boolean;
  include_pmi: boolean;
  include_vmi: boolean;
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

// ---------------------------------------------------------------------------
// Group Report (SRS 04 — corporate managers view aggregated employee performance)
// ---------------------------------------------------------------------------

export interface GroupReportCandidate {
  id: number;
  name: string;
  email: string;
  total_score: number | null;
  percentage: number | null;
  session_id: number;
}

export interface GroupReportSectionAverage {
  section_id: number;
  section_title: string;
  average_percentage: number;
  min_percentage: number;
  max_percentage: number;
  candidate_count: number;
}

export interface GroupReportData {
  report_title: string;
  report_type: string;
  assessment_title: string;
  candidate_count: number;
  average_score: number;
  average_percentage: number;
  min_score: number;
  max_score: number;
  min_percentage: number;
  max_percentage: number;
  pass_threshold: number;
  pass_rate: number;
  pass_count: number;
  section_averages: GroupReportSectionAverage[];
  distribution: {
    "fail (0-40)": number;
    "below_avg (40-60)": number;
    "average (60-80)": number;
    "above_avg (80-100)": number;
  };
  candidates: GroupReportCandidate[];
}

export function generateGroupReport(
  reportId: number,
  sessionIds: number[],
): Promise<GroupReportData> {
  return apiPost<GroupReportData>(`${BASE}/reports/${reportId}/generate_group/`, {
    session_ids: sessionIds,
  });
}

// ---------------------------------------------------------------------------
// HFMI / LFMI Data Selection (SRS 06 §2.2)
// ---------------------------------------------------------------------------

export interface ProfilingSelectionCareer {
  id: number;
  career_stream: string;
  career_title: string;
  career_code: string;
  fmi: number | null;
  vmi: number | null;
}

export interface ProfilingSelectionResult {
  data_type: "HFMI" | "LFMI";
  extraction_mode: "user" | "system";
  total_available: number;
  selected_count: number;
  selected: ProfilingSelectionCareer[];
  fmi_range?: number[] | null;
  n_categories?: number;
  n_criterions?: number;
}

export function selectProfilingData(
  reportId: number,
  payload: {
    candidate_id: number;
    data_type: "HFMI" | "LFMI";
    extraction_mode: "user" | "system";
    fmi_range?: [number, number];
    n_categories?: number;
    n_criterions?: number;
    selected_career_titles?: string[];
  },
): Promise<ProfilingSelectionResult> {
  return apiPost<ProfilingSelectionResult>(`${BASE}/reports/${reportId}/select_data/`, payload);
}

export const REPORT_TYPES = [
  { value: "descriptive", label: "Descriptive Report" },
  { value: "typological", label: "Typological Report" },
  { value: "interpretative", label: "Interpretative Report" },
  { value: "group", label: "Group Report" },
];

export const REPORT_SCOPES = [
  { value: "general", label: "General (single assessment)" },
  { value: "profiling", label: "Profiling (multiple assessments)" },
];

export const DATA_INPUT_LEVELS = [
  { value: "level0", label: "Level 0 (entire assessment)" },
  { value: "level1", label: "Level 1 (all L1 variables)" },
  { value: "level2", label: "Level 2 (all L2 variables)" },
  { value: "level3", label: "Level 3 (all L3 variables)" },
  { value: "level4", label: "Level 4 (all L4 variables)" },
  { value: "question", label: "Question Level" },
];

export const STAT_CONVERSIONS = [
  { value: "percentage", label: "Percentage Score" },
  { value: "percentile", label: "Percentile Score" },
  { value: "sten", label: "STEN Score" },
  { value: "stenine", label: "STENINE Score" },
];

export const REPORT_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];
