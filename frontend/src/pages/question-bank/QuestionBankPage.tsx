import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

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
  deleteQuestion,
  listQuestions,
  QUESTION_STATUSES,
  QUESTION_TYPES,
  submitForReview,
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
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [mineOnly, setMineOnly] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null);
  const [categoriesOpen, setCategoriesOpen] = useState(false);
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
      categoryFilter,
    ],
    queryFn: () =>
      listQuestions({
        page,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(typeFilter ? { question_type: typeFilter } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(mineOnly ? { mine: true } : {}),
        ...(categoryFilter ? { category: categoryFilter } : {}),
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
      <Card className="border-l-0 border-t-0 border-r-0">
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
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setCategoriesOpen(true)}>
                Categories
              </Button>
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
                              onClick={() => setDeleteQ({ id: q.id, text: q.question_text_1 })}
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
      </Card>

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
        onClose={() => setDeleteQ(null)}
        onConfirm={() => deleteQ && deleteMutation.mutate(deleteQ.id)}
      />
    </div>
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
