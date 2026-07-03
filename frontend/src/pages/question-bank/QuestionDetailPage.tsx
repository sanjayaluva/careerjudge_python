import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Modal,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui";
import { retrieveQuestion, submitForReview, submitReview } from "@/api/questionBank";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import type { QuestionDetail } from "@/api/questionBank";
import { QuestionEditorModal } from "./QuestionEditorModal";

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning" | "primary"> = {
  draft: "default",
  pending_content_review: "warning",
  content_reviewed: "primary",
  pending_psychometric_review: "warning",
  confirmed: "success",
  sent_back: "default",
  rejected: "default",
  inactive: "default",
};

// ---------------------------------------------------------------------------
// Type-specific field visibility config
// ---------------------------------------------------------------------------

interface FieldConfig {
  key: keyof QuestionDetail;
  label: string;
  showForTypes?: string[]; // if undefined, show for all types
  format?: (val: unknown) => string;
}

const TYPE_SPECIFIC_FIELDS: FieldConfig[] = [
  {
    key: "case_sensitive",
    label: "Case Sensitive",
    showForTypes: [
      "FITB_SINGLE",
      "FITB_MULTI_FIELD",
      "FITB_WORD_FLASH_MULTI",
      "FITB_IMAGE_FLASH_MULTI",
    ],
  },
  { key: "pct_match_threshold", label: "Match Threshold (%)", showForTypes: ["FITB_SINGLE"] },
  {
    key: "display_duration_seconds",
    label: "Display Duration (sec)",
    showForTypes: ["MCQ_PASSAGE_DISPLAY_MULTI", "MCQ_IMAGE_DISPLAY_MULTI"],
  },
  {
    key: "flash_interval_ms",
    label: "Flash Interval (ms)",
    showForTypes: [
      "MCQ_WORD_FLASH_MULTI",
      "MCQ_IMAGE_FLASH_MULTI",
      "FITB_WORD_FLASH_MULTI",
      "FITB_IMAGE_FLASH_MULTI",
    ],
  },
  {
    key: "flash_display_count",
    label: "Flash Display Count",
    showForTypes: [
      "MCQ_WORD_FLASH_MULTI",
      "MCQ_IMAGE_FLASH_MULTI",
      "FITB_WORD_FLASH_MULTI",
      "FITB_IMAGE_FLASH_MULTI",
    ],
  },
  { key: "grid_rows", label: "Grid Rows", showForTypes: ["GRID_LIST_SELECTION"] },
  { key: "grid_cols", label: "Grid Columns", showForTypes: ["GRID_LIST_SELECTION"] },
  {
    key: "rating_scale_points",
    label: "Rating Scale Points",
    showForTypes: ["RANK_THEN_RATE", "STANDARD_RATING_SCALE", "FORCED_CHOICE_TWO_LEVEL"],
  },
  { key: "rating_direction", label: "Rating Direction", showForTypes: ["STANDARD_RATING_SCALE"] },
  { key: "passage_title", label: "Passage Title", showForTypes: ["MCQ_PASSAGE_DISPLAY_MULTI"] },
  { key: "passage_body", label: "Passage Body", showForTypes: ["MCQ_PASSAGE_DISPLAY_MULTI"] },
  { key: "discrimination_index", label: "Discrimination Index" },
];

const COMMON_FIELDS: FieldConfig[] = [
  { key: "question_id_label", label: "Question ID Label" },
  { key: "scoring_type_label", label: "Scoring Type" },
  { key: "difficulty_level", label: "Difficulty Level" },
  { key: "cognitive_level", label: "Cognitive Level" },
  { key: "exposure_limit", label: "Exposure Limit" },
  { key: "exposure_count", label: "Exposure Count" },
];

function shouldShowField(field: FieldConfig, questionType: string): boolean {
  if (!field.showForTypes) return true;
  return field.showForTypes.includes(questionType);
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  return String(val);
}

// ---------------------------------------------------------------------------

export default function QuestionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qid = Number(id);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [reviewOpen, setReviewOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    data: question,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["question-bank", "questions", qid],
    queryFn: () => retrieveQuestion(qid),
    enabled: !Number.isNaN(qid),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitForReview(qid),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["question-bank", "questions", qid] }),
    onError: (err) => setError(extractApiError(err)),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !question) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load question.</AlertDescription>
      </Alert>
    );
  }

  const q = question as QuestionDetail;
  const isAdmin = user?.role === "cj_admin";
  const canEditAnyQuestion = ["sme", "psychometrician", "cj_admin"].includes(user?.role ?? "");
  // Edit rules: cj_admin can edit ANY question; others can edit only draft/sent_back.
  const canEdit =
    isAdmin || (canEditAnyQuestion && (q.status === "draft" || q.status === "sent_back"));
  const canSubmit =
    (q.status === "draft" || q.status === "sent_back") &&
    ["sme", "cj_admin"].includes(user?.role ?? "");
  const canReviewContent =
    q.status === "pending_content_review" && ["reviewer", "cj_admin"].includes(user?.role ?? "");
  const canReviewPsychometric =
    q.status === "pending_psychometric_review" &&
    ["psychometrician", "cj_admin"].includes(user?.role ?? "");

  const visibleTypeFields = TYPE_SPECIFIC_FIELDS.filter((f) => shouldShowField(f, q.question_type));
  const hasMedia =
    q.image || q.media_files.length > 0 || q.flash_items.length > 0 || q.hotspot_areas.length > 0;
  const hasOptions = q.options.length > 0;

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div>
        <Link to="/question-bank" className="text-sm text-primary-600 hover:underline">
          ← Back to Question Bank
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">{q.question_type_label}</h1>
          <Badge variant={STATUS_VARIANTS[q.status] ?? "default"}>{q.status_label}</Badge>
          {q.difficulty_level && <Badge variant="outline">Difficulty: {q.difficulty_level}</Badge>}
          {q.cognitive_level && <Badge variant="outline">Cognitive: {q.cognitive_level}</Badge>}
        </div>
      </div>

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="options">Options ({q.options.length})</TabsTrigger>
          <TabsTrigger value="media">
            Media ({q.image ? 1 : 0 + q.media_files.length + q.flash_items.length})
          </TabsTrigger>
          <TabsTrigger value="reviews">Reviews ({q.reviews.length})</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>

        {/* === DETAILS TAB === */}
        <TabsContent value="details">
          <Card>
            <CardHeader>
              <CardTitle>Question Properties</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2">
                {/* Question text — always shown */}
                <div className="py-1 sm:col-span-2">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Question Text
                  </dt>
                  <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                    {q.question_text_1}
                  </dd>
                </div>
                {q.question_text_2 && (
                  <div className="py-1 sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Additional Text
                    </dt>
                    <dd className="mt-1 text-sm text-slate-900">{q.question_text_2}</dd>
                  </div>
                )}

                {/* Common fields */}
                {COMMON_FIELDS.map((f) => (
                  <div key={f.key} className="py-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      {f.label}
                    </dt>
                    <dd className="text-sm text-slate-900">{formatValue(q[f.key])}</dd>
                  </div>
                ))}

                {/* Type-specific fields — only show relevant ones */}
                {visibleTypeFields.map((f) => {
                  const val = q[f.key];
                  if (val === null || val === undefined || val === "" || val === false) return null;
                  return (
                    <div key={f.key} className="py-1">
                      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        {f.label}
                      </dt>
                      <dd className="text-sm text-slate-900">{formatValue(val)}</dd>
                    </div>
                  );
                })}

                {/* Passage body — special rendering */}
                {q.passage_body && visibleTypeFields.some((f) => f.key === "passage_body") && (
                  <div className="py-1 sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Passage Body
                    </dt>
                    <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                      {q.passage_body}
                    </dd>
                  </div>
                )}

                {/* Audit */}
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created By
                  </dt>
                  <dd className="text-sm text-slate-900">{q.created_by_name || "—"}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created At
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {new Date(q.created_at).toLocaleString()}
                  </dd>
                </div>
              </dl>

              <div className="mt-6 flex gap-2 border-t border-slate-100 pt-4">
                {canEdit && (
                  <Button variant="outline" onClick={() => setEditorOpen(true)}>
                    Edit question
                  </Button>
                )}
                {canSubmit && (
                  <Button
                    loading={submitMutation.isPending}
                    onClick={() => submitMutation.mutate()}
                  >
                    Submit for Review
                  </Button>
                )}
                {canReviewContent && (
                  <Button onClick={() => setReviewOpen(true)}>Review (Content)</Button>
                )}
                {canReviewPsychometric && (
                  <Button onClick={() => setReviewOpen(true)}>Review (Psychometric)</Button>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* === OPTIONS TAB === */}
        <TabsContent value="options">
          <Card>
            <CardHeader>
              <CardTitle>Response Options</CardTitle>
            </CardHeader>
            <CardContent>
              {q.options.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">
                  No response options attached. Options are added via the question editor during
                  creation/editing.
                </p>
              ) : (
                <div className="space-y-3">
                  {q.options.map((opt) => (
                    <div key={opt.id} className="rounded-md border border-slate-200 p-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{opt.option_type}</Badge>
                        {opt.is_correct && <Badge variant="success">✓ Correct</Badge>}
                        {opt.match_pair_id !== null && (
                          <Badge variant="default">Pair #{opt.match_pair_id}</Badge>
                        )}
                        <span className="ml-auto text-xs text-slate-400">
                          Sub-Q: {opt.sub_question_index} · Order: {opt.order}
                        </span>
                      </div>
                      {opt.text_value && (
                        <p className="mt-2 text-sm text-slate-900">{opt.text_value}</p>
                      )}
                      {opt.image_file && (
                        <img
                          src={opt.image_file}
                          alt="Option"
                          className="mt-2 max-h-32 rounded border border-slate-200"
                        />
                      )}
                      {opt.predefined_score !== 1.0 && (
                        <p className="mt-1 text-xs text-slate-500">Score: {opt.predefined_score}</p>
                      )}
                      {opt.correct_answers.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-slate-500">Accepted Answers:</p>
                          <ul className="ml-4 list-disc text-xs text-slate-600">
                            {opt.correct_answers.map((ca) => (
                              <li key={ca.id}>{ca.answer_text}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === MEDIA TAB === */}
        <TabsContent value="media">
          <Card>
            <CardHeader>
              <CardTitle>Media Files</CardTitle>
            </CardHeader>
            <CardContent>
              {!hasMedia ? (
                <p className="py-4 text-center text-sm text-slate-500">
                  No media files attached to this question.
                </p>
              ) : (
                <div className="space-y-4">
                  {q.image && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                        Question Image
                      </p>
                      <img
                        src={q.image}
                        alt="Question"
                        className="max-h-60 rounded border border-slate-200"
                      />
                    </div>
                  )}
                  {q.media_files.map((mf) => (
                    <div key={mf.id} className="rounded-md border border-slate-200 p-3">
                      <Badge variant="default">{mf.media_type}</Badge>
                      {mf.media_type === "AUDIO" && (
                        <audio controls src={mf.file} className="mt-2 w-full" />
                      )}
                      {mf.media_type === "VIDEO" && (
                        <video controls src={mf.file} className="mt-2 max-h-40 w-full rounded" />
                      )}
                    </div>
                  ))}
                  {q.flash_items.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                        Flash Items ({q.flash_items.length})
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {q.flash_items.map((fi) => (
                          <div key={fi.id} className="rounded-md border border-slate-200 p-2">
                            {fi.item_type === "TEXT" ? (
                              <span className="text-sm text-slate-700">{fi.text_value}</span>
                            ) : (
                              fi.image_file && (
                                <img
                                  src={fi.image_file}
                                  alt="Flash"
                                  className="h-12 w-12 rounded"
                                />
                              )
                            )}
                            {!fi.is_in_display_pool && (
                              <span className="ml-1 text-xs text-slate-400">(excluded)</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {q.hotspot_areas.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                        Hotspot Areas ({q.hotspot_areas.length})
                      </p>
                      {q.image && (
                        <div className="relative inline-block">
                          <img
                            src={q.image}
                            alt="Hotspot"
                            className="max-w-md rounded border border-slate-300"
                          />
                          {q.hotspot_areas.map((ha, i) => (
                            <div
                              key={ha.id}
                              className="absolute border-2 border-success-500/50 bg-success-500/10"
                              style={{
                                left: `${ha.x}px`,
                                top: `${ha.y}px`,
                                width: `${ha.width_px}px`,
                                height: `${ha.height_px}px`,
                              }}
                            >
                              <span className="absolute -top-5 left-0 text-xs text-success-600">
                                Zone {i + 1}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === REVIEWS TAB === */}
        <TabsContent value="reviews">
          <Card>
            <CardHeader>
              <CardTitle>Review History</CardTitle>
            </CardHeader>
            <CardContent>
              {q.reviews.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">No reviews yet.</p>
              ) : (
                <div className="space-y-4">
                  {q.reviews.map((review) => (
                    <div key={review.id} className="rounded-md border border-slate-200 p-4">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            review.action === "approve"
                              ? "success"
                              : review.action === "send_back"
                                ? "warning"
                                : "default"
                          }
                        >
                          {review.action_label}
                        </Badge>
                        <Badge variant="outline">{review.review_type_label}</Badge>
                        {review.rating && (
                          <Badge variant="primary">Rating: {review.rating}/5</Badge>
                        )}
                      </div>
                      {review.comment && (
                        <p className="mt-2 text-sm text-slate-600">{review.comment}</p>
                      )}
                      <p className="mt-2 text-xs text-slate-400">
                        by {review.reviewer_name || "Unknown"} on{" "}
                        {new Date(review.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === PREVIEW TAB === */}
        <TabsContent value="preview">
          <Card>
            <CardHeader>
              <CardTitle>Candidate Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border-2 border-slate-200 bg-white p-6">
                {q.question_id_label && (
                  <p className="mb-2 text-xs font-medium text-slate-400">{q.question_id_label}</p>
                )}
                {q.passage_title && (
                  <div className="mb-4 rounded-md bg-slate-50 p-4">
                    <p className="font-semibold text-slate-900">{q.passage_title}</p>
                    {q.passage_body && (
                      <p className="mt-2 text-sm text-slate-700">{q.passage_body}</p>
                    )}
                  </div>
                )}
                {q.image && (
                  <img
                    src={q.image}
                    alt="Question"
                    className="mb-4 max-h-60 rounded border border-slate-200"
                  />
                )}
                {q.media_files.map((mf) => (
                  <div key={mf.id} className="mb-4">
                    {mf.media_type === "AUDIO" && (
                      <audio controls src={mf.file} className="w-full" />
                    )}
                    {mf.media_type === "VIDEO" && (
                      <video controls src={mf.file} className="max-h-60 w-full rounded" />
                    )}
                  </div>
                ))}
                {q.flash_items.length > 0 && (
                  <div className="mb-4">
                    <p className="mb-2 text-xs text-slate-500">
                      Flash items ({q.flash_display_count || q.flash_items.length} shown at{" "}
                      {q.flash_interval_ms || "?"}ms intervals):
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {q.flash_items
                        .filter((fi) => fi.is_in_display_pool)
                        .map((fi) => (
                          <div
                            key={fi.id}
                            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm"
                          >
                            {fi.item_type === "TEXT"
                              ? fi.text_value
                              : fi.image_file && (
                                  <img src={fi.image_file} alt="" className="h-8 w-8" />
                                )}
                          </div>
                        ))}
                    </div>
                  </div>
                )}
                <p className="mb-4 text-base font-medium text-slate-900">{q.question_text_1}</p>
                {q.question_text_2 && (
                  <p className="mb-4 text-sm text-slate-600">{q.question_text_2}</p>
                )}

                {/* Options rendered by type */}
                {hasOptions && (
                  <div className="space-y-2">
                    {/* MCQ: radio or checkbox */}
                    {q.question_type.startsWith("MCQ_") && (
                      <>
                        {q.options.filter((o) => o.is_correct).length > 1
                          ? q.options.map((opt, i) => (
                              <label
                                key={opt.id}
                                className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm"
                              >
                                <input type="checkbox" disabled className="h-4 w-4" />
                                {opt.image_file && (
                                  <img src={opt.image_file} alt="" className="h-8 w-8 rounded" />
                                )}
                                <span className="text-slate-700">
                                  {opt.text_value || `(option ${i + 1})`}
                                </span>
                              </label>
                            ))
                          : q.options.map((opt, i) => (
                              <label
                                key={opt.id}
                                className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm"
                              >
                                <input
                                  type="radio"
                                  name="preview-mcq"
                                  disabled
                                  className="h-4 w-4"
                                />
                                {opt.image_file && (
                                  <img src={opt.image_file} alt="" className="h-8 w-8 rounded" />
                                )}
                                <span className="text-slate-700">
                                  {opt.text_value || `(option ${i + 1})`}
                                </span>
                              </label>
                            ))}
                      </>
                    )}
                    {/* FITB: text inputs */}
                    {q.question_type.startsWith("FITB_") &&
                      q.options.map((opt, i) => (
                        <div key={opt.id} className="flex items-center gap-2 text-sm">
                          <span className="text-slate-600">Field {i + 1}:</span>
                          <input
                            type="text"
                            disabled
                            placeholder="Type answer..."
                            className="flex-1 rounded-md border border-slate-200 px-3 py-1.5 text-sm"
                          />
                        </div>
                      ))}
                    {/* Match: two columns */}
                    {q.question_type === "MATCH_FOLLOWING" && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="mb-1 text-xs font-medium text-slate-500">Group A</p>
                          {q.options
                            .filter((o) => o.option_type === "MATCH_A")
                            .map((opt, i) => (
                              <div
                                key={opt.id}
                                className="mb-1 rounded-md border border-slate-200 px-3 py-1.5 text-sm"
                              >
                                {opt.text_value || `Item ${i + 1}`}
                              </div>
                            ))}
                        </div>
                        <div>
                          <p className="mb-1 text-xs font-medium text-slate-500">
                            Group B (shuffled)
                          </p>
                          {q.options
                            .filter((o) => o.option_type === "MATCH_B")
                            .map((opt, i) => (
                              <div
                                key={opt.id}
                                className="mb-1 rounded-md border border-slate-200 px-3 py-1.5 text-sm"
                              >
                                {opt.text_value || `Match ${i + 1}`}
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                    {/* Grid: table */}
                    {q.question_type === "GRID_LIST_SELECTION" && (
                      <table className="w-full text-sm">
                        <tbody>
                          {[...Array(q.grid_rows || 3)].map((_, r) => (
                            <tr key={r}>
                              <td className="border border-slate-200 p-2 font-medium text-slate-600">
                                Row {r + 1}
                              </td>
                              {[...Array(q.grid_cols || 3)].map((_, c) => (
                                <td key={c} className="border border-slate-200 p-2 text-center">
                                  <input type="checkbox" disabled className="h-4 w-4" />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {/* Hotspot: image with zones */}
                    {q.question_type.startsWith("HOTSPOT_") && q.image && (
                      <div className="relative inline-block">
                        <img
                          src={q.image}
                          alt="Hotspot"
                          className="max-w-md rounded border border-slate-300"
                        />
                        {q.hotspot_areas.map((ha, i) => (
                          <div
                            key={ha.id}
                            className="absolute border-2 border-success-500/50 bg-success-500/10"
                            style={{
                              left: `${ha.x}px`,
                              top: `${ha.y}px`,
                              width: `${ha.width_px}px`,
                              height: `${ha.height_px}px`,
                            }}
                          >
                            <span className="absolute -top-5 left-0 text-xs text-success-600">
                              Zone {i + 1}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    {/* Rank: dropdowns */}
                    {q.question_type === "RANK_SIMPLE" &&
                      q.options.map((opt, i) => (
                        <div key={opt.id} className="flex items-center gap-2 text-sm">
                          <select disabled className="h-8 rounded border border-slate-200 text-xs">
                            <option>Rank {i + 1}</option>
                          </select>
                          <span className="text-slate-700">
                            {opt.text_value || `Item ${i + 1}`}
                          </span>
                        </div>
                      ))}
                    {/* Rating: scale circles */}
                    {q.question_type === "STANDARD_RATING_SCALE" && (
                      <div className="flex items-center gap-3">
                        {[...Array(q.rating_scale_points || 5)].map((_, p) => (
                          <button
                            key={p}
                            type="button"
                            disabled
                            className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-300 text-xs text-slate-500"
                          >
                            {p + 1}
                          </button>
                        ))}
                      </div>
                    )}
                    {/* Forced Choice: radios */}
                    {q.question_type.startsWith("FORCED_CHOICE_") &&
                      q.options.map((opt, i) => (
                        <label key={opt.id} className="flex items-center gap-2 text-sm">
                          <input type="radio" name="preview-fc" disabled className="h-4 w-4" />
                          <span className="text-slate-700">
                            {opt.text_value || `Option ${i + 1}`}
                          </span>
                          <span className="ml-auto text-xs text-slate-400">
                            score: {opt.predefined_score}
                          </span>
                        </label>
                      ))}
                  </div>
                )}

                {/* Empty state when no options */}
                {!hasOptions && !hasMedia && (
                  <p className="py-4 text-center text-sm text-slate-400">
                    No options or media attached. Create options via the question editor.
                  </p>
                )}

                <div className="mt-6 border-t border-slate-100 pt-3 text-xs text-slate-400">
                  Type: {q.question_type_label} · Scoring: {q.scoring_type_label}
                  {q.case_sensitive && " · Case sensitive"}
                  {q.pct_match_threshold !== null && ` · Match: ${q.pct_match_threshold}%`}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ReviewModal
        open={reviewOpen}
        onClose={() => setReviewOpen(false)}
        questionId={qid}
        reviewType={canReviewPsychometric ? "psychometric" : "content"}
        canSetExposure={canReviewPsychometric}
      />

      <QuestionEditorModal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        questionId={qid}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review Modal
// ---------------------------------------------------------------------------

function ReviewModal({
  open,
  onClose,
  questionId,
  reviewType,
  canSetExposure,
}: {
  open: boolean;
  onClose: () => void;
  questionId: number;
  reviewType: string;
  canSetExposure: boolean;
}) {
  const queryClient = useQueryClient();
  const [action, setAction] = useState("approve");
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(4);
  const [exposureLimit, setExposureLimit] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      submitReview(questionId, {
        review_type: reviewType,
        action,
        comment,
        rating: Number(rating),
        ...(canSetExposure && exposureLimit ? { exposure_limit: Number(exposureLimit) } : {}),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["question-bank", "questions", questionId] });
      setComment("");
      setExposureLimit("");
      setError(null);
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Review (${reviewType})`}
      description="Review the question and take action."
      size="md"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label required>Action</Label>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={action === "approve" ? "primary" : "outline"}
              size="sm"
              onClick={() => setAction("approve")}
            >
              Approve
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setAction("send_back")}
            >
              Send Back
            </Button>
            <Button
              type="button"
              variant={action === "reject" ? "danger" : "outline"}
              size="sm"
              onClick={() => setAction("reject")}
            >
              Reject
            </Button>
          </div>
        </div>
        <div>
          <Label htmlFor="comment">Comment / Reason</Label>
          <textarea
            id="comment"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={
              action === "send_back" ? "Reason for sending back..." : "Approval comment..."
            }
          />
        </div>
        <div>
          <Label htmlFor="rating">Content quality rating (1-5)</Label>
          <select
            id="rating"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((r) => (
              <option key={r} value={r}>
                {r} - {["Poor", "Fair", "Good", "Very Good", "Excellent"][r - 1]}
              </option>
            ))}
          </select>
        </div>
        {canSetExposure && (
          <div>
            <Label htmlFor="exposure">Exposure limit (optional)</Label>
            <Input
              id="exposure"
              type="number"
              value={exposureLimit}
              onChange={(e) => setExposureLimit(e.target.value)}
              placeholder="e.g. 100"
            />
            <p className="mt-1 text-xs text-slate-500">
              Max times this question can be used before auto-deactivation.
            </p>
          </div>
        )}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Submit review
          </Button>
        </div>
      </form>
    </Modal>
  );
}
