/**
 * Assessments page — list assessments + create new.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Badge,
  Button,
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
  WysiwygEditor,
  useToast,
} from "@/components/ui";
import {
  type AssessmentSession,
  ASSESSMENT_STATUSES,
  ASSESSMENT_TYPES,
  ATTEMPT_RULES,
  NAVIGATION_RULES,
  TIMER_LEVELS,
  createAssessment,
  deleteAssessment,
  listAssessments,
  listMySessions,
  publishAssessment,
  startSession,
} from "@/api/assessment";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

import { CandidateAssessments } from "./CandidateAssessments";
import { fromEditorHtml } from "./richDefinition";
import { useTakeAssessment } from "./useTakeAssessment";
import { PrivateSpaceNote } from "@/components/PrivateSpaceNote";
import { usePrivateSpace } from "@/hooks/usePrivateSpace";

const ASSESS_KEY = ["assessments"];

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function AssessmentsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  // Report 3 §4.1 / Doc 7 §2.4.1 (signed): trainers author their own assessments
  // using the CJ Question Bank. The backend scopes a trainer to their OWN
  // assessments; the list only shows their drafts + published, so Publish/Delete
  // here act on their own drafts.
  // Report 9 #10: corporate admins do not author assessments — they see and
  // schedule only what CJ Admin assigned to their organization.
  const canManage = ["cj_admin", "psychometrician", "trainer"].includes(user?.role ?? "");
  // Report 9 #41/#42: the Corporate Exclusive Admin authors his organization's
  // private assessments; CJ assessments licensed to him stay read-only.
  const { isPrivateAuthor, ownsItem } = usePrivateSpace();
  const canCreate = canManage || isPrivateAuthor;
  const canManageRow = (a: { owner_organization?: number | null }) => canManage || ownsItem(a);
  // Report 9 #72: the individual sees My Assessments apart from Browse.
  const isCandidate = user?.role === "individual";
  // Report 9 #113: Help Desk views every assessment, read-only.
  const viewOnly = user?.role === "helpdesk";

  const { data, isLoading } = useQuery({
    queryKey: [...ASSESS_KEY, debouncedSearch, statusFilter],
    queryFn: () =>
      listAssessments({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      }),
  });

  // Fetch the current user's sessions so we can show Take / Resume / View
  // Results actions per assessment. Individual users (candidates) need this
  // to interact with assessments — without it, the actions column is empty.
  const { data: mySessions } = useQuery({
    queryKey: ["my-sessions"],
    queryFn: () => listMySessions(),
  });

  // Build a lookup: assessmentId → latest session for the current user
  const sessionByAssessment = new Map<number, AssessmentSession>();
  for (const s of mySessions ?? []) {
    const existing = sessionByAssessment.get(s.assessment);
    if (!existing || new Date(s.started_at) > new Date(existing.started_at)) {
      sessionByAssessment.set(s.assessment, s);
    }
  }

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createAssessment(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ASSESS_KEY });
      setCreateOpen(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const publishMutation = useMutation({
    mutationFn: (id: number) => publishAssessment(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ASSESS_KEY });
      toast.success("Assessment published.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAssessment(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ASSESS_KEY });
      toast.success("Assessment deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Resume an in-flight session (no payment needed — it was paid to begin).
  const startSessionMutation = useMutation({
    mutationFn: (assessmentId: number) => startSession(assessmentId),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["my-sessions"] });
      navigate(`/assessments/sessions/${data.id}`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Report 9 #73/#75: Take Assessment → pay prompt with the price for a paid
  // assessment → the assessment description page, whose Start begins it.
  const take = useTakeAssessment();

  const assessments = data?.results ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Assessments</h1>
            <p className="text-sm text-slate-500">
              {data?.count ?? 0} assessment{(data?.count ?? 0) !== 1 ? "s" : ""}
            </p>
          </div>
          {canCreate && <Button onClick={() => setCreateOpen(true)}>Create assessment</Button>}
        </div>
        <div className="px-6 pb-4 empty:hidden">
          <PrivateSpaceNote what="assessments" />
        </div>

        <div className="flex flex-wrap items-center gap-2 px-6 pb-4">
          <Input
            type="search"
            placeholder="Search assessments..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setTimeout(() => setDebouncedSearch(e.target.value), 350);
            }}
            className="max-w-sm"
          />
          {/* Report 9 #74: only authors see drafts, so only they filter by status. */}
          {(canCreate || viewOnly) && (
            <select
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All statuses</option>
              {ASSESSMENT_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          )}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : assessments.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            {canCreate
              ? "No assessments yet. Create one to get started."
              : "No assessments are available to you yet."}
          </p>
        ) : isCandidate ? (
          <CandidateAssessments
            assessments={assessments}
            sessionByAssessment={sessionByAssessment}
            take={take}
            onResume={(id) => startSessionMutation.mutate(id)}
            resuming={startSessionMutation.isPending}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Navigation</TableHead>
                <TableHead>Sections</TableHead>
                <TableHead>Sessions</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assessments.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium text-slate-900">
                    <a href={`/assessments/${a.id}`} className="text-primary-600 hover:underline">
                      {a.title}
                    </a>
                  </TableCell>
                  <TableCell>
                    <Badge variant={a.assessment_type === "psychometric" ? "primary" : "default"}>
                      {a.assessment_type === "psychometric" ? "Psychometric" : "Normal"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[a.status] ?? "default"}>{a.status}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">
                    {a.total_duration_seconds
                      ? `${Math.floor(a.total_duration_seconds / 60)} min`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-xs text-slate-500">
                    {NAVIGATION_RULES.find((n) => n.value === a.navigation_rule)?.label ?? "—"}
                  </TableCell>
                  <TableCell className="text-slate-500">{a.section_count}</TableCell>
                  <TableCell className="text-slate-500">{a.session_count}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      {/* Manager actions: Publish + Delete (draft only) */}
                      {a.status === "draft" && canManageRow(a) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={publishMutation.isPending}
                          onClick={() => publishMutation.mutate(a.id)}
                        >
                          Publish
                        </Button>
                      )}
                      {a.status === "draft" && canManageRow(a) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-danger hover:bg-danger-50"
                          onClick={() => deleteMutation.mutate(a.id)}
                        >
                          Delete
                        </Button>
                      )}
                      {/* Candidate actions: Take / Resume / View Results.
                          Available to all users on published assessments. */}
                      {a.status === "published" &&
                        !viewOnly &&
                        (() => {
                          const session = sessionByAssessment.get(a.id);
                          if (!session) {
                            return (
                              <Button
                                size="sm"
                                loading={take.checkingId === a.id}
                                onClick={() => take.begin(a)}
                              >
                                Take Assessment
                              </Button>
                            );
                          }
                          if (session.status === "active" || session.status === "suspended") {
                            return (
                              <Button
                                size="sm"
                                loading={startSessionMutation.isPending}
                                onClick={() => startSessionMutation.mutate(a.id)}
                              >
                                Resume
                              </Button>
                            );
                          }
                          if (session.status === "completed") {
                            return (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  navigate(`/assessments/sessions/${session.id}/results`)
                                }
                              >
                                View Results
                              </Button>
                            );
                          }
                          return null;
                        })()}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </PageCard>

      {take.prompt}

      <CreateAssessmentModal
        open={createOpen}
        loading={createMutation.isPending}
        onClose={() => {
          setCreateOpen(false);
        }}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />
    </div>
  );
}

function CreateAssessmentModal({
  open,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [title, setTitle] = useState("");
  const [assessmentType, setAssessmentType] = useState<"normal" | "psychometric">("normal");
  const [objective, setObjective] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [duration, setDuration] = useState("");
  const [navigationRule, setNavigationRule] = useState("FREE");
  const [attemptRule, setAttemptRule] = useState("SINGLE_SESSION");
  const [displayOrder, setDisplayOrder] = useState<"STATIC" | "RANDOM">("STATIC");
  const [timerLevel, setTimerLevel] = useState("assessment");

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create Assessment"
      description="Configure a new assessment with sections, questions, and delivery rules."
      size="lg"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          // The form collects duration in MINUTES (user-friendly), but the
          // backend stores total_duration_seconds. Convert here.
          const durationMinutes = duration ? parseInt(duration, 10) : null;
          onSubmit({
            title,
            assessment_type: assessmentType,
            objective,
            description: fromEditorHtml(description),
            instructions: fromEditorHtml(instructions),
            total_duration_seconds: durationMinutes !== null ? durationMinutes * 60 : null,
            navigation_rule: navigationRule,
            attempt_rule: attemptRule,
            display_order: displayOrder,
            timer_level: timerLevel,
          });
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="title" required>
            Assessment title
          </Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Career Aptitude Test 2026"
            required
          />
        </div>
        <div>
          <Label htmlFor="assessment_type" required>
            Assessment type
          </Label>
          <div className="mt-1 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {ASSESSMENT_TYPES.map((t) => (
              <label
                key={t.value}
                className={`flex cursor-pointer flex-col rounded-md border p-3 text-sm transition-colors ${
                  assessmentType === t.value
                    ? "border-primary-500 bg-primary-50"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="assessment_type"
                    checked={assessmentType === t.value}
                    onChange={() => setAssessmentType(t.value)}
                    className="h-4 w-4"
                  />
                  <span className="font-medium text-slate-900">{t.label}</span>
                </div>
                <span className="mt-1 text-xs text-slate-500">{t.description}</span>
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-amber-700">
            ⚠ Once created, only matching question types can be attached to this assessment. Normal
            and psychometric questions cannot be mixed.
          </p>
        </div>
        <div>
          <Label htmlFor="objective">Objective</Label>
          <textarea
            id="objective"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="What this assessment measures..."
          />
        </div>
        {/* Report 9 #75 (Doc 3 §2.1.2): Description and Instructions are
            formatted text with images, shown on the assessment description
            page before the test begins. */}
        <div>
          <Label>Description (shown to candidates)</Label>
          <WysiwygEditor value={description} onChange={setDescription} minHeight={120} />
        </div>
        <div>
          <Label>Instructions (shown to candidates)</Label>
          <WysiwygEditor value={instructions} onChange={setInstructions} minHeight={120} />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <Label htmlFor="duration">Duration (minutes)</Label>
            <Input
              id="duration"
              type="number"
              min="1"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="e.g. 60"
            />
            <p className="mt-1 text-xs text-slate-400">
              Leave empty for no time limit. Stored as seconds on the server.
            </p>
          </div>
          <div>
            <Label htmlFor="nav">Navigation</Label>
            <select
              id="nav"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={navigationRule}
              onChange={(e) => setNavigationRule(e.target.value)}
            >
              {NAVIGATION_RULES.map((n) => (
                <option key={n.value} value={n.value}>
                  {n.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="attempt">Attempt rule</Label>
            <select
              id="attempt"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={attemptRule}
              onChange={(e) => setAttemptRule(e.target.value)}
            >
              {ATTEMPT_RULES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="display_order">Display order</Label>
            <select
              id="display_order"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={displayOrder}
              onChange={(e) => setDisplayOrder(e.target.value as "STATIC" | "RANDOM")}
            >
              <option value="STATIC">Static (as configured)</option>
              <option value="RANDOM">Random</option>
            </select>
          </div>
          <div>
            <Label htmlFor="timer_level">Timer level</Label>
            <select
              id="timer_level"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={timerLevel}
              onChange={(e) => setTimerLevel(e.target.value)}
            >
              {TIMER_LEVELS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-400">
              Only one level can have a timer — set the duration above for assessment-level.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create assessment
          </Button>
        </div>
      </form>
    </Modal>
  );
}
