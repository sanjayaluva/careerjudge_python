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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["question-bank", "questions", qid] });
    },
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
            <Badge variant="outline">{question.difficulty_level}</Badge>
          )}
        </div>
      </div>

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Question Details</TabsTrigger>
          <TabsTrigger value="options">Options ({question.options.length})</TabsTrigger>
          <TabsTrigger value="reviews">Reviews ({question.reviews.length})</TabsTrigger>
        </TabsList>

        {/* Question Details Tab */}
        <TabsContent value="details">
          <Card>
            <CardHeader>
              <CardTitle>Question</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Question text
                  </dt>
                  <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                    {question.question_text_1}
                  </dd>
                </div>
                {question.question_text_2 && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Additional text
                    </dt>
                    <dd className="mt-1 text-sm text-slate-900">{question.question_text_2}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Scoring type
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{question.scoring_type_label}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Cognitive level
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{question.cognitive_level || "—"}</dd>
                </div>
                {question.passage_title && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Passage title
                    </dt>
                    <dd className="mt-1 text-sm text-slate-900">{question.passage_title}</dd>
                  </div>
                )}
                {question.passage_body && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Passage body
                    </dt>
                    <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                      {question.passage_body}
                    </dd>
                  </div>
                )}
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created by
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{question.created_by_name || "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created at
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">
                    {new Date(question.created_at).toLocaleString()}
                  </dd>
                </div>
                {question.exposure_limit !== null && (
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Exposure limit
                    </dt>
                    <dd className="mt-1 text-sm text-slate-900">{question.exposure_limit}</dd>
                  </div>
                )}
              </dl>

              <div className="mt-6 flex gap-2 border-t border-slate-100 pt-4">
                {canSubmit && (
                  <Button
                    loading={submitMutation.isPending}
                    onClick={() => submitMutation.mutate()}
                  >
                    Submit for review
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

        {/* Options Tab */}
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
                    <div
                      key={opt.id}
                      className="flex items-start gap-3 rounded-md border border-slate-200 p-3"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{opt.option_type}</Badge>
                          {opt.is_correct && <Badge variant="success">Correct</Badge>}
                          {opt.label && <span className="text-xs text-slate-500">{opt.label}</span>}
                        </div>
                        <p className="mt-1 text-sm text-slate-900">
                          {opt.text_value || "(image option)"}
                        </p>
                        {opt.correct_answers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-slate-500">Correct answers:</p>
                            <ul className="ml-4 list-disc text-xs text-slate-600">
                              {opt.correct_answers.map((ca) => (
                                <li key={ca.id}>{ca.answer_text}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reviews Tab */}
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
