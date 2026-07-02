import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Modal,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import {
  createQuestion,
  deleteQuestion,
  DIFFICULTY_LEVELS,
  listQuestions,
  QUESTION_STATUSES,
  QUESTION_TYPES,
  SCORING_TYPES,
  submitForReview,
} from "@/api/questionBank";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const QB_KEY = ["question-bank", "questions"];

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

export default function QuestionBankPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [mineOnly, setMineOnly] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteQ, setDeleteQ] = useState<{ id: number; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Debounce search
  useState(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: [...QB_KEY, page, debouncedSearch, typeFilter, statusFilter, mineOnly],
    queryFn: () =>
      listQuestions({
        page,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(typeFilter ? { question_type: typeFilter } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(mineOnly ? { mine: true } : {}),
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteQuestion(id),
    onSuccess: () => {
      setDeleteQ(null);
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const submitMutation = useMutation({
    mutationFn: (id: number) => submitForReview(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const questions = data?.results ?? [];
  const count = data?.count ?? 0;
  const hasNext = Boolean(data?.next);
  const hasPrev = Boolean(data?.previous);

  const canCreate =
    user?.role === "sme" || user?.role === "psychometrician" || user?.role === "cj_admin";
  const canDelete = user?.role === "sme" || user?.role === "cj_admin";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Question Bank</CardTitle>
              <CardDescription>
                {count > 0
                  ? `${count} question${count === 1 ? "" : "s"}`
                  : "Manage assessment questions"}
              </CardDescription>
            </div>
            {canCreate && <Button onClick={() => setCreateOpen(true)}>Create question</Button>}
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="error" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Input
              type="search"
              placeholder="Search questions..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="max-w-sm"
              aria-label="Search questions"
            />
            <select
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All types</option>
              {QUESTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <select
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {QUESTION_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={mineOnly}
                onChange={(e) => {
                  setMineOnly(e.target.checked);
                  setPage(1);
                }}
                className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
              />
              My questions
            </label>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : isError ? (
            <Alert variant="error">
              <AlertDescription>Failed to load questions.</AlertDescription>
            </Alert>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Question</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Difficulty</TableHead>
                  <TableHead>Created by</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {questions.length === 0 ? (
                  <TableEmpty colSpan={7}>
                    {debouncedSearch || typeFilter || statusFilter
                      ? "No questions match your filters."
                      : "No questions yet. Create one to get started."}
                  </TableEmpty>
                ) : (
                  questions.map((q) => (
                    <TableRow key={q.id}>
                      <TableCell className="max-w-xs truncate font-medium text-slate-900">
                        <Link
                          to={`/question-bank/${q.id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {q.question_text_1}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="default">{q.question_type_label}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANTS[q.status] ?? "default"}>
                          {q.status_label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">{q.difficulty_level || "—"}</TableCell>
                      <TableCell className="text-slate-500">{q.created_by_name || "—"}</TableCell>
                      <TableCell className="text-slate-500">
                        {new Date(q.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          {q.status === "draft" || q.status === "sent_back" ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              loading={submitMutation.isPending}
                              onClick={() => submitMutation.mutate(q.id)}
                            >
                              Submit
                            </Button>
                          ) : null}
                          {canDelete && (q.status === "draft" || q.status === "sent_back") ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-danger hover:bg-danger-50"
                              onClick={() => setDeleteQ({ id: q.id, text: q.question_text_1 })}
                            >
                              Delete
                            </Button>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}

          {(hasPrev || hasNext) && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-slate-500">Page {page}</p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasPrev}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasNext}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <CreateQuestionModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <DeleteQuestionModal
        question={deleteQ}
        loading={deleteMutation.isPending}
        onClose={() => setDeleteQ(null)}
        onConfirm={() => deleteQ && deleteMutation.mutate(deleteQ.id)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create Question Modal
// ---------------------------------------------------------------------------

function CreateQuestionModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [questionType, setQuestionType] = useState("MCQ_TEXT_IMAGE");
  const [questionText, setQuestionText] = useState("");
  const [scoringType, setScoringType] = useState("BINARY");
  const [difficulty, setDifficulty] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      createQuestion({
        question_type: questionType,
        question_text_1: questionText,
        scoring_type: scoringType,
        difficulty_level: difficulty,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
      setQuestionText("");
      setError(null);
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create question"
      description="Create a new question (draft status)."
      size="lg"
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
          if (!questionText.trim()) {
            setError("Question text is required.");
            return;
          }
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="qtype" required>
              Question type
            </Label>
            <select
              id="qtype"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={questionType}
              onChange={(e) => setQuestionType(e.target.value)}
            >
              {QUESTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="stype">Scoring type</Label>
            <select
              id="stype"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={scoringType}
              onChange={(e) => setScoringType(e.target.value)}
            >
              {SCORING_TYPES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="diff">Difficulty</Label>
            <select
              id="diff"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              <option value="">Select...</option>
              {DIFFICULTY_LEVELS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <Label htmlFor="qtext" required>
            Question text
          </Label>
          <textarea
            id="qtext"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="Enter the question..."
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Create question
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Delete Question Modal
// ---------------------------------------------------------------------------

function DeleteQuestionModal({
  question,
  loading,
  onClose,
  onConfirm,
}: {
  question: { id: number; text: string } | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!question) return null;
  return (
    <Modal
      open={Boolean(question)}
      onClose={onClose}
      title="Delete question"
      description="This action cannot be undone."
      size="sm"
    >
      <p className="text-sm text-slate-600">Are you sure you want to delete this question?</p>
      <p className="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-500">
        "{question.text.substring(0, 100)}
        {question.text.length > 100 ? "..." : ""}"
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" loading={loading} onClick={onConfirm}>
          Delete question
        </Button>
      </div>
    </Modal>
  );
}
