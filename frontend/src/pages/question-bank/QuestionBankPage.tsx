import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Modal,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
  PageCard,
  stripHtml,
  useToast,
} from "@/components/ui";
import {
  approveDeletionRequest,
  batchSetExposureLimit,
  batchSetQuestionStatus,
  bulkImportQuestions,
  declineDeletionRequest,
  deleteQuestion,
  listDeletionRequests,
  listQuestions,
  QUESTION_STATUSES,
  QUESTION_TYPES,
  submitForReview,
  type BulkImportResult,
} from "@/api/questionBank";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { CategoryManagerModal } from "./CategoryManager";

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
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [mineOnly, setMineOnly] = useState(false);
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null);
  const [categoriesOpen, setCategoriesOpen] = useState(false);
  const [bulkImportOpen, setBulkImportOpen] = useState(false);
  const [deleteQ, setDeleteQ] = useState<{ id: number; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const { data, isLoading, isError } = useQuery({
    queryKey: [
      ...QB_KEY,
      page,
      debouncedSearch,
      typeFilter,
      statusFilter,
      mineOnly,
      assignedToMe,
      categoryFilter,
    ],
    queryFn: () =>
      listQuestions({
        page,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(typeFilter ? { question_type: typeFilter } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(mineOnly ? { mine: true } : {}),
        ...(assignedToMe ? { assignedToMe: true } : {}),
        ...(categoryFilter ? { category: categoryFilter } : {}),
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (v: { id: number; reason: string }) => deleteQuestion(v.id, v.reason),
    onSuccess: () => {
      setDeleteQ(null);
      // QB-1: a non-admin's delete creates a request for admin approval; an
      // admin deletes directly.
      toast.success(
        user?.role === "cj_admin"
          ? "Question deleted."
          : "Deletion request submitted — an admin will review it.",
      );
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
      void queryClient.invalidateQueries({ queryKey: ["qb-deletion-requests"] });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const submitMutation = useMutation({
    mutationFn: (id: number) => submitForReview(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QB_KEY }),
    onError: (err) => setError(extractApiError(err)),
  });

  const questions = data?.results ?? [];
  const count = data?.count ?? 0;
  const hasNext = Boolean(data?.next);
  const hasPrev = Boolean(data?.previous);

  const canCreate = ["sme", "psychometrician", "cj_admin"].includes(user?.role ?? "");
  const canDelete = ["sme", "cj_admin"].includes(user?.role ?? "");
  const isAdmin = user?.role === "cj_admin";
  const canManageCategories = ["psychometrician", "cj_admin"].includes(user?.role ?? "");

  // Review permissions — Reviewer reviews content, Psychometrician reviews psychometric,
  // cj_admin can review both. Used to show the Review button on the list and to power
  // the "Pending My Review" quick filter.
  const canReviewContent = ["reviewer", "cj_admin"].includes(user?.role ?? "");
  const canReviewPsychometric = ["psychometrician", "cj_admin"].includes(user?.role ?? "");

  // QB-2 (D1 §4.2/§4.3): periodic QB updation — batch activate/inactivate and
  // exposure-limit management (psychometrician / admin).
  const canManageQB = ["psychometrician", "cj_admin"].includes(user?.role ?? "");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const clearSelection = () => setSelected(new Set());
  const toggleSelect = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const batchStatusMutation = useMutation({
    mutationFn: (isActive: boolean) =>
      batchSetQuestionStatus({ question_ids: [...selected], is_active: isActive }),
    onSuccess: (res) => {
      toast.success(`${res.updated_count} question(s) updated.`);
      clearSelection();
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
  const batchExposureMutation = useMutation({
    mutationFn: (limit: number | null) =>
      batchSetExposureLimit({ question_ids: [...selected], exposure_limit: limit }),
    onSuccess: (res) => {
      toast.success(`Exposure limit set on ${res.updated_count} question(s).`);
      clearSelection();
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // QB-1 (D1 §4.3): admin queue of pending deletion requests.
  const deletionRequestsQuery = useQuery({
    queryKey: ["qb-deletion-requests"],
    queryFn: listDeletionRequests,
    enabled: isAdmin,
  });
  const pendingDeletionRequests = (deletionRequestsQuery.data ?? []).filter(
    (r) => r.status === "pending",
  );
  const reviewDeletionMutation = useMutation({
    mutationFn: (v: { id: number; approve: boolean }) =>
      v.approve ? approveDeletionRequest(v.id) : declineDeletionRequest(v.id),
    onSuccess: () => {
      toast.success("Deletion request reviewed.");
      void queryClient.invalidateQueries({ queryKey: ["qb-deletion-requests"] });
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
  const canReviewAny = canReviewContent || canReviewPsychometric;

  // The statuses the current user can review — used by the "Pending My Review" shortcut.
  const reviewStatuses: string[] = [];
  if (canReviewContent) reviewStatuses.push("pending_content_review");
  if (canReviewPsychometric) reviewStatuses.push("pending_psychometric_review");

  /** Does this question's status match a review stage the current user can act on? */
  const canReviewQuestion = (qStatus: string) => reviewStatuses.includes(qStatus);

  // Can the current user edit a specific question?
  // - cj_admin: can edit ANY question regardless of status
  // - sme / custom roles with change permission: can edit only draft or sent_back
  const canEditQuestion = (status: string) =>
    isAdmin || (canCreate && (status === "draft" || status === "sent_back"));

  const openCreateEditor = () => {
    navigate("/question-bank/new");
  };

  const openEditEditor = (id: number) => {
    navigate(`/question-bank/${id}/edit`);
  };

  return (
    <div className="space-y-6">
      <PageCard>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>
                {user?.role === "reviewer" ? "My Review Questions" : "Question Bank"}
              </CardTitle>
              <CardDescription>
                {count > 0
                  ? `${count} question${count === 1 ? "" : "s"}`
                  : "Manage assessment questions"}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {canManageQB && (
                <Button variant="outline" onClick={() => navigate("/question-bank/psychometrics")}>
                  Psychometric Analysis
                </Button>
              )}
              <Button variant="outline" onClick={() => setCategoriesOpen(true)}>
                Categories
              </Button>
              {canCreate && (
                <Button variant="outline" onClick={() => setBulkImportOpen(true)}>
                  Bulk import
                </Button>
              )}
              {canCreate && <Button onClick={openCreateEditor}>Create question</Button>}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="error" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Quick filter for reviewers / psychometricians — surfaces questions
              pending their review so they don't have to dig through the status
              dropdown. Hidden for SMEs and roles with no review permission. */}
          {canReviewAny && (
            <div className="mb-4 flex flex-wrap items-center gap-2 rounded-md border border-amber-200 bg-amber-50 p-3">
              <span className="text-sm font-medium text-amber-900">Quick filters:</span>
              {canReviewContent && (
                <Button
                  variant={statusFilter === "pending_content_review" ? "primary" : "outline"}
                  size="sm"
                  onClick={() => {
                    setStatusFilter(
                      statusFilter === "pending_content_review" ? "" : "pending_content_review",
                    );
                    setPage(1);
                  }}
                >
                  Pending Content Review
                </Button>
              )}
              {canReviewPsychometric && (
                <Button
                  variant={statusFilter === "pending_psychometric_review" ? "primary" : "outline"}
                  size="sm"
                  onClick={() => {
                    setStatusFilter(
                      statusFilter === "pending_psychometric_review"
                        ? ""
                        : "pending_psychometric_review",
                    );
                    setPage(1);
                  }}
                >
                  Pending Psychometric Review
                </Button>
              )}
              <span className="ml-auto text-xs text-amber-700">
                Click a status to filter; click again to clear.
              </span>
            </div>
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
            {canReviewContent && (
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={assignedToMe}
                  onChange={(e) => {
                    setAssignedToMe(e.target.checked);
                    setPage(1);
                  }}
                  className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
                />
                Assigned to me
              </label>
            )}
            {categoryFilter && (
              <Badge variant="primary" className="gap-1">
                Filtered by category
                <button
                  type="button"
                  onClick={() => setCategoryFilter(null)}
                  className="ml-1 rounded-full px-1 hover:bg-primary-100"
                  aria-label="Clear category filter"
                >
                  ×
                </button>
              </Badge>
            )}
          </div>

          {/* QB-1: admin deletion-request queue (D1 §4.3) */}
          {isAdmin && pendingDeletionRequests.length > 0 && (
            <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-800">
                Pending deletion requests ({pendingDeletionRequests.length})
              </p>
              <ul className="space-y-2">
                {pendingDeletionRequests.map((r) => (
                  <li
                    key={r.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded border border-amber-200 bg-white p-2 text-sm"
                  >
                    <div className="min-w-0">
                      <span className="font-medium text-slate-800">
                        {r.target_type === "category" ? "Category" : "Question"}: {r.target_label}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {r.requester_name ?? "A user"} — {r.reason}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="danger"
                        loading={reviewDeletionMutation.isPending}
                        onClick={() => reviewDeletionMutation.mutate({ id: r.id, approve: true })}
                      >
                        Approve delete
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => reviewDeletionMutation.mutate({ id: r.id, approve: false })}
                      >
                        Decline
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* QB-2: batch action bar (D1 §4.2/§4.3) */}
          {canManageQB && selected.size > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-primary-200 bg-primary-50 px-3 py-2 text-sm">
              <span className="font-medium text-primary-800">{selected.size} selected</span>
              <Button
                size="sm"
                variant="outline"
                loading={batchStatusMutation.isPending}
                onClick={() => batchStatusMutation.mutate(true)}
              >
                Activate
              </Button>
              <Button
                size="sm"
                variant="outline"
                loading={batchStatusMutation.isPending}
                onClick={() => batchStatusMutation.mutate(false)}
              >
                Inactivate
              </Button>
              <Button
                size="sm"
                variant="outline"
                loading={batchExposureMutation.isPending}
                onClick={() => {
                  const raw = window.prompt(
                    "Exposure limit for the selected questions (blank = no limit):",
                  );
                  if (raw === null) return;
                  const val = raw.trim() === "" ? null : Number(raw);
                  if (val !== null && (Number.isNaN(val) || val < 0)) {
                    toast.error("Enter a non-negative number, or leave blank for no limit.");
                    return;
                  }
                  batchExposureMutation.mutate(val);
                }}
              >
                Set exposure limit
              </Button>
              <button
                className="ml-auto text-xs text-slate-500 hover:underline"
                onClick={clearSelection}
              >
                Clear
              </button>
            </div>
          )}

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
                  {canManageQB && <TableHead className="w-10" />}
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
                  <TableEmpty colSpan={canManageQB ? 8 : 7}>
                    {debouncedSearch || typeFilter || statusFilter
                      ? "No questions match your filters."
                      : "No questions yet. Create one to get started."}
                  </TableEmpty>
                ) : (
                  questions.map((q) => (
                    <TableRow key={q.id}>
                      {canManageQB && (
                        <TableCell>
                          <input
                            type="checkbox"
                            aria-label="Select question"
                            checked={selected.has(q.id)}
                            onChange={() => toggleSelect(q.id)}
                          />
                        </TableCell>
                      )}
                      <TableCell className="max-w-xs truncate font-medium text-slate-900">
                        <Link
                          to={`/question-bank/${q.id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {q.question_title || stripHtml(q.question_text_1) || "(untitled)"}
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
                          {canReviewQuestion(q.status) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-primary-600 hover:bg-primary-50"
                              onClick={() => navigate(`/question-bank/${q.id}?review=1`)}
                            >
                              Review
                            </Button>
                          )}
                          {canEditQuestion(q.status) && (
                            <Button variant="ghost" size="sm" onClick={() => openEditEditor(q.id)}>
                              Edit
                            </Button>
                          )}
                          {(q.status === "draft" || q.status === "sent_back") && canCreate && (
                            <Button
                              variant="ghost"
                              size="sm"
                              loading={submitMutation.isPending}
                              onClick={() => submitMutation.mutate(q.id)}
                            >
                              Submit
                            </Button>
                          )}
                          {canEditQuestion(q.status) && canDelete && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-danger hover:bg-danger-50"
                              onClick={() =>
                                setDeleteQ({
                                  id: q.id,
                                  text:
                                    q.question_title ||
                                    stripHtml(q.question_text_1) ||
                                    "(untitled)",
                                })
                              }
                            >
                              Delete
                            </Button>
                          )}
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
      </PageCard>

      <CategoryManagerModal
        open={categoriesOpen}
        onClose={() => setCategoriesOpen(false)}
        canManage={canManageCategories}
        selectedCategoryId={categoryFilter}
        onSelectCategory={(id) => {
          setCategoryFilter(id);
          setPage(1);
        }}
      />
      <DeleteQuestionModal
        question={deleteQ}
        loading={deleteMutation.isPending}
        isAdmin={isAdmin}
        onClose={() => setDeleteQ(null)}
        onConfirm={(reason) => deleteQ && deleteMutation.mutate({ id: deleteQ.id, reason })}
      />
      {bulkImportOpen && (
        <BulkImportModal
          onClose={() => setBulkImportOpen(false)}
          onImported={() => void queryClient.invalidateQueries({ queryKey: QB_KEY })}
        />
      )}
    </div>
  );
}

function BulkImportModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const toast = useToast();
  const [text, setText] = useState("");
  const [result, setResult] = useState<BulkImportResult | null>(null);

  const importMutation = useMutation({
    mutationFn: (questions: Record<string, unknown>[]) => bulkImportQuestions(questions),
    onSuccess: (res) => {
      setResult(res);
      if (res.created_count > 0) {
        toast.success(`Imported ${res.created_count} question(s).`);
        onImported();
      }
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result ?? ""));
    reader.readAsText(file);
  };

  const submit = () => {
    setResult(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      toast.error('Invalid JSON. Paste an array of questions or { "questions": [...] }.');
      return;
    }
    const questions = Array.isArray(parsed)
      ? parsed
      : (parsed as { questions?: unknown }).questions;
    if (!Array.isArray(questions) || questions.length === 0) {
      toast.error("Provide a non-empty array of question objects.");
      return;
    }
    importMutation.mutate(questions as Record<string, unknown>[]);
  };

  return (
    <Modal open onClose={onClose} title="Bulk import questions" size="lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Paste a JSON array of full questions (or a{" "}
          <code className="rounded bg-slate-100 px-1">{`{ "questions": [...] }`}</code> object), or
          upload a <code className="rounded bg-slate-100 px-1">.json</code> file. Each item uses the
          same fields as a single question (e.g. <code>question_type</code>,{" "}
          <code>question_title</code>, <code>question_text_1</code>, <code>scoring_type</code>).
        </p>
        <div>
          <input
            type="file"
            accept="application/json,.json"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
            className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-700 hover:file:bg-primary-100"
          />
        </div>
        <textarea
          rows={10}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 font-mono text-xs"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder='[{"question_type": "MCQ_TEXT_IMAGE", "question_title": "Q1", "question_text_1": "First?", "scoring_type": "BINARY"}]'
        />
        {result && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-medium text-slate-900">
              Imported {result.created_count}; {result.error_count} error(s).
            </p>
            {result.errors.length > 0 && (
              <ul className="mt-2 max-h-32 space-y-1 overflow-auto text-xs text-danger-600">
                {result.errors.map((e) => (
                  <li key={e.index}>
                    Row {e.index + 1}: {JSON.stringify(e.errors)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button loading={importMutation.isPending} disabled={!text.trim()} onClick={submit}>
            Import
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Delete Question Modal
// ---------------------------------------------------------------------------

function DeleteQuestionModal({
  question,
  loading,
  isAdmin,
  onClose,
  onConfirm,
}: {
  question: { id: number; text: string } | null;
  loading: boolean;
  isAdmin: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  useEffect(() => {
    setReason("");
  }, [question?.id]);
  if (!question) return null;
  return (
    <Modal
      open={Boolean(question)}
      onClose={onClose}
      title={isAdmin ? "Delete question" : "Request question deletion"}
      description={
        isAdmin
          ? "This action cannot be undone."
          : "A CJ Admin will review your request before the question is removed (D1 §4.3)."
      }
      size="sm"
    >
      <p className="text-sm text-slate-600">
        {isAdmin
          ? "Are you sure you want to delete this question?"
          : "Request deletion of this question?"}
      </p>
      <p className="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-500">
        "{question.text.substring(0, 100)}
        {question.text.length > 100 ? "..." : ""}"
      </p>
      <div className="mt-4">
        <label htmlFor="del-reason" className="mb-1 block text-sm font-medium text-slate-700">
          Reason{isAdmin ? " (optional)" : " (required)"}
        </label>
        <textarea
          id="del-reason"
          rows={2}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why should this question be removed?"
        />
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button
          type="button"
          variant="danger"
          loading={loading}
          disabled={!isAdmin && !reason.trim()}
          onClick={() => onConfirm(reason)}
        >
          {isAdmin ? "Delete question" : "Submit request"}
        </Button>
      </div>
    </Modal>
  );
}
