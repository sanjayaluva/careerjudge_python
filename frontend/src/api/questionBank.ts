/**
 * Question Bank API functions.
 */
import { apiDelete, apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/question-bank";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Category {
  id: number;
  name: string;
  parent: number | null;
  description: string;
  is_active: boolean;
  question_count: number;
  subcategory_count: number;
  full_path: string;
}

export interface QuestionListItem {
  id: number;
  question_type: string;
  question_type_label: string;
  question_id_label: string;
  question_title: string;
  question_text_1: string;
  category: number | null;
  category_name: string | null;
  status: string;
  status_label: string;
  scoring_type: string;
  scoring_type_label: string;
  difficulty_level: string;
  cognitive_level: string;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  exposure_count: number;
}

export interface ResponseOption {
  id: number;
  sub_question_index: number;
  option_type: string;
  label: string;
  text_value: string;
  image_file: string | null;
  is_correct: boolean;
  match_pair_id: number | null;
  predefined_score: number;
  order: number;
  correct_answers: { id: number; answer_text: string; order: number }[];
}

export interface QuestionDetail extends QuestionListItem {
  question_text_2: string;
  image: string | null;
  order: number;
  case_sensitive: boolean;
  pct_match_threshold: number | null;
  display_duration_seconds: number | null;
  flash_interval_ms: number | null;
  flash_display_count: number | null;
  flash_order: string;
  grid_rows: number | null;
  grid_cols: number | null;
  rating_scale_points: number | null;
  rating_direction: string | null;
  passage_title: string;
  passage_body: string;
  exposure_limit: number | null;
  discrimination_index: number | null;
  options: ResponseOption[];
  media_files: { id: number; media_type: string; file: string; created_at: string }[];
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
    sub_question_index: number;
    x: number;
    y: number;
    width_px: number;
    height_px: number;
    area_size_code: string;
  }[];
  reviews: {
    id: number;
    reviewer_name: string;
    review_type: string;
    review_type_label: string;
    action: string;
    action_label: string;
    comment: string;
    rating: number | null;
    created_at: string;
  }[];
}

export interface QuestionReview {
  id: number;
  question: number;
  reviewer: number | null;
  reviewer_name: string | null;
  review_type: string;
  review_type_label: string;
  action: string;
  action_label: string;
  comment: string;
  rating: number | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Category API
// ---------------------------------------------------------------------------

export function listCategories(params?: { parent?: string }): Promise<Category[]> {
  return apiGetPaged<Category>(`${BASE}/categories/`, {
    params: params || {},
  }).then((r) => r.results);
}

export function retrieveCategory(id: number): Promise<Category> {
  return apiGet<Category>(`${BASE}/categories/${id}/`);
}

export function createCategory(payload: {
  name: string;
  parent?: number | null;
  description?: string;
}): Promise<Category> {
  return apiPost<Category>(`${BASE}/categories/`, payload);
}

export function updateCategory(
  id: number,
  payload: Partial<{ name: string; description: string; is_active: boolean }>,
): Promise<Category> {
  return apiPatch<Category>(`${BASE}/categories/${id}/`, payload);
}

export function deleteCategory(id: number): Promise<void> {
  return apiDelete(`${BASE}/categories/${id}/`);
}

export function getCategoryTree(): Promise<unknown> {
  return apiGet(`${BASE}/categories/tree/`);
}

// ---------------------------------------------------------------------------
// Question API
// ---------------------------------------------------------------------------

export interface QuestionListParams {
  page?: number;
  search?: string;
  category?: number;
  question_type?: string;
  status?: string;
  difficulty?: string;
  mine?: boolean;
}

export function listQuestions(params: QuestionListParams = {}): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: QuestionListItem[];
}> {
  return apiGetPaged<QuestionListItem>(`${BASE}/questions/`, {
    params: {
      page: params.page ?? 1,
      ...(params.search ? { search: params.search } : {}),
      ...(params.category ? { category: params.category } : {}),
      ...(params.question_type ? { question_type: params.question_type } : {}),
      ...(params.status ? { status: params.status } : {}),
      ...(params.difficulty ? { difficulty: params.difficulty } : {}),
      ...(params.mine ? { mine: "true" } : {}),
    },
  });
}

export function retrieveQuestion(id: number): Promise<QuestionDetail> {
  return apiGet<QuestionDetail>(`${BASE}/questions/${id}/`);
}

export function createQuestion(payload: Record<string, unknown>): Promise<QuestionDetail> {
  return apiPost<QuestionDetail>(`${BASE}/questions/`, payload);
}

export function updateQuestion(
  id: number,
  payload: Record<string, unknown>,
): Promise<QuestionDetail> {
  return apiPatch<QuestionDetail>(`${BASE}/questions/${id}/`, payload);
}

export function deleteQuestion(id: number): Promise<void> {
  return apiDelete(`${BASE}/questions/${id}/`);
}

export function submitForReview(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`${BASE}/questions/${id}/submit_for_review/`);
}

// ---------------------------------------------------------------------------
// Review API
// ---------------------------------------------------------------------------

export function submitReview(
  questionId: number,
  payload: {
    review_type: string;
    action: string;
    comment?: string;
    rating?: number;
    exposure_limit?: number;
  },
): Promise<{ review: QuestionReview; question_status: string }> {
  return apiPost(`${BASE}/questions/${questionId}/review/`, payload);
}

export function listReviews(questionId: number): Promise<QuestionReview[]> {
  return apiGet<QuestionReview[]>(`${BASE}/questions/${questionId}/reviews/`);
}

// ---------------------------------------------------------------------------
// Child resource APIs (options, media, flash items, hotspots)
// ---------------------------------------------------------------------------

export function listOptions(questionId: number): Promise<ResponseOption[]> {
  return apiGetPaged<ResponseOption>(`${BASE}/questions/${questionId}/options/`).then(
    (r) => r.results,
  );
}

export function bulkSaveOptions(
  questionId: number,
  options: Record<string, unknown>[],
): Promise<ResponseOption[]> {
  return apiPost<ResponseOption[]>(`${BASE}/questions/${questionId}/options/bulk/`, { options });
}

export function createOption(
  questionId: number,
  payload: Partial<ResponseOption>,
): Promise<ResponseOption> {
  return apiPost<ResponseOption>(`${BASE}/questions/${questionId}/options/`, payload);
}

export function updateOption(
  questionId: number,
  optionId: number,
  payload: Partial<ResponseOption>,
): Promise<ResponseOption> {
  return apiPatch<ResponseOption>(`${BASE}/questions/${questionId}/options/${optionId}/`, payload);
}

export function deleteOption(questionId: number, optionId: number): Promise<void> {
  return apiDelete(`${BASE}/questions/${questionId}/options/${optionId}/`);
}

export function createMediaFile(
  questionId: number,
  payload: { media_type: string; file: string },
): Promise<unknown> {
  return apiPost(`${BASE}/questions/${questionId}/media/`, payload);
}

export function deleteMediaFile(questionId: number, mediaId: number): Promise<void> {
  return apiDelete(`${BASE}/questions/${questionId}/media/${mediaId}/`);
}

export function createFlashItem(
  questionId: number,
  payload: Record<string, unknown>,
): Promise<unknown> {
  return apiPost(`${BASE}/questions/${questionId}/flash-items/`, payload);
}

export function deleteFlashItem(questionId: number, itemId: number): Promise<void> {
  return apiDelete(`${BASE}/questions/${questionId}/flash-items/${itemId}/`);
}

export function createHotspot(
  questionId: number,
  payload: Record<string, unknown>,
): Promise<unknown> {
  return apiPost(`${BASE}/questions/${questionId}/hotspots/`, payload);
}

export function deleteHotspot(questionId: number, hotspotId: number): Promise<void> {
  return apiDelete(`${BASE}/questions/${questionId}/hotspots/${hotspotId}/`);
}

export const QUESTION_TYPES = [
  { value: "MCQ_TEXT_IMAGE", label: "1a: MCQ – Text/Image" },
  { value: "MCQ_TEXT_IMAGE_IMG_OPTIONS", label: "1b: MCQ – Text/Image with Image Options" },
  { value: "MCQ_AUDIO_MULTI", label: "1c: MCQ – Audio with Multiple Questions" },
  { value: "MCQ_VIDEO_MULTI", label: "1d: MCQ – Video with Multiple Questions" },
  { value: "MCQ_WORD_FLASH_MULTI", label: "1e: MCQ – Word Flash" },
  { value: "MCQ_IMAGE_FLASH_MULTI", label: "1f: MCQ – Image Flash" },
  { value: "MCQ_PASSAGE_DISPLAY_MULTI", label: "1g: MCQ – Passage Display" },
  { value: "MCQ_IMAGE_DISPLAY_MULTI", label: "1h: MCQ – Image Display" },
  { value: "FITB_SINGLE", label: "2a: FITB – Single Field" },
  { value: "FITB_MULTI_FIELD", label: "2b: FITB – Multiple Fields" },
  { value: "FITB_WORD_FLASH_MULTI", label: "2c: FITB – Word Flash" },
  { value: "FITB_IMAGE_FLASH_MULTI", label: "2d: FITB – Image Flash" },
  { value: "MATCH_FOLLOWING", label: "3: Match-the-Following" },
  { value: "GRID_LIST_SELECTION", label: "4: Grid-List Selection" },
  { value: "HOTSPOT_SINGLE", label: "5a: Hotspot – Single Answer" },
  { value: "HOTSPOT_MULTI", label: "5b: Hotspot – Multiple Answers" },
  { value: "RANK_SIMPLE", label: "6a: Simple Ranking Scale" },
  { value: "RANK_THEN_RATE", label: "6b: Rank-then-Rate Scale" },
  { value: "STANDARD_RATING_SCALE", label: "7: Standard Rating Scale" },
  { value: "FORCED_CHOICE_SINGLE_LEVEL", label: "8a: Forced-Choice – Single Level" },
  { value: "FORCED_CHOICE_TWO_LEVEL", label: "8b: Forced-Choice – Two-Level" },
];

export const SCORING_TYPES = [
  {
    value: "BINARY",
    label: "Binary (0 or 1)",
    description:
      "The candidate gets 1 point if the answer is exactly correct, 0 otherwise. Used for MCQ with a single correct answer, FITB single-field with exact match, and Hotspot single-answer.",
  },
  {
    value: "BINARY_FUZZY",
    label: "Binary with Fuzzy Match",
    description:
      "Same as Binary (0 or 1) but allows a percentage match threshold (e.g. 80%) for FITB answers — partial spelling differences are accepted. Set the match threshold in the FITB options.",
  },
  {
    value: "PARTIAL",
    label: "Partial Credit",
    description:
      "The candidate gets partial credit for each correct option selected (e.g. 0.25 per correct option in a 4-option MCQ). Used for MCQ with multiple correct answers and Match-the-Following.",
  },
  {
    value: "NEGATIVE",
    label: "Negative Marking",
    description:
      "Correct answer = +1, wrong answer = negative fraction (e.g. -0.25). Discourages guessing. Used in competitive exams. The negative fraction is configured per-question.",
  },
  {
    value: "RANK",
    label: "Rank Scoring",
    description:
      "Candidate ranks items; score = (number of items in correct relative order) / total items. Used for Rank-Simple (6a) questions.",
  },
  {
    value: "RANK_RATE",
    label: "Rank-then-Rate",
    description:
      "Two-stage: candidate ranks items first, then rates each. Final score combines rank order + rating values. Used for Rank-then-Rate (6b) questions.",
  },
  {
    value: "RATING",
    label: "Rating Scale",
    description:
      "Candidate picks a point on a scale (e.g. 1-5 Likert). Score = the rating value itself (no right/wrong answer). Used for Standard Rating Scale (7) questions.",
  },
  {
    value: "FORCED_CHOICE",
    label: "Forced-Choice",
    description:
      "Candidate must choose between two statements (no neutral option). Each statement has a predefined score. Used for Forced-Choice Single-Level (8a) questions.",
  },
  {
    value: "FORCED_CHOICE_RATED",
    label: "Forced-Choice Two-Level",
    description:
      "Two-stage: candidate picks a statement, then rates it. Score = statement's predefined score × rating. Used for Forced-Choice Two-Level (8b) questions.",
  },
];

export const QUESTION_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "pending_content_review", label: "Pending Content Review" },
  { value: "content_reviewed", label: "Content Reviewed" },
  { value: "pending_psychometric_review", label: "Pending Psychometric Review" },
  { value: "confirmed", label: "Confirmed (In Question Bank)" },
  { value: "sent_back", label: "Sent Back" },
  { value: "rejected", label: "Rejected" },
  { value: "inactive", label: "Inactive" },
];

export const DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"];
