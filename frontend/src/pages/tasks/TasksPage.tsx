/**
 * Tasks page — Admin assigns + monitors tasks; assignee works on assigned tasks.
 * SRS 09 §3 — Task Management.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Modal,
  PageCard,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "@/components/ui";
import { tasksApi, type Task, type TaskCreateInput, type AssigneeRole } from "@/api/tasks";
import { listCategories, QUESTION_TYPES } from "@/api/questionBank";
import { listAllUsers } from "@/api/users";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { nameWithExpertise } from "@/lib/profileFields";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700 ring-slate-500/20",
  in_progress: "bg-info-50 text-info-700 ring-info-600/20",
  awaiting_review: "bg-warning-50 text-warning-800 ring-warning-600/25",
  completed: "bg-success-50 text-success-700 ring-success-600/20",
  cancelled: "bg-danger-50 text-danger-700 ring-danger-600/20",
  overdue: "bg-danger-50 text-danger-700 ring-danger-600/20",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  awaiting_review: "Awaiting Review",
  completed: "Completed",
  cancelled: "Cancelled",
  overdue: "Overdue",
};

const PRIORITY_BADGE: Record<string, string> = {
  low: "bg-slate-100 text-slate-700 ring-slate-500/20",
  medium: "bg-info-50 text-info-700 ring-info-600/20",
  high: "bg-warning-50 text-warning-800 ring-warning-600/25",
  urgent: "bg-danger-50 text-danger-700 ring-danger-600/20",
};

const ROLE_LABEL: Record<AssigneeRole, string> = {
  sme: "SME",
  reviewer: "Reviewer",
  psychometrician: "Psychometrician",
  trainer: "Trainer",
  counsellor: "Counsellor",
};

export default function TasksPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "cj_admin";
  const qc = useQueryClient();
  const toast = useToast();

  const [assignOpen, setAssignOpen] = useState(false);

  const myTasksQuery = useQuery({
    queryKey: ["tasks", "my"],
    queryFn: () => tasksApi.myTasks(),
  });

  const assignedQuery = useQuery({
    queryKey: ["tasks", "assigned"],
    queryFn: () => tasksApi.assigned(),
    enabled: isAdmin,
  });

  const allTasksQuery = useQuery({
    queryKey: ["tasks", "all"],
    queryFn: () => tasksApi.list(),
    enabled: isAdmin,
  });

  const myTasks = myTasksQuery.data?.results ?? [];
  const assignedTasks = assignedQuery.data?.results ?? [];
  const allTasks = allTasksQuery.data?.results ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex flex-col gap-4 p-6 pb-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">Task Management</h1>
            <p className="mt-1 text-sm text-slate-500">
              {isAdmin
                ? "Assign and monitor tasks for SME / Reviewer / Psychometrician / Trainer / Counsellor"
                : "Tasks assigned to you by the admin"}
            </p>
          </div>
          {isAdmin && (
            <div className="flex shrink-0 flex-wrap gap-2">
              <Button onClick={() => setAssignOpen(true)}>+ Assign Task</Button>
            </div>
          )}
        </div>

        <Tabs defaultValue={isAdmin ? "assigned" : "mine"}>
          <div className="overflow-x-auto px-6">
            <TabsList>
              {isAdmin && (
                <>
                  <TabsTrigger value="assigned">
                    Assigned by Me ({assignedTasks.length})
                  </TabsTrigger>
                  <TabsTrigger value="all">All Tasks ({allTasks.length})</TabsTrigger>
                </>
              )}
              <TabsTrigger value="mine">My Tasks ({myTasks.length})</TabsTrigger>
            </TabsList>
          </div>

          {isAdmin && (
            <TabsContent value="assigned" className="px-6 py-4">
              <TasksTable
                tasks={assignedTasks}
                isLoading={assignedQuery.isLoading}
                emptyMessage="No tasks assigned yet. Click '+ Assign Task' to create one."
              />
            </TabsContent>
          )}

          {isAdmin && (
            <TabsContent value="all" className="px-6 py-4">
              <TasksTable
                tasks={allTasks}
                isLoading={allTasksQuery.isLoading}
                emptyMessage="No tasks in the system yet."
              />
            </TabsContent>
          )}

          <TabsContent value="mine" className="px-6 py-4">
            <TasksTable
              tasks={myTasks}
              isLoading={myTasksQuery.isLoading}
              emptyMessage="You have no tasks assigned to you."
            />
          </TabsContent>
        </Tabs>
      </PageCard>

      {assignOpen && (
        <AssignTaskModal
          open={assignOpen}
          onClose={() => setAssignOpen(false)}
          onCreated={() => {
            setAssignOpen(false);
            qc.invalidateQueries({ queryKey: ["tasks"] });
            toast.success("Task assigned. Notification sent to assignee.");
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tasks Table
// ---------------------------------------------------------------------------

function TasksTable({
  tasks,
  isLoading,
  emptyMessage,
}: {
  tasks: Task[];
  isLoading: boolean;
  emptyMessage: string;
}) {
  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }
  if (tasks.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center text-sm text-slate-500">
        {emptyMessage}
      </p>
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Task ID</TableHead>
          <TableHead>Title</TableHead>
          <TableHead>Assigned To</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Priority</TableHead>
          <TableHead>Due</TableHead>
          <TableHead className="text-right"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((t) => (
          <TableRow key={t.id}>
            <TableCell className="whitespace-nowrap font-mono text-xs text-slate-500">
              {t.task_id}
            </TableCell>
            <TableCell className="font-medium text-slate-900">{t.title}</TableCell>
            <TableCell>{t.assigned_to_name}</TableCell>
            <TableCell>
              <Badge variant="outline">{ROLE_LABEL[t.assignee_role]}</Badge>
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap items-center gap-1">
                <Badge className={STATUS_BADGE[t.status]}>{STATUS_LABEL[t.status]}</Badge>
                {t.is_overdue && <Badge variant="danger">Overdue</Badge>}
              </div>
            </TableCell>
            <TableCell>
              <Badge className={PRIORITY_BADGE[t.priority]}>{t.priority}</Badge>
            </TableCell>
            <TableCell className="whitespace-nowrap text-xs tabular-nums text-slate-600">
              {t.due_date ? new Date(t.due_date).toLocaleDateString() : "—"}
            </TableCell>
            <TableCell className="text-right">
              <Link to={`/tasks/${t.id}`}>
                <Button variant="ghost" size="sm">
                  Open
                </Button>
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ---------------------------------------------------------------------------
// Assign Task Modal
// ---------------------------------------------------------------------------

// One row of an SME task's spec — D9: multi-category task sheet. A task
// can carry more than one of these (e.g. "5 Easy Quant MCQs" + "3 Hard
// Verbal FITB" in the same task).
interface SpecRow {
  qb_category: string;
  qb_subcategory: string;
  question_type: string;
  num_questions: number | "";
  num_options: number | "";
  num_correct: number | "";
  difficulty: "" | "easy" | "medium" | "hard" | "expert";
  cognitive: "" | "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
}

function emptySpecRow(): SpecRow {
  return {
    qb_category: "",
    qb_subcategory: "",
    question_type: "",
    num_questions: "",
    num_options: "",
    num_correct: "",
    difficulty: "",
    cognitive: "",
  };
}

function AssignTaskModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assigneeRole, setAssigneeRole] = useState<AssigneeRole>("sme");
  const [assignedTo, setAssignedTo] = useState<number | "">("");
  const [priority, setPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");
  const [dueDate, setDueDate] = useState("");
  const [parentTaskId, setParentTaskId] = useState("");
  // Report 9 #65: on an SME task, the Reviewer the SME sends the questions to.
  const [taskReviewer, setTaskReviewer] = useState<number | "">("");

  // SME-specific spec fields — a task can carry multiple category/
  // difficulty/type rows (D9: SME multi-category task sheet), so this is a
  // list of rows rather than a single set of fields.
  const [specRows, setSpecRows] = useState<SpecRow[]>([emptySpecRow()]);
  // ADM-4 (§3.1.1): QB categories/subcategories drive the spec dropdowns
  // instead of free text.
  const { data: qbCategories } = useQuery({
    queryKey: ["question-bank", "categories", "all"],
    queryFn: () => listCategories(),
  });
  const topCategories = (qbCategories ?? []).filter((c) => c.parent === null);
  const subsForCategory = (catName: string) => {
    const cat = topCategories.find((c) => c.name === catName);
    return cat ? (qbCategories ?? []).filter((c) => c.parent === cat.id) : [];
  };

  // ADM-3 (§3.1.2/3): a Reviewer/Psychometrician task picks its parent from the
  // upstream tasks not yet assigned to that role, instead of a free-text ID.
  const needsParentPicklist = assigneeRole === "reviewer" || assigneeRole === "psychometrician";
  const { data: allTasksPage } = useQuery({
    queryKey: ["tasks", "all-for-parent"],
    queryFn: () => tasksApi.list(),
    enabled: needsParentPicklist,
  });
  const allTasks = allTasksPage?.results ?? [];
  const hasChildOfRole = (taskId: number, role: AssigneeRole) =>
    allTasks.some((t) => t.parent_task === taskId && t.assignee_role === role);
  const parentTaskOptions =
    assigneeRole === "reviewer"
      ? allTasks.filter((t) => t.assignee_role === "sme" && !hasChildOfRole(t.id, "reviewer"))
      : assigneeRole === "psychometrician"
        ? allTasks.filter(
            (t) =>
              (t.assignee_role === "sme" || t.assignee_role === "reviewer") &&
              !hasChildOfRole(t.id, "psychometrician"),
          )
        : [];

  const updateSpecRow = (index: number, patch: Partial<SpecRow>) => {
    setSpecRows((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };
  const addSpecRow = () => setSpecRows((rows) => [...rows, emptySpecRow()]);
  const removeSpecRow = (index: number) =>
    setSpecRows((rows) => (rows.length > 1 ? rows.filter((_, i) => i !== index) : rows));

  // Load users list filtered by role — every page, so nobody past the first
  // 100 is missing from the pickers.
  const usersQuery = useQuery({
    queryKey: ["users", "by-role", "all", assigneeRole],
    queryFn: () => listAllUsers({ role: assigneeRole }),
  });
  const users = usersQuery.data ?? [];
  // Report 9 #65/#69: active reviewers (with domains) for the SME task.
  const reviewersQuery = useQuery({
    queryKey: ["users", "by-role", "all", "reviewer"],
    queryFn: () => listAllUsers({ role: "reviewer" }),
    enabled: assigneeRole === "sme",
  });
  const reviewers = (reviewersQuery.data ?? []).filter((u) => u.is_active);

  const createMutation = useMutation({
    mutationFn: (input: TaskCreateInput) => tasksApi.create(input),
    onSuccess: () => {
      onCreated();
      setTitle("");
      setDescription("");
      setAssignedTo("");
      setPriority("medium");
      setDueDate("");
      setParentTaskId("");
      setTaskReviewer("");
      setSpecRows([emptySpecRow()]);
    },
    onError: (err) => {
      toast.error(`Failed to assign task: ${extractApiError(err)}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !description || !assignedTo) {
      toast.error("Please fill in all required fields.");
      return;
    }
    const input: TaskCreateInput = {
      title,
      description,
      assigned_to: Number(assignedTo),
      assignee_role: assigneeRole,
      priority,
      due_date: dueDate ? new Date(dueDate).toISOString() : null,
      ...(parentTaskId && assigneeRole !== "sme" ? { parent_task_id: parentTaskId } : {}),
      ...(assigneeRole === "sme"
        ? {
            reviewer: taskReviewer === "" ? null : taskReviewer,
            specs: specRows.map((row) => ({
              qb_category: row.qb_category,
              qb_subcategory: row.qb_subcategory,
              question_type: row.question_type,
              num_questions: row.num_questions === "" ? null : Number(row.num_questions),
              num_options: row.num_options === "" ? null : Number(row.num_options),
              num_correct_options: row.num_correct === "" ? null : Number(row.num_correct),
              difficulty_level: row.difficulty,
              cognitive_level: row.cognitive,
            })),
          }
        : {}),
    };
    createMutation.mutate(input);
  };

  return (
    <Modal open={open} onClose={onClose} title="Assign Task" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="title">Title *</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Create 5 MCQs under Quant > Algebra"
            required
          />
        </div>

        <div>
          <Label htmlFor="description">Description / Message *</Label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detailed instructions for the assignee"
            required
            rows={3}
            className="min-h-[6rem] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="assignee_role">Assignee Role *</Label>
            <select
              id="assignee_role"
              value={assigneeRole}
              onChange={(e) => {
                setAssigneeRole(e.target.value as AssigneeRole);
                setAssignedTo("");
              }}
              className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
            >
              <option value="sme">SME</option>
              <option value="reviewer">Reviewer</option>
              <option value="psychometrician">Psychometrician</option>
              <option value="trainer">Trainer</option>
              <option value="counsellor">Counsellor</option>
            </select>
          </div>
          <div>
            <Label htmlFor="assigned_to">Assignee *</Label>
            <select
              id="assigned_to"
              value={assignedTo}
              onChange={(e) => setAssignedTo(Number(e.target.value))}
              required
              className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
            >
              <option value="">Select user…</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {/* Report 9 #67/#69: domains of expertise next to the name. */}
                  {nameWithExpertise(u.full_name || u.email, u.profile?.domains_of_expertise)}
                </option>
              ))}
            </select>
            {usersQuery.isLoading && <p className="text-xs text-slate-500">Loading users…</p>}
            {users.length === 0 && !usersQuery.isLoading && (
              <p className="text-xs text-warning-600">No users with this role.</p>
            )}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="priority">Priority</Label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as typeof priority)}
              className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
          <div>
            <Label htmlFor="due_date">Due Date</Label>
            <Input
              id="due_date"
              type="datetime-local"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
        </div>

        {/* Report 9 #109: an SME task has no parent (Doc 9 §3.1.2), so the
            free-text parent box is not shown for it. */}
        {assigneeRole !== "sme" && (
          <div>
            <Label htmlFor="parent_task_id">
              {needsParentPicklist ? "Parent task" : "Parent Task ID (optional)"}
            </Label>
            {needsParentPicklist ? (
              <select
                id="parent_task_id"
                className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                value={parentTaskId}
                onChange={(e) => setParentTaskId(e.target.value)}
              >
                <option value="">
                  {parentTaskOptions.length
                    ? "Select an unassigned upstream task…"
                    : "No unassigned upstream tasks available"}
                </option>
                {parentTaskOptions.map((t) => (
                  <option key={t.id} value={t.task_id ?? ""}>
                    {t.task_id} — {t.title} ({ROLE_LABEL[t.assignee_role]})
                  </option>
                ))}
              </select>
            ) : (
              <Input
                id="parent_task_id"
                value={parentTaskId}
                onChange={(e) => setParentTaskId(e.target.value)}
                placeholder="e.g. TSK-2026-AB12CD — links this task to a parent"
              />
            )}
          </div>
        )}

        {assigneeRole === "sme" && (
          <div>
            <Label htmlFor="task_reviewer">Reviewer to send completed questions to</Label>
            <select
              id="task_reviewer"
              className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
              value={taskReviewer}
              onChange={(e) => setTaskReviewer(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Not specified — the SME chooses</option>
              {reviewers.map((u) => (
                <option key={u.id} value={u.id}>
                  {nameWithExpertise(u.full_name || u.email, u.profile?.domains_of_expertise)}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Pre-selected for the SME when he submits the questions for review.
            </p>
          </div>
        )}

        {assigneeRole === "sme" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">SME Task Specification</CardTitle>
              <p className="text-xs text-slate-500">
                Add a row per category/difficulty/type combination this task covers.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              {specRows.map((row, i) => (
                <div key={i} className="space-y-3 rounded-md border border-slate-200 p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Row {i + 1}
                    </p>
                    {specRows.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-danger-600 hover:bg-danger-50 hover:text-danger-700"
                        onClick={() => removeSpecRow(i)}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
                    <div>
                      <Label htmlFor={`qb_category-${i}`}>QB Category</Label>
                      <select
                        id={`qb_category-${i}`}
                        className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                        value={row.qb_category}
                        onChange={(e) =>
                          updateSpecRow(i, { qb_category: e.target.value, qb_subcategory: "" })
                        }
                      >
                        <option value="">Select category...</option>
                        {topCategories.map((c) => (
                          <option key={c.id} value={c.name}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label htmlFor={`qb_subcategory-${i}`}>QB Subcategory</Label>
                      <select
                        id={`qb_subcategory-${i}`}
                        className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25 disabled:opacity-50"
                        value={row.qb_subcategory}
                        disabled={!row.qb_category}
                        onChange={(e) => updateSpecRow(i, { qb_subcategory: e.target.value })}
                      >
                        <option value="">
                          {row.qb_category ? "Select subcategory..." : "Choose a category first"}
                        </option>
                        {subsForCategory(row.qb_category).map((c) => (
                          <option key={c.id} value={c.name}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <Label htmlFor={`question_type-${i}`}>Question Type</Label>
                    <select
                      id={`question_type-${i}`}
                      className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                      value={row.question_type}
                      onChange={(e) => updateSpecRow(i, { question_type: e.target.value })}
                    >
                      <option value="">Select type...</option>
                      {QUESTION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-3 gap-3 sm:gap-4">
                    <div>
                      <Label htmlFor={`num_questions-${i}`}># Questions</Label>
                      <Input
                        id={`num_questions-${i}`}
                        type="number"
                        value={row.num_questions}
                        onChange={(e) =>
                          updateSpecRow(i, {
                            num_questions: e.target.value ? Number(e.target.value) : "",
                          })
                        }
                      />
                    </div>
                    <div>
                      <Label htmlFor={`num_options-${i}`}># Options</Label>
                      <Input
                        id={`num_options-${i}`}
                        type="number"
                        value={row.num_options}
                        onChange={(e) =>
                          updateSpecRow(i, {
                            num_options: e.target.value ? Number(e.target.value) : "",
                          })
                        }
                      />
                    </div>
                    <div>
                      <Label htmlFor={`num_correct-${i}`}># Correct</Label>
                      <Input
                        id={`num_correct-${i}`}
                        type="number"
                        value={row.num_correct}
                        onChange={(e) =>
                          updateSpecRow(i, {
                            num_correct: e.target.value ? Number(e.target.value) : "",
                          })
                        }
                      />
                    </div>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
                    <div>
                      <Label htmlFor={`difficulty-${i}`}>Difficulty (optional)</Label>
                      <select
                        id={`difficulty-${i}`}
                        value={row.difficulty}
                        onChange={(e) =>
                          updateSpecRow(i, { difficulty: e.target.value as SpecRow["difficulty"] })
                        }
                        className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                      >
                        <option value="">—</option>
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                        <option value="expert">Expert</option>
                      </select>
                    </div>
                    <div>
                      <Label htmlFor={`cognitive-${i}`}>Cognitive Level (optional)</Label>
                      <select
                        id={`cognitive-${i}`}
                        value={row.cognitive}
                        onChange={(e) =>
                          updateSpecRow(i, { cognitive: e.target.value as SpecRow["cognitive"] })
                        }
                        className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                      >
                        <option value="">—</option>
                        <option value="remember">Remember</option>
                        <option value="understand">Understand</option>
                        <option value="apply">Apply</option>
                        <option value="analyze">Analyze</option>
                        <option value="evaluate">Evaluate</option>
                        <option value="create">Create</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={addSpecRow}>
                + Add another category
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Assigning…" : "Assign Task"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
