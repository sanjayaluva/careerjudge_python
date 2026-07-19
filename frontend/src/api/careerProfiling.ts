/**
 * Career Profiling API client.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";
import { listAssessments } from "./assessment";

const BASE = "/career-profiling";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProfilingSolution {
  id: number;
  title: string;
  purpose: string;
  description: string;
  image: string | null;
  status: string;
  has_polar_assessment: boolean;
  created_by: number | null;
  created_by_name: string | null;
  assessment_count: number;
  selected_assessments: SelectedAssessment[];
  created_at: string;
  updated_at: string;
}

export interface SelectedAssessment {
  id: number;
  solution: number;
  assessment: number;
  assessment_detail?: {
    id: number;
    title: string;
    status: string;
    assessment_type: string;
  };
  label: string;
  is_polar: boolean;
  order: number;
  band_definitions: BandDefinition[];
}

export interface BandDefinition {
  id: number;
  selected_assessment: number;
  section: number;
  section_title: string;
  bands: Band[];
}

export interface Band {
  id: number;
  band_definition: number;
  band_number: number;
  range_min: number;
  range_max: number;
  band_code: string;
  sub_variable_name: string;
}

export interface MappingCriterion {
  id: number;
  solution: number;
  career_title: string;
  section: number;
  section_title: string;
  criterion_band_code: string;
  weight: number;
}

export interface MatchIndex {
  id: number;
  solution: number;
  candidate: number;
  candidate_name: string | null;
  career_title: string;
  variable_mapping_index: number | null;
  final_match_index: number | null;
  variable_details: Record<string, unknown> | null;
  computed_at: string;
}

// ---------------------------------------------------------------------------
// Solution CRUD
// ---------------------------------------------------------------------------

export function listSolutions(params?: {
  page?: number;
  search?: string;
  status?: string;
}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: ProfilingSolution[];
}> {
  return apiGetPaged<ProfilingSolution>(`${BASE}/solutions/`, {
    params: {
      page: params?.page ?? 1,
      ...(params?.search ? { search: params.search } : {}),
      ...(params?.status ? { status: params.status } : {}),
    },
  });
}

export function retrieveSolution(id: number): Promise<ProfilingSolution> {
  return apiGet<ProfilingSolution>(`${BASE}/solutions/${id}/`);
}

export function createSolution(payload: Record<string, unknown>): Promise<ProfilingSolution> {
  return apiPost<ProfilingSolution>(`${BASE}/solutions/`, payload);
}

export function updateSolution(
  id: number,
  payload: Record<string, unknown>,
): Promise<ProfilingSolution> {
  return apiPatch<ProfilingSolution>(`${BASE}/solutions/${id}/`, payload);
}

export function deleteSolution(id: number): Promise<void> {
  return apiDelete(`${BASE}/solutions/${id}/`);
}

export function publishSolution(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`${BASE}/solutions/${id}/publish/`);
}

// ---------------------------------------------------------------------------
// Selected Assessments
// ---------------------------------------------------------------------------

export function listSolutionAssessments(solutionId: number): Promise<SelectedAssessment[]> {
  return apiGet<SelectedAssessment[]>(`${BASE}/solutions/${solutionId}/assessments/`);
}

export function addSolutionAssessment(
  solutionId: number,
  payload: { assessment: number; label: string; is_polar?: boolean; order?: number },
): Promise<SelectedAssessment> {
  return apiPost<SelectedAssessment>(`${BASE}/solutions/${solutionId}/assessments/`, payload);
}

// ---------------------------------------------------------------------------
// Band Definitions
// ---------------------------------------------------------------------------

export function listBands(solutionId: number): Promise<BandDefinition[]> {
  return apiGet<BandDefinition[]>(`${BASE}/solutions/${solutionId}/bands/`);
}

export function createBandDefinition(
  solutionId: number,
  payload: { selected_assessment: number; section: number },
): Promise<BandDefinition> {
  return apiPost<BandDefinition>(`${BASE}/solutions/${solutionId}/bands/`, payload);
}

// ---------------------------------------------------------------------------
// Mapping Criteria
// ---------------------------------------------------------------------------

export function listCriteria(solutionId: number): Promise<MappingCriterion[]> {
  return apiGet<MappingCriterion[]>(`${BASE}/solutions/${solutionId}/criteria/`);
}

export function createCriterion(
  solutionId: number,
  payload: { career_title: string; section: number; criterion_band_code: string; weight?: number },
): Promise<MappingCriterion> {
  return apiPost<MappingCriterion>(`${BASE}/solutions/${solutionId}/criteria/`, payload);
}

// ---------------------------------------------------------------------------
// Match Indices
// ---------------------------------------------------------------------------

export function listMatchIndices(solutionId: number): Promise<MatchIndex[]> {
  return apiGet<MatchIndex[]>(`${BASE}/solutions/${solutionId}/match_indices/`);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const SOLUTION_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

// Re-export for convenience (used by the detail page to list available assessments)
export { listAssessments };
