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

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  const display = value === null || value === undefined || value === "" ? "—" : value;
  return (
    <div className="flex flex-col gap-0.5 py-1">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-900">{display}</dd>
    </div>
  );
}

function BoolField({ label, value }: { label: string; value: boolean }) {
  return <FieldRow label={label} value={value ? "Yes" : "No"} />;
}

export default function QuestionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qid = Number(id);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [reviewOpen, setReviewOpen] = useState(false);
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

  const canSubmit =
    (question.status === "draft" || question.status === "sent_back") &&
    (user?.role === "sme" || user?.role === "cj_admin");
  const canReviewContent =
    question.status === "pending_content_review" &&
    (user?.role === "reviewer" || user?.role === "cj_admin");
  const canReviewPsychometric =
    question.status === "pending_psychometric_review" &&
    (user?.role === "psychometrician" || user?.role === "cj_admin");

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Header */}
      <div>
        <Link to="/question-bank" className="text-sm text-primary-600 hover:underline">
          ← Back to Question Bank
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">{question.question_type_label}</h1>
          <Badge variant={STATUS_VARIANTS[question.status] ?? "default"}>
            {question.status_label}
          </Badge>
          {question.difficulty_level && (
            <Badge variant="outline">Difficulty: {question.difficulty_level}</Badge>
          )}
          {question.cognitive_level && (
            <Badge variant="outline">Cognitive: {question.cognitive_level}</Badge>
          )}
          {question.scoring_type_label && (
            <Badge variant="primary">{question.scoring_type_label}</Badge>
          )}
        </div>
      </div>

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">All Details</TabsTrigger>
          <TabsTrigger value="options">Options ({question.options.length})</TabsTrigger>
          <TabsTrigger value="media">Media</TabsTrigger>
          <TabsTrigger value="reviews">Reviews ({question.reviews.length})</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>

        {/* === ALL DETAILS TAB === */}
        <TabsContent value="details">
          <Card>
            <CardHeader>
              <CardTitle>Question Properties</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2">
                {/* Core */}
                <FieldRow label="Question ID Label" value={question.question_id_label} />
                <FieldRow label="Question Type" value={question.question_type_label} />
                <FieldRow label="Status" value={question.status_label} />
                <FieldRow label="Scoring Type" value={question.scoring_type_label} />

                {/* Text content */}
                <div className="py-1 sm:col-span-2">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Question Text (Primary)
                  </dt>
                  <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                    {question.question_text_1}
                  </dd>
                </div>
                {question.question_text_2 && (
                  <div className="py-1 sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Additional Text
                    </dt>
                    <dd className="mt-1 text-sm text-slate-900">{question.question_text_2}</dd>
                  </div>
                )}

                {/* Category */}
                <FieldRow label="Category" value={question.category_name} />

                {/* Scoring config */}
                <BoolField label="Case Sensitive" value={question.case_sensitive} />
                {question.pct_match_threshold !== null && (
                  <FieldRow label="Match Threshold (%)" value={question.pct_match_threshold} />
                )}

                {/* Type-specific config */}
                {question.display_duration_seconds !== null && (
                  <FieldRow
                    label="Display Duration (sec)"
                    value={question.display_duration_seconds}
                  />
                )}
                {question.flash_interval_ms !== null && (
                  <FieldRow label="Flash Interval (ms)" value={question.flash_interval_ms} />
                )}
                {question.flash_display_count !== null && (
                  <FieldRow label="Flash Display Count" value={question.flash_display_count} />
                )}
                {question.grid_rows !== null && (
                  <FieldRow label="Grid Rows" value={question.grid_rows} />
                )}
                {question.grid_cols !== null && (
                  <FieldRow label="Grid Columns" value={question.grid_cols} />
                )}
                {question.rating_scale_points !== null && (
                  <FieldRow label="Rating Scale Points" value={question.rating_scale_points} />
                )}
                {question.rating_direction && (
                  <FieldRow label="Rating Direction" value={question.rating_direction} />
                )}

                {/* Passage */}
                {question.passage_title && (
                  <FieldRow label="Passage Title" value={question.passage_title} />
                )}
                {question.passage_body && (
                  <div className="py-1 sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Passage Body
                    </dt>
                    <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                      {question.passage_body}
                    </dd>
                  </div>
                )}

                {/* Psychometric */}
                <FieldRow label="Difficulty Level" value={question.difficulty_level} />
                <FieldRow label="Cognitive Level" value={question.cognitive_level} />
                {question.discrimination_index !== null && (
                  <FieldRow label="Discrimination Index" value={question.discrimination_index} />
                )}

                {/* Exposure */}
                {question.exposure_limit !== null && (
                  <FieldRow label="Exposure Limit" value={question.exposure_limit} />
                )}
                <FieldRow label="Exposure Count" value={question.exposure_count} />

                {/* Audit */}
                <FieldRow label="Created By" value={question.created_by_name} />
                <FieldRow
                  label="Created At"
                  value={new Date(question.created_at).toLocaleString()}
                />
                <FieldRow
                  label="Updated At"
                  value={new Date(question.updated_at).toLocaleString()}
                />
                <BoolField label="Is Active" value={question.is_active} />
              </dl>

              {/* Actions */}
              <div className="mt-6 flex gap-2 border-t border-slate-100 pt-4">
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
              {question.options.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">
                  No response options defined. Options can be added when editing the question.
                </p>
              ) : (
                <div className="space-y-3">
                  {question.options.map((opt) => (
                    <div key={opt.id} className="rounded-md border border-slate-200 p-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{opt.option_type}</Badge>
                        {opt.is_correct && <Badge variant="success">✓ Correct</Badge>}
                        {opt.label && <span className="text-xs text-slate-500">{opt.label}</span>}
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
                        <p className="mt-1 text-xs text-slate-500">
                          Predefined score: {opt.predefined_score}
                        </p>
                      )}
                      {opt.correct_answers.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-slate-500">Correct Answers:</p>
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
              {question.image && (
                <div className="mb-4">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Question Image
                  </p>
                  <img
                    src={question.image}
                    alt="Question"
                    className="max-h-60 rounded border border-slate-200"
                  />
                </div>
              )}
              {question.media_files.length > 0 ? (
                <div className="space-y-3">
                  {question.media_files.map((mf) => (
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
                </div>
              ) : (
                <p className="py-4 text-center text-sm text-slate-500">No media files attached.</p>
              )}
              {question.flash_items.length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Flash Items ({question.flash_items.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {question.flash_items.map((fi) => (
                      <div key={fi.id} className="rounded-md border border-slate-200 p-2">
                        {fi.item_type === "TEXT" ? (
                          <span className="text-sm text-slate-700">{fi.text_value}</span>
                        ) : (
                          <img
                            src={fi.image_file || ""}
                            alt="Flash"
                            className="h-12 w-12 rounded"
                          />
                        )}
                        {!fi.is_in_display_pool && (
                          <span className="ml-1 text-xs text-slate-400">(excluded)</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {question.hotspot_areas.length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Hotspot Areas ({question.hotspot_areas.length})
                  </p>
                  <div className="space-y-1">
                    {question.hotspot_areas.map((ha) => (
                      <div key={ha.id} className="text-xs text-slate-600">
                        Sub-Q {ha.sub_question_index}: ({ha.x}, {ha.y}) {ha.width_px}×{ha.height_px}
                        px
                        {ha.area_size_code && ` [${ha.area_size_code}]`}
                      </div>
                    ))}
                  </div>
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
              {question.reviews.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">No reviews yet.</p>
              ) : (
                <div className="space-y-4">
                  {question.reviews.map((review) => (
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
                {/* Question ID */}
                {question.question_id_label && (
                  <p className="mb-2 text-xs font-medium text-slate-400">
                    {question.question_id_label}
                  </p>
                )}

                {/* Passage (type 1g) */}
                {question.passage_title && (
                  <div className="mb-4 rounded-md bg-slate-50 p-4">
                    <p className="font-semibold text-slate-900">{question.passage_title}</p>
                    {question.passage_body && (
                      <p className="mt-2 text-sm text-slate-700">{question.passage_body}</p>
                    )}
                  </div>
                )}

                {/* Question image */}
                {question.image && (
                  <img
                    src={question.image}
                    alt="Question"
                    className="mb-4 max-h-60 rounded border border-slate-200"
                  />
                )}

                {/* Audio/Video */}
                {question.media_files.map((mf) => (
                  <div key={mf.id} className="mb-4">
                    {mf.media_type === "AUDIO" && (
                      <audio controls src={mf.file} className="w-full" />
                    )}
                    {mf.media_type === "VIDEO" && (
                      <video controls src={mf.file} className="max-h-60 w-full rounded" />
                    )}
                  </div>
                ))}

                {/* Flash items */}
                {question.flash_items.length > 0 && (
                  <div className="mb-4">
                    <p className="mb-2 text-xs text-slate-500">
                      Flash items (displayed at {question.flash_interval_ms}ms intervals,{" "}
                      {question.flash_display_count} shown):
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {question.flash_items
                        .filter((fi) => fi.is_in_display_pool)
                        .map((fi) => (
                          <div
                            key={fi.id}
                            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm"
                          >
                            {fi.item_type === "TEXT" ? (
                              fi.text_value
                            ) : (
                              <img src={fi.image_file || ""} alt="" className="h-8 w-8" />
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Question text */}
                <p className="mb-4 text-base font-medium text-slate-900">
                  {question.question_text_1}
                </p>
                {question.question_text_2 && (
                  <p className="mb-4 text-sm text-slate-600">{question.question_text_2}</p>
                )}

                {/* Response options — rendered by type */}
                {question.options.length > 0 && (
                  <div className="space-y-2">
                    {question.question_type.startsWith("MCQ_") && (
                      <>
                        {/* Check if multiple correct answers exist */}
                        {question.options.filter((o) => o.is_correct).length > 1
                          ? // Multiple answer: checkboxes
                            question.options.map((opt, i) => (
                              <label
                                key={opt.id}
                                className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm"
                              >
                                <input
                                  type="checkbox"
                                  disabled
                                  className="h-4 w-4 border-slate-300 text-primary-600"
                                />
                                {opt.image_file && (
                                  <img src={opt.image_file} alt="" className="h-8 w-8 rounded" />
                                )}
                                <span className="text-slate-700">
                                  {opt.text_value || `(option ${i + 1})`}
                                </span>
                              </label>
                            ))
                          : // Single answer: radio
                            question.options.map((opt, i) => (
                              <label
                                key={opt.id}
                                className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm"
                              >
                                <input
                                  type="radio"
                                  name="preview-mcq"
                                  disabled
                                  className="h-4 w-4 border-slate-300 text-primary-600"
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

                    {question.question_type.startsWith("FITB_") && (
                      <div className="space-y-2">
                        {question.options.map((opt, i) => (
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
                      </div>
                    )}

                    {question.question_type === "MATCH_FOLLOWING" && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="mb-1 text-xs font-medium text-slate-500">Group A</p>
                          {question.options
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
                          {question.options
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

                    {question.question_type === "GRID_LIST_SELECTION" && (
                      <table className="w-full text-sm">
                        <tbody>
                          {[...Array(question.grid_rows || 3)].map((_, r) => (
                            <tr key={r}>
                              <td className="border border-slate-200 p-2 font-medium text-slate-600">
                                Row {r + 1}
                              </td>
                              {[...Array(question.grid_cols || 3)].map((_, c) => (
                                <td key={c} className="border border-slate-200 p-2 text-center">
                                  <input type="checkbox" readOnly className="h-4 w-4" />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}

                    {question.question_type.startsWith("HOTSPOT_") && question.image && (
                      <div className="relative inline-block">
                        <img
                          src={question.image}
                          alt="Hotspot"
                          className="max-w-md rounded border border-slate-300"
                        />
                        {question.hotspot_areas.map((ha, i) => (
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

                    {question.question_type === "RANK_SIMPLE" && (
                      <div className="space-y-1">
                        {question.options.map((opt, i) => (
                          <div key={opt.id} className="flex items-center gap-2 text-sm">
                            <select
                              disabled
                              className="h-8 rounded border border-slate-200 text-xs"
                            >
                              <option>Rank {i + 1}</option>
                            </select>
                            <span className="text-slate-700">
                              {opt.text_value || `Item ${i + 1}`}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {question.question_type === "STANDARD_RATING_SCALE" && (
                      <div className="flex items-center gap-3">
                        <div className="flex gap-2">
                          {[...Array(question.rating_scale_points || 5)].map((_, p) => (
                            <button
                              key={p}
                              type="button"
                              className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-300 text-xs text-slate-500"
                            >
                              {p + 1}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {question.question_type.startsWith("FORCED_CHOICE_") && (
                      <div className="space-y-1">
                        {question.options.map((opt, i) => (
                          <label key={opt.id} className="flex items-center gap-2 text-sm">
                            <input type="radio" name="preview-fc" readOnly className="h-4 w-4" />
                            <span className="text-slate-700">
                              {opt.text_value || `Option ${i + 1}`}
                            </span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Footer info */}
                <div className="mt-6 border-t border-slate-100 pt-3 text-xs text-slate-400">
                  Type: {question.question_type_label} · Scoring: {question.scoring_type_label}
                  {question.case_sensitive && " · Case sensitive"}
                  {question.pct_match_threshold !== null &&
                    ` · Match threshold: ${question.pct_match_threshold}%`}
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
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review Modal (unchanged)
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
              variant={action === "send_back" ? "outline" : "outline"}
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
