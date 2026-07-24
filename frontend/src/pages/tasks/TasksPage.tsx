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

  // SME-specific spec fields
  const [qbCategory, setQbCategory] = useState("");
  const [qbSubcategory, setQbSubcategory] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [numQuestions, setNumQuestions] = useState<number | "">("");
  const [numOptions, setNumOptions] = useState<number | "">("");
  const [numCorrect, setNumCorrect] = useState<number | "">("");
  const [difficulty, setDifficulty] = useState<"" | "easy" | "medium" | "hard" | "expert">("");
  const [cognitive, setCognitive] = useState<
    "" | "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create"
  >("");

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
      setQbCategory("");
      setQbSubcategory("");
      setQuestionType("");
      setNumQuestions("");
      setNumOptions("");
      setNumCorrect("");
      setDifficulty("");
      setCognitive("");
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
            spec: {
              qb_category: qbCategory,
              qb_subcategory: qbSubcategory,
              question_type: questionType,
              num_questions: numQuestions === "" ? null : Number(numQuestions),
              num_options: numOptions === "" ? null : Number(numOptions),
              num_correct_options: numCorrect === "" ? null : Number(numCorrect),
              difficulty_level: difficulty,
              cognitive_level: cognitive,
            },
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
          <Label htmlFor="parent_task_id">Parent Task ID (optional)</Label>
          <Input
            id="parent_task_id"
            value={parentTaskId}
            onChange={(e) => setParentTaskId(e.target.value)}
            placeholder="e.g. TSK-2026-AB12CD — links this task to a parent (e.g. SME task for a Reviewer task)"
          />
        </div>

        {assigneeRole === "sme" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">SME Task Specification</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="qb_category">QB Category</Label>
                  <Input
                    id="qb_category"
                    value={qbCategory}
                    onChange={(e) => setQbCategory(e.target.value)}
                    placeholder="e.g. Quantitative"
                  />
                </div>
                <div>
                  <Label htmlFor="qb_subcategory">QB Subcategory</Label>
                  <Input
                    id="qb_subcategory"
                    value={qbSubcategory}
                    onChange={(e) => setQbSubcategory(e.target.value)}
                    placeholder="e.g. Algebra"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="question_type">Question Type</Label>
                <Input
                  id="question_type"
                  value={questionType}
                  onChange={(e) => setQuestionType(e.target.value)}
                  placeholder="e.g. mcq_text"
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label htmlFor="num_questions"># Questions</Label>
                  <Input
                    id="num_questions"
                    type="number"
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(e.target.value ? Number(e.target.value) : "")}
                  />
                </div>
                <div>
                  <Label htmlFor="num_options"># Options</Label>
                  <Input
                    id="num_options"
                    type="number"
                    value={numOptions}
                    onChange={(e) => setNumOptions(e.target.value ? Number(e.target.value) : "")}
                  />
                </div>
                <div>
                  <Label htmlFor="num_correct"># Correct</Label>
                  <Input
                    id="num_correct"
                    type="number"
                    value={numCorrect}
                    onChange={(e) => setNumCorrect(e.target.value ? Number(e.target.value) : "")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="difficulty">Difficulty (optional)</Label>
                  <select
                    id="difficulty"
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as typeof difficulty)}
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
                  <Label htmlFor="cognitive">Cognitive Level (optional)</Label>
                  <select
                    id="cognitive"
                    value={cognitive}
                    onChange={(e) => setCognitive(e.target.value as typeof cognitive)}
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
