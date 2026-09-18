/**
 * Assessment Detail Page — shows assessment config with tabs:
 * - Overview: assessment properties + edit
 * - Sections: hierarchical section tree + CRUD
 * - Questions: assign question bank questions to sections
 * - Sessions: list sessions for this assessment
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

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
  stripHtml,
  useToast,
} from "@/components/ui";
import {
  type AssessmentDetail,
  type AssessmentReadiness as _AssessmentReadiness,
  type AssessmentSection,
  type AssessmentSession,
  ATTEMPT_RULES,
  NAVIGATION_RULES,
  TIMER_LEVELS,
  approveModificationRequest,
  assignQuestion,
  createSection,
  declineModificationRequest,
  deleteAssessment,
  deleteSection,
  getAssessmentReadiness,
  listModificationRequests,
  listMySessions,
  listSectionQuestions,
  publishAssessment,
  unpublishAssessment,
  removeQuestion,
  requestAssessmentTitleChange,
  retrieveAssessment,
  startSession,
  updateAssessment,
  updateAssignedQuestion,
  updateSection,
} from "@/api/assessment";
import {
  listQuestions,
  NORMAL_QUESTION_TYPES,
  PSYCHOMETRIC_QUESTION_TYPES_LIST,
  retrieveQuestion,
} from "@/api/questionBank";
import { extractApiError, extractApiErrorCode } from "@/api/client";
import { createCheckout, openRazorpayCheckout } from "@/api/payments";
import { useAuth } from "@/hooks/useAuth";
const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const aid = Number(id);
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [sectionModal, setSectionModal] = useState<{
    open: boolean;
    parent: number | null;
    /** When set, the modal is in edit-mode (pre-populated with this section). */
    editSection: AssessmentSection | null;
  }>({ open: false, parent: null, editSection: null });
  const [sectionToDelete, setSectionToDelete] = useState<AssessmentSection | null>(null);

  const toast = useToast();
  const canManage = ["cj_admin", "corp_admin", "psychometrician"].includes(user?.role ?? "");

  const { data: assessment, isLoading } = useQuery({
    queryKey: ["assessments", aid],
    queryFn: () => retrieveAssessment(aid),
    enabled: !Number.isNaN(aid),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishAssessment(aid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", aid] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const unpublishMutation = useMutation({
    mutationFn: () => unpublishAssessment(aid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", aid] });
      toast.success("Assessment returned to draft.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const startSessionMutation = useMutation({
    mutationFn: () => startSession(aid),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      navigate(`/assessments/sessions/${data.id}`);
    },
    onError: async (err) => {
      // PLT-3 pay-for-test gate: a priced assessment answers 402 until paid.
      // Kick off Stripe checkout for this assessment; on return the candidate
      // starts again and the server re-checks the payment.
      if (extractApiErrorCode(err) === "payment_required") {
        try {
          const res = await createCheckout({
            module: "assessment",
            item_id: aid,
            amount: assessment?.price ?? "0",
            description: `Assessment: ${assessment?.title ?? ""}`,
          });
          if (res.order) {
            // E-PLT-4: Razorpay is the active gateway — open its widget.
            const paid = await openRazorpayCheckout(res.order);
            if (paid) startSessionMutation.mutate();
            else toast.error("Payment not completed. Start again once it has cleared.");
            return;
          }
          if (res.checkout_url) {
            window.location.href = res.checkout_url;
            return;
          }
          if (res.status === "paid" || res.status === "free") {
            startSessionMutation.mutate();
            return;
          }
          toast.error(
            "Payment is pending confirmation. Please start again once it has cleared.",
          );
        } catch (e) {
          toast.error(extractApiError(e));
        }
        return;
      }
      toast.error(extractApiError(err));
    },
  });

  // Readiness check — fetches whether the assessment is ready to publish.
  // Only for draft assessments (published ones are already live).
  const { data: readiness } = useQuery({
    queryKey: ["assessment-readiness", aid],
    queryFn: () => getAssessmentReadiness(aid),
    enabled: !Number.isNaN(aid) && assessment?.status === "draft",
  });

  // Edit-assessment modal state. cj_admin can edit any assessment (including
  // published); other roles can only edit draft assessments (backend enforces).
  const [editModalOpen, setEditModalOpen] = useState(false);
  const assessmentUpdateMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateAssessment(aid, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", aid] });
      setEditModalOpen(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // ASM-2 (SRS §2.2/§2.3): a non-admin's edit/delete of a PUBLISHED assessment
  // is routed to an admin for approval; admins get an approve/decline queue.
  const isCjAdmin = user?.role === "cj_admin";
  const [requestChangeOpen, setRequestChangeOpen] = useState(false);
  const [requestDeleteOpen, setRequestDeleteOpen] = useState(false);

  const requestChangeMutation = useMutation({
    mutationFn: (payload: { title: string; reason: string }) =>
      requestAssessmentTitleChange(aid, payload.title, payload.reason),
    onSuccess: () => {
      toast.success("Change request submitted — an admin will review it.");
      setRequestChangeOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["assessment-mod-requests"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const requestDeleteMutation = useMutation({
    mutationFn: (reason: string) => deleteAssessment(aid, reason),
    onSuccess: () => {
      toast.success("Deletion request submitted — an admin will review it.");
      setRequestDeleteOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["assessment-mod-requests"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const modRequestsQuery = useQuery({
    queryKey: ["assessment-mod-requests"],
    queryFn: listModificationRequests,
    enabled: isCjAdmin,
  });
  const pendingRequests = (modRequestsQuery.data ?? []).filter(
    (r) => r.assessment === aid && r.status === "pending",
  );

  const reviewMutation = useMutation({
    mutationFn: (v: { id: number; approve: boolean }) =>
      v.approve ? approveModificationRequest(v.id) : declineModificationRequest(v.id),
    onSuccess: () => {
      toast.success("Request reviewed.");
      void queryClient.invalidateQueries({ queryKey: ["assessment-mod-requests"] });
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const sectionCreateMutation = useMutation({
    mutationFn: (payload: {
      title: string;
      parent?: number | null;
      description?: string;
      level?: number;
    }) => createSection(aid, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", aid] });
      setSectionModal({ open: false, parent: null, editSection: null });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const sectionUpdateMutation = useMutation({
    mutationFn: (payload: {
      sectionId: number;
      data: {
        title?: string;
        description?: string;
        duration_seconds?: number | null;
        delivery_count?: number | null;
        order_mode?: "STATIC" | "RANDOM";
        order?: number;
      };
    }) => updateSection(aid, payload.sectionId, payload.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", aid] });
      setSectionModal({ open: false, parent: null, editSection: null });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const sectionDeleteMutation = useMutation({
    mutationFn: (sectionId: number) => deleteSection(aid, sectionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments", aid] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", aid] });
      setSectionToDelete(null);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!assessment) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load assessment.</AlertDescription>
      </Alert>
    );
  }

  const a = assessment as AssessmentDetail;

  // canEdit: who can modify this assessment's structure (sections + questions)?
  // - Managers can edit DRAFT assessments
  // - cj_admin can also edit PUBLISHED assessments (admin override per SRS §2.2)
  // This single variable drives all section/question edit-button visibility.
  const canEdit = canManage && (a.status === "draft" || user?.role === "cj_admin");
  // ASM-2: a non-admin manager can't edit a published assessment directly, but
  // may request an admin-approved title change / deletion.
  const canRequestChange = canManage && a.status === "published" && !isCjAdmin;

  // Question count comes from the detail serializer's question_count
  // field (counts all assigned questions across all sections, including
  // nested subsections). This works for both draft AND published assessments.
  const questionCount = a.question_count ?? 0;
  // session_count comes from the detail serializer (added to include both
  // section_count + session_count on the detail endpoint). For candidates,
  // this shows the total sessions across ALL users; their own sessions
  // are in the My Sessions tab filtered to their account.
  const sessionCount = a.session_count ?? 0;

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link to="/assessments" className="text-sm text-primary-600 hover:underline">
          ← Back to Assessments
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">{a.title}</h1>
          <Badge variant={STATUS_VARIANTS[a.status] ?? "default"}>{a.status}</Badge>
          {a.total_duration_seconds && (
            <Badge variant="outline">{Math.floor(a.total_duration_seconds / 60)} min</Badge>
          )}
        </div>
        {a.objective && <p className="mt-1 text-sm text-slate-500">{a.objective}</p>}
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          {/* Sections tab: visible to managers (who can edit) and to
              candidates (read-only — just shows the variable structure,
              not question content). */}
          <TabsTrigger value="sections">Sections ({a.sections.length})</TabsTrigger>
          {/* Questions tab: MANAGERS ONLY. Candidates must NOT see the
              assigned questions before taking the assessment — showing
              question titles/content would let them preview the test. */}
          {canManage && <TabsTrigger value="questions">Questions ({questionCount})</TabsTrigger>}
          <TabsTrigger value="sessions">My Sessions ({sessionCount})</TabsTrigger>
        </TabsList>

        {/* === OVERVIEW TAB === */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Assessment Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Status
                  </dt>
                  <dd className="text-sm text-slate-900">{a.status}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Assessment Type
                  </dt>
                  <dd className="text-sm text-slate-900">
                    <Badge variant={a.assessment_type === "psychometric" ? "primary" : "default"}>
                      {a.assessment_type === "psychometric" ? "Psychometric" : "Normal"}
                    </Badge>
                    <span className="ml-2 text-xs text-slate-500">
                      {a.assessment_type === "psychometric"
                        ? "(Rating/Rank/Forced-Choice only)"
                        : "(MCQ/FITB/Match/Grid/Hotspot only)"}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Duration
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {a.total_duration_seconds
                      ? `${Math.floor(a.total_duration_seconds / 60)} minutes`
                      : "No time limit"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Navigation
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {NAVIGATION_RULES.find((n) => n.value === a.navigation_rule)?.label ??
                      a.navigation_rule}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Attempt Rule
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {ATTEMPT_RULES.find((r) => r.value === a.attempt_rule)?.label ?? a.attempt_rule}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Display Order
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {a.display_order === "RANDOM" ? "Random" : "Static (as configured)"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Timer Level
                  </dt>
                  <dd className="text-sm text-slate-900">{a.timer_level}</dd>
                </div>
              </dl>

              {a.instructions && (
                <div className="mt-4">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Instructions
                  </dt>
                  <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                    {a.instructions}
                  </dd>
                </div>
              )}

              {/* Readiness checklist — shows what's missing before publishing.
                  Only visible on draft assessments for managers. */}
              {a.status === "draft" && canManage && readiness && (
                <div
                  className={`mt-4 rounded-md border p-4 ${
                    readiness.ready
                      ? "border-green-200 bg-green-50"
                      : "border-amber-200 bg-amber-50"
                  }`}
                >
                  <p className="mb-2 text-sm font-semibold text-slate-900">
                    {readiness.ready
                      ? "✓ Ready to publish"
                      : "⚠ Complete the following before publishing:"}
                  </p>
                  <ul className="space-y-1 text-xs">
                    <li className={readiness.has_title ? "text-green-600" : "text-amber-700"}>
                      {readiness.has_title ? "✓" : "✗"} Title is set
                    </li>
                    <li
                      className={readiness.section_count > 0 ? "text-green-600" : "text-amber-700"}
                    >
                      {readiness.section_count > 0 ? "✓" : "✗"} At least 1 section created (
                      {readiness.section_count} current)
                    </li>
                    <li
                      className={readiness.question_count > 0 ? "text-green-600" : "text-amber-700"}
                    >
                      {readiness.question_count > 0 ? "✓" : "✗"} At least 1 question assigned (
                      {readiness.question_count} current)
                    </li>
                    {readiness.errors.length > 0 &&
                      readiness.errors.map((err: string, i: number) => (
                        <li key={i} className="text-amber-700">
                          ✗ {err}
                        </li>
                      ))}
                  </ul>
                </div>
              )}

              <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                {/* Edit button — cj_admin can edit any assessment (including
                    published per SRS §2.2 admin-approval path); other roles
                    can only edit draft assessments. */}
                {canEdit && (
                  <Button variant="outline" onClick={() => setEditModalOpen(true)}>
                    Edit Assessment
                  </Button>
                )}
                {canRequestChange && (
                  <>
                    <Button variant="outline" onClick={() => setRequestChangeOpen(true)}>
                      Request Title Change
                    </Button>
                    <Button
                      variant="outline"
                      className="text-danger hover:bg-danger-50"
                      onClick={() => setRequestDeleteOpen(true)}
                    >
                      Request Deletion
                    </Button>
                  </>
                )}
                {a.status === "draft" && canManage && (
                  <Button
                    loading={publishMutation.isPending}
                    disabled={readiness && !readiness.ready}
                    title={
                      readiness && !readiness.ready
                        ? readiness.errors.join("\n")
                        : "Publish this assessment so candidates can take it"
                    }
                    onClick={() => publishMutation.mutate()}
                  >
                    Publish Assessment
                  </Button>
                )}
                {a.status === "published" && canEdit && (
                  <Button
                    variant="outline"
                    loading={unpublishMutation.isPending}
                    title="Return this assessment to draft to edit it (E-ASM-11)"
                    onClick={() => unpublishMutation.mutate()}
                  >
                    Return to draft
                  </Button>
                )}
                {a.status === "published" && (
                  <div className="flex flex-col items-end gap-1">
                    {Number(a.price) > 0 && (
                      <span className="text-xs text-slate-500">
                        Paid assessment — {a.price} due before you start
                      </span>
                    )}
                    <Button
                      loading={startSessionMutation.isPending}
                      onClick={() => startSessionMutation.mutate()}
                    >
                      {Number(a.price) > 0 ? `Pay & Start (${a.price})` : "Start Session"}
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* ASM-2: admin approve/decline queue for pending title-change /
              deletion requests on this assessment. */}
          {isCjAdmin && pendingRequests.length > 0 && (
            <Card className="mt-4 border-amber-200">
              <CardHeader>
                <CardTitle>Pending change requests ({pendingRequests.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {pendingRequests.map((r) => (
                    <li
                      key={r.id}
                      className="flex flex-wrap items-start justify-between gap-3 rounded-md border border-slate-200 p-3"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900">
                          {r.action === "delete"
                            ? "Delete this assessment"
                            : `Rename to "${r.proposed_title ?? ""}"`}
                        </p>
                        <p className="text-xs text-slate-500">
                          Requested by {r.requester_name ?? "a user"} — {r.reason}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          loading={reviewMutation.isPending}
                          onClick={() => reviewMutation.mutate({ id: r.id, approve: true })}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => reviewMutation.mutate({ id: r.id, approve: false })}
                        >
                          Decline
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* === SECTIONS TAB === */}
        <TabsContent value="sections">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Sections (Variable Structure)</CardTitle>
                {canEdit && (
                  <Button
                    size="sm"
                    onClick={() => setSectionModal({ open: true, parent: null, editSection: null })}
                  >
                    + Add Section
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {a.sections.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-500">
                  No sections yet. Add a section to start building the variable structure.
                </p>
              ) : (
                <div className="space-y-1">
                  {a.sections.map((s) => (
                    <SectionTreeRow
                      key={s.id}
                      section={s}
                      depth={0}
                      canManage={canEdit}
                      onAddSubsection={(parentId) =>
                        setSectionModal({ open: true, parent: parentId, editSection: null })
                      }
                      onEditSection={(section) =>
                        setSectionModal({ open: true, parent: null, editSection: section })
                      }
                      onDeleteSection={(section) => setSectionToDelete(section)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === QUESTIONS TAB === */}
        <TabsContent value="questions">
          <QuestionAssignmentTab
            assessmentId={aid}
            assessmentType={a.assessment_type}
            sections={a.sections}
            canManage={canEdit}
          />
        </TabsContent>

        {/* === SESSIONS TAB === */}
        {/* === SESSIONS TAB (My Sessions) === */}
        <TabsContent value="sessions">
          <MySessionsTab
            assessmentId={aid}
            assessmentStatus={a.status}
            canStartSession={a.status === "published"}
            onStartSession={() => startSessionMutation.mutate()}
            startingSession={startSessionMutation.isPending}
          />
        </TabsContent>
      </Tabs>

      <CreateSectionModal
        open={sectionModal.open}
        parentId={sectionModal.parent}
        editSection={sectionModal.editSection}
        loading={sectionCreateMutation.isPending || sectionUpdateMutation.isPending}
        onClose={() => setSectionModal({ open: false, parent: null, editSection: null })}
        onSubmit={(payload) => {
          if (sectionModal.editSection) {
            // Edit mode — PATCH the existing section
            sectionUpdateMutation.mutate({
              sectionId: sectionModal.editSection.id,
              data: {
                title: payload.title,
                description: payload.description,
                // ASM-3: per-section timer duration; ASM-1: delivery count;
                // ASM-5: per-section delivery order mode.
                duration_seconds: payload.duration_seconds ?? null,
                delivery_count: payload.delivery_count ?? null,
                order_mode: payload.order_mode,
              },
            });
          } else {
            // Create mode
            sectionCreateMutation.mutate(payload);
          }
        }}
      />

      {/* Delete confirmation modal */}
      <Modal
        open={sectionToDelete !== null}
        onClose={() => setSectionToDelete(null)}
        title="Delete section"
        size="sm"
      >
        <p className="text-sm text-slate-700">
          Delete <strong>{sectionToDelete?.title}</strong>? This will also delete all sub-sections
          and any questions assigned to them. This cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setSectionToDelete(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            loading={sectionDeleteMutation.isPending}
            onClick={() => {
              if (sectionToDelete) sectionDeleteMutation.mutate(sectionToDelete.id);
            }}
          >
            Delete
          </Button>
        </div>
      </Modal>

      <EditAssessmentModal
        open={editModalOpen}
        assessment={a}
        loading={assessmentUpdateMutation.isPending}
        onClose={() => setEditModalOpen(false)}
        onSubmit={(payload) => assessmentUpdateMutation.mutate(payload)}
      />
      <RequestChangeModal
        open={requestChangeOpen}
        currentTitle={a.title}
        loading={requestChangeMutation.isPending}
        onClose={() => setRequestChangeOpen(false)}
        onSubmit={(title, reason) => requestChangeMutation.mutate({ title, reason })}
      />
      <RequestDeleteModal
        open={requestDeleteOpen}
        loading={requestDeleteMutation.isPending}
        onClose={() => setRequestDeleteOpen(false)}
        onSubmit={(reason) => requestDeleteMutation.mutate(reason)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Question Assignment Tab
// ---------------------------------------------------------------------------

function QuestionAssignmentTab({
  assessmentId,
  assessmentType,
  sections,
  canManage,
}: {
  assessmentId: number;
  assessmentType: "normal" | "psychometric";
  sections: AssessmentSection[];
  canManage: boolean;
}) {
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(
    sections.length > 0 ? sections[0].id : null,
  );
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  // ASM-9: preview a bank question in full before selecting it.
  const [previewId, setPreviewId] = useState<number | null>(null);
  const toast = useToast();
  const queryClient = useQueryClient();

  // Flatten sections for the dropdown (show level + title)
  const flatSections: { id: number; label: string }[] = [];
  const flatten = (secs: AssessmentSection[], depth: number) => {
    for (const s of secs) {
      flatSections.push({
        id: s.id,
        label: `${"  ".repeat(depth)}L${s.level}: ${s.title}`,
      });
      if (s.subsections) flatten(s.subsections, depth + 1);
    }
  };
  flatten(sections, 0);

  // Load assigned questions for the selected section
  const { data: assignedQuestions, isLoading: assignedLoading } = useQuery({
    queryKey: ["assessment-section-questions", assessmentId, selectedSectionId],
    queryFn: () =>
      selectedSectionId
        ? listSectionQuestions(assessmentId, selectedSectionId)
        : Promise.resolve([]),
    enabled: Boolean(selectedSectionId),
  });

  // Load question bank questions for browsing. We fetch ALL confirmed
  // questions (no type filter at the API level when the dropdown is on
  // "All matching types") and then filter client-side by assessment type
  // using the is_psychometric field — this is the critical guard that
  // prevents a psychometric question from showing up in a normal
  // assessment's browser (and vice versa). The backend still rejects
  // mismatched assignments as defense-in-depth, but the UI must never
  // offer the user a question they can't attach.
  const { data: bankData, isLoading: bankLoading } = useQuery({
    queryKey: ["question-bank", "for-assignment", search, typeFilter],
    queryFn: () =>
      listQuestions({
        ...(search ? { search } : {}),
        ...(typeFilter ? { question_type: typeFilter } : {}),
        status: "confirmed",
      }),
  });

  // Client-side filter: only show questions whose category matches the
  // assessment type. is_psychometric comes from the backend
  // (Question.is_psychometric property → QuestionListSerializer).
  const wantPsychometric = assessmentType === "psychometric";
  const bankQuestions = (bankData?.results ?? []).filter(
    (q) => q.is_psychometric === wantPsychometric,
  );

  const assignMutation = useMutation({
    mutationFn: (questionId: number) =>
      assignQuestion(assessmentId, selectedSectionId!, { question: questionId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["assessment-section-questions", assessmentId, selectedSectionId],
      });
      // Also refresh readiness + assessment detail so the Overview tab
      // validation errors update immediately (Issue 5).
      void queryClient.invalidateQueries({ queryKey: ["assessments", assessmentId] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", assessmentId] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const removeMutation = useMutation({
    mutationFn: (qId: number) => removeQuestion(assessmentId, selectedSectionId!, qId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["assessment-section-questions", assessmentId, selectedSectionId],
      });
      // Also refresh readiness + assessment detail (Issue 5).
      void queryClient.invalidateQueries({ queryKey: ["assessments", assessmentId] });
      void queryClient.invalidateQueries({ queryKey: ["assessment-readiness", assessmentId] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // ASM-7: set a per-assessment score override on an assigned question.
  const scoreMutation = useMutation({
    mutationFn: (v: { aqId: number; score_override: number | null }) =>
      updateAssignedQuestion(assessmentId, selectedSectionId!, v.aqId, {
        score_override: v.score_override,
      }),
    onSuccess: () => {
      toast.success("Score updated.");
      void queryClient.invalidateQueries({
        queryKey: ["assessment-section-questions", assessmentId, selectedSectionId],
      });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const assignedIds = new Set((assignedQuestions ?? []).map((q) => q.question));

  if (sections.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="py-8 text-center text-sm text-slate-500">
            Create sections first before assigning questions.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Section selector */}
      <Card>
        <CardHeader>
          <CardTitle>Assign Questions to Sections</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <Label htmlFor="section-select">Select section</Label>
            <select
              id="section-select"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={selectedSectionId ?? ""}
              onChange={(e) => setSelectedSectionId(Number(e.target.value))}
            >
              {flatSections.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Assigned questions */}
          <div className="mb-6">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Assigned Questions ({assignedQuestions?.length ?? 0})
            </p>
            {assignedLoading ? (
              <Spinner size="sm" />
            ) : (assignedQuestions?.length ?? 0) === 0 ? (
              <p className="rounded-md border border-dashed border-slate-200 py-4 text-center text-xs text-slate-400">
                No questions assigned to this section yet.
              </p>
            ) : (
              <div className="space-y-1">
                {assignedQuestions?.map((aq) => (
                  <div
                    key={aq.id}
                    className="flex items-center gap-2 rounded-md border border-slate-200 p-2 text-xs"
                  >
                    <Badge variant="outline">
                      {aq.question_detail?.question_type_label ?? "Q"}
                    </Badge>
                    <span className="flex-1 truncate text-slate-700">
                      {aq.question_detail?.question_title ?? `Question #${aq.question}`}
                    </span>
                    {aq.question_detail?.difficulty_level && (
                      <span className="text-slate-400">{aq.question_detail.difficulty_level}</span>
                    )}
                    {canManage && (
                      <label
                        className="flex items-center gap-1 text-slate-400"
                        title="Per-assessment score override — leave blank to use the question's own score (SRS §4)"
                      >
                        Score
                        <input
                          type="number"
                          min={0}
                          step="0.5"
                          defaultValue={aq.score_override ?? ""}
                          className="w-14 rounded border border-slate-200 px-1.5 py-0.5 text-xs"
                          onBlur={(e) => {
                            const raw = e.target.value.trim();
                            const val = raw === "" ? null : Number(raw);
                            if (val !== (aq.score_override ?? null)) {
                              scoreMutation.mutate({ aqId: aq.id, score_override: val });
                            }
                          }}
                        />
                      </label>
                    )}
                    {canManage && (
                      <button
                        onClick={() => removeMutation.mutate(aq.id)}
                        className="rounded px-2 py-0.5 text-danger hover:bg-danger-50"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Question bank browser */}
          {canManage && (
            <div>
              <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                This is a{" "}
                <strong>{assessmentType === "psychometric" ? "psychometric" : "normal"}</strong>{" "}
                assessment — only{" "}
                {assessmentType === "psychometric"
                  ? "Rating / Rank / Rank-then-Rate / Forced-Choice"
                  : "MCQ / FITB / Match / Grid / Hotspot"}{" "}
                questions can be attached. The backend will reject mismatched assignments.
              </div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Question Bank (confirmed questions only)
              </p>
              <div className="mb-3 flex gap-2">
                <Input
                  type="search"
                  placeholder="Search questions..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="max-w-xs text-sm"
                />
                <select
                  className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                >
                  <option value="">All matching types</option>
                  {(assessmentType === "psychometric"
                    ? PSYCHOMETRIC_QUESTION_TYPES_LIST
                    : NORMAL_QUESTION_TYPES
                  ).map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              {bankLoading ? (
                <Spinner size="sm" />
              ) : bankQuestions.length === 0 ? (
                <div className="py-4 text-center text-xs text-slate-400">
                  <p>
                    No confirmed {assessmentType === "psychometric" ? "psychometric" : "normal"}{" "}
                    questions found. Create and confirm questions in the Question Bank first.
                  </p>
                  {(() => {
                    const total = bankData?.results.length ?? 0;
                    const hidden = total - bankQuestions.length;
                    if (hidden > 0) {
                      return (
                        <p className="mt-1 text-amber-600">
                          {hidden} question{hidden === 1 ? "" : "s"} hidden — wrong category for
                          this {assessmentType} assessment.
                        </p>
                      );
                    }
                    return null;
                  })()}
                </div>
              ) : (
                <div className="max-h-96 space-y-1 overflow-y-auto">
                  {bankQuestions.map((q) => {
                    const isAssigned = assignedIds.has(q.id);
                    return (
                      <div
                        key={q.id}
                        className={`flex items-center gap-2 rounded-md border p-2 text-xs ${
                          isAssigned
                            ? "border-green-200 bg-green-50"
                            : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <Badge variant="outline">{q.question_type_label}</Badge>
                        <span className="flex-1 truncate text-slate-700">
                          {q.question_title || stripHtml(q.question_text_1) || "(untitled)"}
                        </span>
                        {q.difficulty_level && (
                          <span className="text-slate-400">{q.difficulty_level}</span>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => setPreviewId(q.id)}>
                          Preview
                        </Button>
                        {isAssigned ? (
                          <span className="text-green-600">✓ Assigned</span>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            loading={assignMutation.isPending}
                            onClick={() => assignMutation.mutate(q.id)}
                          >
                            + Assign
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {previewId !== null && (
        <QuestionPreviewModal
          questionId={previewId}
          alreadyAssigned={assignedIds.has(previewId)}
          canManage={canManage}
          loading={assignMutation.isPending}
          onClose={() => setPreviewId(null)}
          onSelect={() => {
            assignMutation.mutate(previewId);
            setPreviewId(null);
          }}
        />
      )}
    </div>
  );
}

function QuestionPreviewModal({
  questionId,
  alreadyAssigned,
  canManage,
  loading,
  onClose,
  onSelect,
}: {
  questionId: number;
  alreadyAssigned: boolean;
  canManage: boolean;
  loading: boolean;
  onClose: () => void;
  onSelect: () => void;
}) {
  const { data: q, isLoading } = useQuery({
    queryKey: ["question-detail-preview", questionId],
    queryFn: () => retrieveQuestion(questionId),
  });
  return (
    <Modal
      open
      onClose={onClose}
      title="Question preview"
      description="Review the full question before selecting it (SRS §4.1)."
      size="lg"
    >
      {isLoading || !q ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{q.question_type_label}</Badge>
            {q.difficulty_level && <Badge variant="outline">{q.difficulty_level}</Badge>}
            {q.cognitive_level && <Badge variant="outline">{q.cognitive_level}</Badge>}
            <Badge variant="outline">{q.status_label}</Badge>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Question</p>
            <p className="text-slate-700">{stripHtml(q.question_text_1) || "(no text)"}</p>
          </div>
          {q.worked_solution && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Worked solution
              </p>
              <p className="text-slate-700">{stripHtml(q.worked_solution)}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500">
            <span>Discrimination: {q.discrimination_index ?? "—"}</span>
            <span>Item difficulty: {q.item_difficulty_index ?? "—"}</span>
            <span>Item-total r: {q.item_total_correlation ?? "—"}</span>
            <span>Exposure limit: {q.exposure_limit ?? "—"}</span>
          </div>
        </div>
      )}
      <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        {canManage && !alreadyAssigned && (
          <Button type="button" loading={loading} onClick={onSelect}>
            Select
          </Button>
        )}
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Section tree row (recursive)
// ---------------------------------------------------------------------------

function SectionTreeRow({
  section,
  depth,
  canManage,
  onAddSubsection,
  onEditSection,
  onDeleteSection,
}: {
  section: AssessmentSection;
  depth: number;
  canManage: boolean;
  onAddSubsection: (parentId: number) => void;
  onEditSection: (section: AssessmentSection) => void;
  onDeleteSection: (section: AssessmentSection) => void;
}) {
  return (
    <>
      <div
        className="flex items-center justify-between rounded-md py-2 pr-2 hover:bg-slate-50"
        style={{ paddingLeft: `${depth * 1.5 + 0.5}rem` }}
      >
        <div className="flex items-center gap-2">
          <Badge variant="outline">L{section.level}</Badge>
          <span className="text-sm font-medium text-slate-900">{section.title}</span>
          {section.duration_seconds && (
            <span className="text-xs text-slate-400">
              · {Math.floor(section.duration_seconds / 60)} min
            </span>
          )}
          {section.delivery_count != null && (
            <span className="text-xs text-slate-400">· deliver {section.delivery_count}</span>
          )}
        </div>
        {canManage && (
          <div className="flex items-center gap-1">
            {depth < 3 && (
              <Button variant="ghost" size="sm" onClick={() => onAddSubsection(section.id)}>
                + Sub-section
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={() => onEditSection(section)}>
              Edit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-danger hover:bg-danger-50"
              onClick={() => onDeleteSection(section)}
            >
              Delete
            </Button>
          </div>
        )}
      </div>
      {section.subsections &&
        section.subsections.map((child) => (
          <SectionTreeRow
            key={child.id}
            section={child}
            depth={depth + 1}
            canManage={canManage}
            onAddSubsection={onAddSubsection}
            onEditSection={onEditSection}
            onDeleteSection={onDeleteSection}
          />
        ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Create / Edit Section Modal
// ---------------------------------------------------------------------------

function CreateSectionModal({
  open,
  parentId,
  editSection,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  parentId: number | null;
  /** When set, the modal is in edit-mode (pre-populated with this section). */
  editSection: AssessmentSection | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    parent?: number | null;
    description?: string;
    level?: number;
    duration_seconds?: number | null;
    delivery_count?: number | null;
    order_mode?: "STATIC" | "RANDOM";
  }) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  // ASM-3 per-section timer (entered in minutes) + ASM-1 delivery count +
  // ASM-5 per-section delivery order mode.
  const [durationMin, setDurationMin] = useState("");
  const [deliveryCount, setDeliveryCount] = useState("");
  const [orderMode, setOrderMode] = useState<"STATIC" | "RANDOM">("STATIC");

  // Sync form fields when the modal opens (create or edit).
  // useEffect deps: [open, editSection] — runs when the modal opens or when
  // the edit target changes.
  useEffect(() => {
    if (!open) return;
    setTitle(editSection?.title ?? "");
    setDescription(editSection?.description ?? "");
    setDurationMin(
      editSection?.duration_seconds ? String(Math.round(editSection.duration_seconds / 60)) : "",
    );
    setDeliveryCount(editSection?.delivery_count != null ? String(editSection.delivery_count) : "");
    setOrderMode(editSection?.order_mode ?? "STATIC");
  }, [open, editSection]);

  const isEdit = editSection !== null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit Section" : parentId ? "Add Sub-Section" : "Add Section"}
      description={
        isEdit
          ? "Update this section's title and description."
          : parentId
            ? "Create a sub-section within the selected section."
            : "Create a top-level section (Level 1 variable)."
      }
      size="md"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({
            title,
            parent: parentId,
            description,
            // ASM-4: the server derives level from the parent (parent.level + 1),
            // so Level 3/4 sub-sections are created correctly.
            duration_seconds: durationMin.trim() ? Number(durationMin) * 60 : null,
            delivery_count: deliveryCount.trim() ? Number(deliveryCount) : null,
            order_mode: orderMode,
          });
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="sec-title" required>
            Section title
          </Label>
          <Input
            id="sec-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Quantitative Aptitude"
            required
          />
        </div>
        <div>
          <Label htmlFor="sec-desc">Description (optional)</Label>
          <textarea
            id="sec-desc"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What this section covers..."
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="sec-timer">Timer (minutes, optional)</Label>
            <Input
              id="sec-timer"
              type="number"
              min={0}
              value={durationMin}
              onChange={(e) => setDurationMin(e.target.value)}
              placeholder="e.g. 15"
            />
            <p className="mt-1 text-xs text-slate-500">
              Per-section time limit (SRS §5.2). Used when the assessment timer level is a section
              level.
            </p>
          </div>
          <div>
            <Label htmlFor="sec-delivery">Delivery count (optional)</Label>
            <Input
              id="sec-delivery"
              type="number"
              min={0}
              value={deliveryCount}
              onChange={(e) => setDeliveryCount(e.target.value)}
              placeholder="e.g. 10"
            />
            <p className="mt-1 text-xs text-slate-500">
              Randomly deliver this many questions from the pool (SRS §4.1.1). Blank = deliver all.
            </p>
          </div>
          <div>
            <Label htmlFor="sec-order">Question order</Label>
            <select
              id="sec-order"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={orderMode}
              onChange={(e) => setOrderMode(e.target.value as "STATIC" | "RANDOM")}
            >
              <option value="STATIC">Static (as configured)</option>
              <option value="RANDOM">Random</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Delivery order of this section's questions (SRS §5.1).
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            {isEdit ? "Save changes" : "Create section"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// ASM-2: Request-change / request-delete modals (published assessments)
// ---------------------------------------------------------------------------

function RequestChangeModal({
  open,
  currentTitle,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  currentTitle: string;
  loading: boolean;
  onClose: () => void;
  onSubmit: (title: string, reason: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [reason, setReason] = useState("");
  useEffect(() => {
    if (!open) return;
    setTitle(currentTitle);
    setReason("");
  }, [open, currentTitle]);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Request title change"
      description="This assessment is published, so a title change needs admin approval (SRS §2.2)."
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(title, reason);
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="rc-title" required>
            New title
          </Label>
          <Input id="rc-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>
        <div>
          <Label htmlFor="rc-reason" required>
            Reason
          </Label>
          <textarea
            id="rc-reason"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading} disabled={!title.trim() || !reason.trim()}>
            Submit request
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RequestDeleteModal({
  open,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  useEffect(() => {
    if (open) setReason("");
  }, [open]);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Request deletion"
      description="This assessment is published, so deletion needs admin approval (SRS §2.3)."
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(reason);
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="rd-reason" required>
            Reason
          </Label>
          <textarea
            id="rd-reason"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading} disabled={!reason.trim()}>
            Submit request
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Edit Assessment Modal
// ---------------------------------------------------------------------------

function EditAssessmentModal({
  open,
  assessment,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  assessment: AssessmentDetail;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  // Local form state — initialised from the assessment on open.
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [instructions, setInstructions] = useState("");
  const [duration, setDuration] = useState("");
  const [navigationRule, setNavigationRule] = useState("FREE");
  const [attemptRule, setAttemptRule] = useState("SINGLE_SESSION");
  const [displayOrder, setDisplayOrder] = useState<"STATIC" | "RANDOM">("STATIC");
  const [timerLevel, setTimerLevel] = useState("assessment");
  const [price, setPrice] = useState("0");

  // Sync form fields when the modal opens.
  useEffect(() => {
    if (!open) return;
    setTitle(assessment.title ?? "");
    setObjective(assessment.objective ?? "");
    setInstructions(assessment.instructions ?? "");
    // Backend stores seconds; the form shows minutes.
    const minutes = assessment.total_duration_seconds
      ? Math.round(assessment.total_duration_seconds / 60)
      : 0;
    setDuration(minutes > 0 ? String(minutes) : "");
    setNavigationRule(assessment.navigation_rule ?? "FREE");
    setAttemptRule(assessment.attempt_rule ?? "SINGLE_SESSION");
    setDisplayOrder((assessment.display_order as "STATIC" | "RANDOM") ?? "STATIC");
    setTimerLevel(assessment.timer_level ?? "assessment");
    setPrice(assessment.price ?? "0");
  }, [open, assessment]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit Assessment"
      description="Update assessment configuration. cj_admin can edit published assessments."
      size="lg"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          // Convert minutes (form input) → seconds (backend storage).
          const durationMinutes = duration ? parseInt(duration, 10) : null;
          onSubmit({
            title,
            objective,
            instructions,
            total_duration_seconds: durationMinutes !== null ? durationMinutes * 60 : null,
            navigation_rule: navigationRule,
            attempt_rule: attemptRule,
            display_order: displayOrder,
            timer_level: timerLevel,
            price: price.trim() === "" ? "0" : price,
          });
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="edit-title" required>
            Assessment title
          </Label>
          <Input
            id="edit-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="edit-objective">Objective</Label>
          <textarea
            id="edit-objective"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="edit-instructions">Instructions (shown to candidates)</Label>
          <textarea
            id="edit-instructions"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <Label htmlFor="edit-duration">Duration (minutes)</Label>
            <Input
              id="edit-duration"
              type="number"
              min="1"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="Leave empty for no time limit"
            />
          </div>
          <div>
            <Label htmlFor="edit-price">Price (0 = free)</Label>
            <Input
              id="edit-price"
              type="number"
              min="0"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
            />
          </div>
          <div>
            <Label htmlFor="edit-nav">Navigation</Label>
            <select
              id="edit-nav"
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
            <Label htmlFor="edit-attempt">Attempt rule</Label>
            <select
              id="edit-attempt"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={attemptRule}
              onChange={(e) => setAttemptRule(e.target.value)}
            >
              {ATTEMPT_RULES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="edit-display-order">Display order</Label>
            <select
              id="edit-display-order"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={displayOrder}
              onChange={(e) => setDisplayOrder(e.target.value as "STATIC" | "RANDOM")}
            >
              <option value="STATIC">Static (as configured)</option>
              <option value="RANDOM">Random</option>
            </select>
          </div>
          <div>
            <Label htmlFor="edit-timer-level">Timer level</Label>
            <select
              id="edit-timer-level"
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
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Save changes
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// My Sessions Tab — shows the current user's sessions for this assessment
// ---------------------------------------------------------------------------

function MySessionsTab({
  assessmentId,
  assessmentStatus,
  canStartSession,
  onStartSession,
  startingSession,
}: {
  assessmentId: number;
  assessmentStatus: string;
  canStartSession: boolean;
  onStartSession: () => void;
  startingSession: boolean;
}) {
  const navigate = useNavigate();
  const { data: allMySessions, isLoading } = useQuery({
    queryKey: ["my-sessions", assessmentId],
    queryFn: () => listMySessions(),
  });

  // Filter to only this assessment's sessions
  const mySessions = (allMySessions ?? []).filter((s) => s.assessment === assessmentId);

  const formatDate = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>My Sessions</CardTitle>
          {canStartSession && (
            <Button loading={startingSession} onClick={onStartSession}>
              Start New Session
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {mySessions.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            {assessmentStatus === "published"
              ? 'You have not taken this assessment yet. Click "Start New Session" to begin.'
              : "This assessment is not yet published."}
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Percentage</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mySessions.map((s: AssessmentSession, idx: number) => {
                const completedSessions = mySessions.filter(
                  (x: AssessmentSession) => x.status === "completed",
                );
                const bestPercentage = Math.max(
                  ...completedSessions.map((x: AssessmentSession) => x.percentage ?? 0),
                );
                const isBest =
                  s.status === "completed" && s.percentage === bestPercentage && bestPercentage > 0;
                return (
                  <TableRow key={s.id} className={isBest ? "bg-green-50" : ""}>
                    <TableCell className="text-slate-500">
                      Attempt {idx + 1}
                      {isBest && <span className="ml-1 text-xs text-green-600">★ Best</span>}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          s.status === "completed"
                            ? "success"
                            : s.status === "active"
                              ? "primary"
                              : s.status === "suspended"
                                ? "warning"
                                : "default"
                        }
                      >
                        {s.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {formatDate(s.started_at)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {formatDate(s.completed_at)}
                    </TableCell>
                    <TableCell className="text-slate-700">
                      {s.total_score !== null ? s.total_score.toFixed(1) : "—"}
                      {s.max_score !== null && (
                        <span className="text-slate-400"> / {s.max_score.toFixed(1)}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {s.percentage !== null ? (
                        <Badge variant={s.percentage >= 40 ? "success" : "warning"}>
                          {s.percentage.toFixed(1)}%
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        {(s.status === "active" || s.status === "suspended") && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/assessments/sessions/${s.id}`)}
                          >
                            Resume
                          </Button>
                        )}
                        {s.status === "completed" && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/assessments/sessions/${s.id}/results`)}
                          >
                            View Results
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
