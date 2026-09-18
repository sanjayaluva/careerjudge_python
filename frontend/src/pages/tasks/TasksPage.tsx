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
import { listUsers } from "@/api/users";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  in_progress: "bg-blue-100 text-blue-700",
  awaiting_review: "bg-amber-100 text-amber-700",
  completed: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-red-100 text-red-700",
  overdue: "bg-red-100 text-red-700",
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
  low: "bg-slate-100 text-slate-700",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-amber-100 text-amber-700",
  urgent: "bg-red-100 text-red-700",
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
        <div className="flex items-start justify-between p-6 pb-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Task Management</h1>
            <p className="text-sm text-slate-500">
              {isAdmin
                ? "Assign and monitor tasks for SME / Reviewer / Psychometrician / Trainer / Counsellor"
                : "Tasks assigned to you by the admin"}
            </p>
          </div>
          {isAdmin && <Button onClick={() => setAssignOpen(true)}>+ Assign Task</Button>}
        </div>

        <Tabs defaultValue={isAdmin ? "assigned" : "mine"}>
          <div className="px-6">
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
    return <p className="py-8 text-center text-sm text-slate-500">{emptyMessage}</p>;
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
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((t) => (
          <TableRow key={t.id}>
            <TableCell className="font-mono text-xs">{t.task_id}</TableCell>
            <TableCell className="font-medium">{t.title}</TableCell>
            <TableCell>{t.assigned_to_name}</TableCell>
            <TableCell>
              <Badge variant="outline">{ROLE_LABEL[t.assignee_role]}</Badge>
            </TableCell>
            <TableCell>
              <Badge className={STATUS_BADGE[t.status]}>{STATUS_LABEL[t.status]}</Badge>
              {t.is_overdue && <Badge className="ml-1 bg-red-100 text-red-700">Overdue</Badge>}
            </TableCell>
            <TableCell>
              <Badge className={PRIORITY_BADGE[t.priority]}>{t.priority}</Badge>
            </TableCell>
            <TableCell className="text-xs text-slate-600">
              {t.due_date ? new Date(t.due_date).toLocaleDateString() : "—"}
            </TableCell>
            <TableCell>
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

  // Load users list filtered by role
  const usersQuery = useQuery({
    queryKey: ["users", "by-role", assigneeRole],
    queryFn: () => listUsers({ role: assigneeRole, page_size: 100 }),
  });
  const users = usersQuery.data?.results ?? [];

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
      ...(parentTaskId ? { parent_task_id: parentTaskId } : {}),
      ...(assigneeRole === "sme"
        ? {
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
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="assignee_role">Assignee Role *</Label>
            <select
              id="assignee_role"
              value={assigneeRole}
              onChange={(e) => {
                setAssigneeRole(e.target.value as AssigneeRole);
                setAssignedTo("");
              }}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
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
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select user…</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </option>
              ))}
            </select>
            {usersQuery.isLoading && <p className="text-xs text-slate-500">Loading users…</p>}
            {users.length === 0 && !usersQuery.isLoading && (
              <p className="text-xs text-amber-600">No users with this role.</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="priority">Priority</Label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as typeof priority)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
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

        <div>
          <Label htmlFor="parent_task_id">
            {needsParentPicklist ? "Parent task" : "Parent Task ID (optional)"}
          </Label>
          {needsParentPicklist ? (
            <select
              id="parent_task_id"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
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
                        className="text-danger hover:bg-danger-50"
                        onClick={() => removeSpecRow(i)}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor={`qb_category-${i}`}>QB Category</Label>
                      <select
                        id={`qb_category-${i}`}
                        className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
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
                        className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm disabled:opacity-50"
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
                      className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
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
                  <div className="grid grid-cols-3 gap-3">
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
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor={`difficulty-${i}`}>Difficulty (optional)</Label>
                      <select
                        id={`difficulty-${i}`}
                        value={row.difficulty}
                        onChange={(e) =>
                          updateSpecRow(i, { difficulty: e.target.value as SpecRow["difficulty"] })
                        }
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
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
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
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

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
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
