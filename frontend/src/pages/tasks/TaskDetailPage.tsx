/**
 * Task detail page — view a single task, see progress, take action.
 * SRS 09 §3.2 — Manage Task: monitor progress, cancel, approve completion.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

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
  useToast,
} from "@/components/ui";
import { tasksApi, type Task, type AssigneeRole, type TaskExtensionRequest } from "@/api/tasks";
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

const ROLE_LABEL: Record<AssigneeRole, string> = {
  sme: "SME",
  reviewer: "Reviewer",
  psychometrician: "Psychometrician",
  trainer: "Trainer",
  counsellor: "Counsellor",
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const taskId = Number(id);
  const { user } = useAuth();
  const isAdmin = user?.role === "cj_admin";
  const qc = useQueryClient();
  const toast = useToast();

  const [progressMsg, setProgressMsg] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [approveOpen, setApproveOpen] = useState(false);
  const [approveComment, setApproveComment] = useState("");
  const [extensionOpen, setExtensionOpen] = useState(false);
  const [extDate, setExtDate] = useState("");
  const [extReason, setExtReason] = useState("");

  const taskQuery = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => tasksApi.retrieve(taskId),
    enabled: !!taskId,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["task", taskId] });
    qc.invalidateQueries({ queryKey: ["tasks"] });
  };

  const startMutation = useMutation({
    mutationFn: () => tasksApi.start(taskId),
    onSuccess: () => {
      toast.success("Task started.");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const submitMutation = useMutation({
    mutationFn: (msg: string) => tasksApi.submit(taskId, msg),
    onSuccess: () => {
      toast.success("Submitted for review.");
      setProgressMsg("");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const approveMutation = useMutation({
    mutationFn: (comment: string) => tasksApi.approve(taskId, comment),
    onSuccess: () => {
      toast.success("Task approved and marked complete.");
      setApproveOpen(false);
      setApproveComment("");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const cancelMutation = useMutation({
    mutationFn: (reason: string) => tasksApi.cancel(taskId, reason),
    onSuccess: () => {
      toast.success("Task cancelled.");
      setCancelOpen(false);
      setCancelReason("");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const requestUpdateMutation = useMutation({
    mutationFn: (msg: string) => tasksApi.requestUpdate(taskId, msg),
    onSuccess: () => {
      toast.success("Progress update requested.");
      setProgressMsg("");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const postProgressMutation = useMutation({
    mutationFn: (msg: string) => tasksApi.postProgress(taskId, msg),
    onSuccess: () => {
      toast.success("Progress update posted.");
      setProgressMsg("");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const requestExtensionMutation = useMutation({
    mutationFn: ({ date, reason }: { date: string; reason: string }) =>
      tasksApi.requestExtension(taskId, date, reason),
    onSuccess: () => {
      toast.success("Extension requested.");
      setExtensionOpen(false);
      setExtDate("");
      setExtReason("");
      invalidate();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  if (taskQuery.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }
  if (taskQuery.isError || !taskQuery.data) {
    return (
      <PageCard>
        <div className="p-6">
          <p className="text-sm text-red-600">Task not found or you don't have access.</p>
          <Link to="/tasks" className="mt-2 inline-block text-sm text-primary-600">
            ← Back to Tasks
          </Link>
        </div>
      </PageCard>
    );
  }

  const task: Task = taskQuery.data;
  const isAssignee = task.assigned_to === user?.id;
  const canStart = isAssignee && task.status === "pending";
  const canSubmit = isAssignee && task.status === "in_progress";
  const canApprove = isAdmin && task.status === "awaiting_review";
  const canCancel = isAdmin && !["completed", "cancelled"].includes(task.status);
  const canRequestExtension = isAssignee && !["completed", "cancelled"].includes(task.status);
  const canPostProgress = isAssignee || isAdmin;
  const canRequestUpdate = isAdmin && !["completed", "cancelled"].includes(task.status);

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="p-6 pb-4">
          <Link to="/tasks" className="text-sm text-primary-600">
            ← Back to Tasks
          </Link>
          <div className="mt-2 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-slate-500">{task.task_id}</span>
                <Badge className={STATUS_BADGE[task.status]}>{STATUS_LABEL[task.status]}</Badge>
                <Badge variant="outline">{ROLE_LABEL[task.assignee_role]}</Badge>
                <Badge variant="outline" className="capitalize">
                  {task.priority}
                </Badge>
                {task.is_overdue && <Badge className="bg-red-100 text-red-700">Overdue</Badge>}
              </div>
              <h1 className="mt-1 text-lg font-bold text-slate-900">{task.title}</h1>
              <p className="text-sm text-slate-500">
                Assigned to <strong>{task.assigned_to_name}</strong> by{" "}
                <strong>{task.assigned_by_name}</strong>
              </p>
            </div>
            <div className="flex gap-2">
              {canStart && (
                <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
                  Start
                </Button>
              )}
              {canSubmit && (
                <Button
                  onClick={() => submitMutation.mutate("Submitted for review.")}
                  disabled={submitMutation.isPending}
                >
                  Submit for Review
                </Button>
              )}
              {canApprove && (
                <Button onClick={() => setApproveOpen(true)}>Approve Completion</Button>
              )}
              {canCancel && (
                <Button variant="danger" onClick={() => setCancelOpen(true)}>
                  Cancel Task
                </Button>
              )}
              {canRequestUpdate && (
                <Button
                  variant="outline"
                  onClick={() => setProgressMsg("Please provide an update on this task.")}
                >
                  Request Update
                </Button>
              )}
              {canRequestExtension && (
                <Button variant="outline" onClick={() => setExtensionOpen(true)}>
                  Request Extension
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 p-6 pt-0 md:grid-cols-3">
          <div className="md:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm text-slate-700">{task.description}</p>
              </CardContent>
            </Card>

            {task.spec && (
              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-sm">Specification</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  {task.spec.qb_category && (
                    <p>
                      <strong>QB Category:</strong> {task.spec.qb_category}
                    </p>
                  )}
                  {task.spec.qb_subcategory && (
                    <p>
                      <strong>Subcategory:</strong> {task.spec.qb_subcategory}
                    </p>
                  )}
                  {task.spec.question_type && (
                    <p>
                      <strong>Question Type:</strong> {task.spec.question_type}
                    </p>
                  )}
                  {task.spec.num_questions != null && (
                    <p>
                      <strong># Questions:</strong> {task.spec.num_questions}
                    </p>
                  )}
                  {task.spec.num_options != null && (
                    <p>
                      <strong># Options:</strong> {task.spec.num_options}
                    </p>
                  )}
                  {task.spec.num_correct_options != null && (
                    <p>
                      <strong># Correct:</strong> {task.spec.num_correct_options}
                    </p>
                  )}
                  {task.spec.difficulty_level && (
                    <p>
                      <strong>Difficulty:</strong> {task.spec.difficulty_level}
                    </p>
                  )}
                  {task.spec.cognitive_level && (
                    <p>
                      <strong>Cognitive Level:</strong> {task.spec.cognitive_level}
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">Progress Updates</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {task.progress_updates && task.progress_updates.length > 0 ? (
                  task.progress_updates.map((u) => (
                    <div
                      key={u.id}
                      className={`rounded-md border p-3 text-sm ${
                        u.is_admin_request
                          ? "border-amber-200 bg-amber-50"
                          : u.author_role === "admin"
                            ? "border-blue-200 bg-blue-50"
                            : "border-slate-200"
                      }`}
                    >
                      <div className="mb-1 flex items-center gap-2 text-xs text-slate-600">
                        <strong>{u.author_name}</strong>
                        <span>·</span>
                        <span>{new Date(u.created_at).toLocaleString()}</span>
                        {u.is_admin_request && (
                          <Badge className="bg-amber-100 text-amber-700">Admin Request</Badge>
                        )}
                      </div>
                      <p className="text-slate-700">{u.message}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No progress updates yet.</p>
                )}

                {canPostProgress && (
                  <div className="mt-4 space-y-2">
                    <textarea
                      value={progressMsg}
                      onChange={(e) => setProgressMsg(e.target.value)}
                      placeholder={
                        canRequestUpdate
                          ? "Type a message to the assignee…"
                          : "Post a progress update…"
                      }
                      rows={2}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <div className="flex justify-end gap-2">
                      {canRequestUpdate && progressMsg && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => requestUpdateMutation.mutate(progressMsg)}
                          disabled={requestUpdateMutation.isPending}
                        >
                          Send as Admin Request
                        </Button>
                      )}
                      <Button
                        size="sm"
                        onClick={() => postProgressMutation.mutate(progressMsg)}
                        disabled={!progressMsg || postProgressMutation.isPending}
                      >
                        Post Update
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div>
                  <p className="text-xs text-slate-500">Due Date</p>
                  <p>{task.due_date ? new Date(task.due_date).toLocaleString() : "No due date"}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Started</p>
                  <p>{task.started_at ? new Date(task.started_at).toLocaleString() : "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Completed</p>
                  <p>{task.completed_at ? new Date(task.completed_at).toLocaleString() : "—"}</p>
                </div>
                {task.parent_task_id && (
                  <div>
                    <p className="text-xs text-slate-500">Parent Task</p>
                    <p className="font-mono">{task.parent_task_id}</p>
                  </div>
                )}
                {task.approval_comment && (
                  <div>
                    <p className="text-xs text-slate-500">Approval Comment</p>
                    <p>{task.approval_comment}</p>
                  </div>
                )}
                {task.cancellation_reason && (
                  <div>
                    <p className="text-xs text-slate-500">Cancellation Reason</p>
                    <p>{task.cancellation_reason}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {task.extension_requests && task.extension_requests.length > 0 && (
              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-sm">Extension Requests</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {task.extension_requests.map((e) => (
                    <ExtensionRequestCard key={e.id} ext={e} onAction={invalidate} />
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </PageCard>

      {/* Cancel Modal */}
      {cancelOpen && (
        <Modal open={cancelOpen} onClose={() => setCancelOpen(false)} title="Cancel Task">
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              The assignee will lose access to this task. A notification will be sent.
            </p>
            <div>
              <Label htmlFor="cancel_reason">Reason *</Label>
              <textarea
                id="cancel_reason"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
                required
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setCancelOpen(false)}>
                Close
              </Button>
              <Button
                variant="danger"
                disabled={!cancelReason || cancelMutation.isPending}
                onClick={() => cancelMutation.mutate(cancelReason)}
              >
                Confirm Cancel
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Approve Modal */}
      {approveOpen && (
        <Modal open={approveOpen} onClose={() => setApproveOpen(false)} title="Approve Completion">
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              The task will be marked as completed. The assignee will be notified.
            </p>
            <div>
              <Label htmlFor="approve_comment">Comment (optional)</Label>
              <textarea
                id="approve_comment"
                value={approveComment}
                onChange={(e) => setApproveComment(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setApproveOpen(false)}>
                Close
              </Button>
              <Button
                disabled={approveMutation.isPending}
                onClick={() => approveMutation.mutate(approveComment)}
              >
                Approve
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Extension Modal */}
      {extensionOpen && (
        <Modal
          open={extensionOpen}
          onClose={() => setExtensionOpen(false)}
          title="Request Extension"
        >
          <div className="space-y-3">
            <div>
              <Label htmlFor="ext_date">Requested Due Date *</Label>
              <Input
                id="ext_date"
                type="datetime-local"
                value={extDate}
                onChange={(e) => setExtDate(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="ext_reason">Reason</Label>
              <textarea
                id="ext_reason"
                value={extReason}
                onChange={(e) => setExtReason(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setExtensionOpen(false)}>
                Close
              </Button>
              <Button
                disabled={!extDate || requestExtensionMutation.isPending}
                onClick={() =>
                  requestExtensionMutation.mutate({
                    date: new Date(extDate).toISOString(),
                    reason: extReason,
                  })
                }
              >
                Submit Request
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Extension Request Card
// ---------------------------------------------------------------------------

function ExtensionRequestCard({
  ext,
  onAction,
}: {
  ext: TaskExtensionRequest;
  onAction: () => void;
}) {
  const toast = useToast();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");

  const approveMutation = useMutation({
    mutationFn: () => tasksApi.approveExtension(ext.id, comment),
    onSuccess: () => {
      toast.success("Extension approved.");
      setComment("");
      qc.invalidateQueries({ queryKey: ["task"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onAction();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  const declineMutation = useMutation({
    mutationFn: () => tasksApi.declineExtension(ext.id, comment),
    onSuccess: () => {
      toast.success("Extension declined.");
      setComment("");
      qc.invalidateQueries({ queryKey: ["task"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onAction();
    },
    onError: (err) => toast.error(`Failed: ${extractApiError(err)}`),
  });

  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <div className="mb-1 flex items-center justify-between">
        <Badge
          className={
            ext.status === "approved"
              ? "bg-emerald-100 text-emerald-700"
              : ext.status === "declined"
                ? "bg-red-100 text-red-700"
                : "bg-amber-100 text-amber-700"
          }
        >
          {ext.status}
        </Badge>
        <span className="text-xs text-slate-500">{new Date(ext.created_at).toLocaleString()}</span>
      </div>
      <p className="text-xs text-slate-600">
        <strong>From:</strong> {new Date(ext.current_due_date).toLocaleString()}
      </p>
      <p className="text-xs text-slate-600">
        <strong>To:</strong> {new Date(ext.requested_due_date).toLocaleString()}
      </p>
      {ext.reason && <p className="mt-1 text-xs italic">"{ext.reason}"</p>}
      {ext.status === "pending" && (
        <div className="mt-2 space-y-2">
          <Input
            placeholder="Comment (optional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="text-xs"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate()}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={declineMutation.isPending}
              onClick={() => declineMutation.mutate()}
            >
              Decline
            </Button>
          </div>
        </div>
      )}
      {ext.review_comment && <p className="mt-2 text-xs italic">Admin: "{ext.review_comment}"</p>}
    </div>
  );
}
