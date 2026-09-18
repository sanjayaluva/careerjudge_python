/**
 * Training Course Detail Page — view course structure + register.
 *
 * Tabs:
 * - Overview: course properties + publish button (trainer)
 * - Structure: lessons → topics → sessions → contents/assignments (read-only tree)
 * - Live Sessions: scheduled online/offline sessions
 * - Assessments: linked assessments at various levels
 * - Registrations: trainer views student registrations
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

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
  useToast,
} from "@/components/ui";
import {
  addCourseAssessment,
  addLiveSession,
  COURSE_TYPES,
  createZoomMeeting,
  deleteCourseAssessment,
  deleteLiveSession,
  getZoomConfig,
  listCompletionParameters,
  listCourseRegistrations,
  listCourseUpdateRequests,
  approveCourseUpdateRequest,
  declineCourseUpdateRequest,
  listMyCourses,
  notifyLiveSessionStudents,
  listLiveSessionConsents,
  listAssignmentReports,
  reviewAssignmentReport,
  listMessages,
  sendMessage,
  type AssignmentReport,
  publishCourse,
  registerForCourse,
  requestCourseUpdate,
  rescheduleLiveSession,
  retrieveCourse,
  SCHEDULE_TYPES,
  setCompletionParameters,
  type CompletionParameter,
  type CourseUpdateRequest,
  type TrainingCourse,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { listAssessments } from "@/api/assessment";
import { createCheckout } from "@/api/payments";
import { useAuth } from "@/hooks/useAuth";
import { LiveSessionConsentModal } from "./LiveSessionConsentModal";
import { CourseStructureEditor } from "./CourseStructureEditor";
import { CoursePlayer } from "./CoursePlayer";

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function TrainingCourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const cid = Number(id);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const canManage = ["cj_admin", "trainer"].includes(user?.role ?? "");
  const [searchParams, setSearchParams] = useSearchParams();

  const { data: course, isLoading } = useQuery({
    queryKey: ["training", "courses", cid],
    queryFn: () => retrieveCourse(cid),
    enabled: !Number.isNaN(cid),
  });

  // Live session consent modal — shown when ?live_session=ID is in the URL
  const liveSessionId = searchParams.get("live_session");
  const consentLiveSession = liveSessionId
    ? course?.live_sessions.find((ls) => ls.id === Number(liveSessionId))
    : null;

  const notifyMutation = useMutation({
    mutationFn: (lsId: number) => notifyLiveSessionStudents(lsId),
    onSuccess: (data) => {
      toast.success(`Notified ${data.notified_count} student(s).`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Student's registration for this course (to show correct button state)
  const { data: myCourses } = useQuery({
    queryKey: ["training", "my-courses"],
    queryFn: () => listMyCourses(),
    enabled: !canManage,
  });
  const myRegistration = myCourses?.find((r) => r.course === cid);

  const publishMutation = useMutation({
    mutationFn: () => publishCourse(cid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", cid] });
      toast.success("Course published.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const registerMutation = useMutation({
    mutationFn: async () => {
      // Step 1: Register for the course
      const reg = await registerForCourse(cid);
      // Step 2: Handle payment (free auto-pays, paid goes to Stripe)
      if (course && parseFloat(course.price) > 0) {
        const checkout = await createCheckout({
          module: "training",
          item_id: cid,
          amount: course.price,
          description: `Course: ${course.title}`,
        });
        if (checkout.checkout_url) {
          // Redirect to Stripe Checkout
          window.location.href = checkout.checkout_url;
          return reg;
        }
      }
      return reg;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["training", "my-courses"] });
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success(
        data.payment_status === "paid"
          ? "Registered! You can start the course now."
          : "Registered for course. Payment pending.",
      );
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
  if (!course) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load course.</AlertDescription>
      </Alert>
    );
  }

  const typeLabel =
    COURSE_TYPES.find((t) => t.value === course.course_type)?.label ?? course.course_type;
  const scheduleLabel =
    SCHEDULE_TYPES.find((s) => s.value === course.schedule_type)?.label ?? course.schedule_type;

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link to="/training" className="text-sm text-primary-600 hover:underline">
          ← Back to Training
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">{course.title}</h1>
          <Badge variant="outline">{typeLabel}</Badge>
          <Badge variant="outline">{scheduleLabel}</Badge>
          <Badge variant={STATUS_VARIANTS[course.status] ?? "default"}>{course.status}</Badge>
          {course.category_name && <Badge variant="outline">{course.category_name}</Badge>}
        </div>
        {course.objective && (
          <p className="mt-2 max-w-3xl text-sm text-slate-600">{course.objective}</p>
        )}
      </div>

      <Tabs defaultValue={myRegistration ? "learn" : "overview"}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          {!canManage && <TabsTrigger value="learn">📖 Learn</TabsTrigger>}
          <TabsTrigger value="structure">Structure ({course.lessons.length} lessons)</TabsTrigger>
          <TabsTrigger value="live-sessions">
            Live Sessions ({course.live_sessions.length})
          </TabsTrigger>
          <TabsTrigger value="assessments">Assessments ({course.assessments.length})</TabsTrigger>
          {canManage && <TabsTrigger value="completion">Completion</TabsTrigger>}
          {canManage && <TabsTrigger value="registrations">Registrations</TabsTrigger>}
          {canManage && <TabsTrigger value="update-requests">Update Requests</TabsTrigger>}
        </TabsList>

        {/* === OVERVIEW TAB === */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Course Properties</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2">
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Price
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">${course.price}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Duration
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">
                    {course.duration_days ? `${course.duration_days} days` : "Self-paced"}
                  </dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created by
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{course.created_by_name ?? "—"}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Registrations
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{course.registration_count}</dd>
                </div>
              </dl>

              {course.description && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Description
                  </div>
                  <p className="mt-1 text-sm text-slate-900">{course.description}</p>
                </div>
              )}

              <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-4">
                {canManage && (
                  <Link to={`/training/${cid}/edit`}>
                    <Button variant="outline">Edit course</Button>
                  </Link>
                )}
                {canManage && course.status === "draft" && (
                  <Button
                    onClick={() => publishMutation.mutate()}
                    loading={publishMutation.isPending}
                  >
                    Publish course
                  </Button>
                )}
                {!canManage && course.status === "published" && !myRegistration && (
                  <Button
                    onClick={() => registerMutation.mutate()}
                    loading={registerMutation.isPending}
                  >
                    {parseFloat(course.price) === 0
                      ? "Enroll for free"
                      : `Register for $${course.price}`}
                  </Button>
                )}
                {!canManage && myRegistration && (
                  <Badge variant={myRegistration.payment_status === "paid" ? "success" : "warning"}>
                    {myRegistration.payment_status === "paid" ? "✓ Enrolled" : "Payment pending"}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* === LEARN TAB (students only — course delivery player) === */}
        {!canManage && (
          <TabsContent value="learn">
            <CoursePlayer course={course} />
          </TabsContent>
        )}

        {/* === STRUCTURE TAB === */}
        <TabsContent value="structure">
          <Card>
            <CardHeader>
              <CardTitle>Course Structure</CardTitle>
            </CardHeader>
            <CardContent>
              <CourseStructureEditor
                courseId={cid}
                lessons={course.lessons}
                canManage={canManage}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* === LIVE SESSIONS TAB === */}
        <TabsContent value="live-sessions">
          <Card>
            <CardHeader>
              <CardTitle>Live Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              {canManage && (
                <div className="mb-3 rounded-md bg-blue-50 p-3 text-xs text-blue-800">
                  <strong>Zoom integration:</strong> Create a meeting at{" "}
                  <a
                    href="https://zoom.us/start/videomeeting"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline"
                  >
                    zoom.us/start
                  </a>{" "}
                  and paste the join URL into the meeting_url field when adding a live session.
                  Students will see a "Join Zoom meeting" link and can consent to attend.
                </div>
              )}
              {course.live_sessions.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">
                  No live sessions scheduled.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Mode</TableHead>
                      <TableHead>Scheduled</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Link</TableHead>
                      {canManage && <TableHead>Actions</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {course.live_sessions.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell className="font-medium text-slate-900">{s.title}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{s.mode}</Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">
                          {new Date(s.scheduled_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-slate-500">{s.duration_minutes} min</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              s.status === "completed"
                                ? "success"
                                : s.status === "cancelled"
                                  ? "danger"
                                  : "warning"
                            }
                          >
                            {s.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {s.mode === "online" && s.meeting_url ? (
                            <a
                              href={s.meeting_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary-600 hover:underline"
                            >
                              Join ↗
                            </a>
                          ) : s.venue ? (
                            <span className="text-slate-500">{s.venue}</span>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        {canManage && (
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => notifyMutation.mutate(s.id)}
                                loading={notifyMutation.isPending}
                              >
                                Notify
                              </Button>
                              <ConsentListButton liveSessionId={s.id} />
                              <RescheduleLiveSessionButton liveSessionId={s.id} courseId={cid} />
                              <DeleteLiveSessionButton liveSessionId={s.id} courseId={cid} />
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              {canManage && <AddLiveSessionForm courseId={cid} />}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="assessments">
          <Card>
            <CardHeader>
              <CardTitle>Course Assessments</CardTitle>
            </CardHeader>
            <CardContent>
              {course.assessments.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">
                  No assessments linked to this course.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Level</TableHead>
                      <TableHead>Assessment</TableHead>
                      <TableHead>Scored</TableHead>
                      {canManage && <TableHead>Actions</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {course.assessments.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="font-medium text-slate-900">{a.title}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{a.level.replace(/_/g, " ")}</Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">
                          {a.assessment_detail?.title ?? `#${a.assessment}`}
                        </TableCell>
                        <TableCell>
                          <Badge variant={a.is_scored ? "success" : "default"}>
                            {a.is_scored ? "scored" : "unscored"}
                          </Badge>
                        </TableCell>
                        {canManage && (
                          <TableCell>
                            <DeleteAssessmentButton assessmentId={a.id} courseId={cid} />
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              {canManage && <AddAssessmentForm courseId={cid} />}
            </CardContent>
          </Card>
        </TabsContent>
        {canManage && (
          <TabsContent value="registrations">
            <RegistrationsTab courseId={cid} />
          </TabsContent>
        )}
        {canManage && (
          <TabsContent value="completion">
            <CompletionParametersTab course={course} />
          </TabsContent>
        )}
        {canManage && (
          <TabsContent value="update-requests">
            <CourseUpdateRequestsTab courseId={cid} />
          </TabsContent>
        )}
      </Tabs>

      {/* Live session consent modal — shown when ?live_session=ID is in URL */}
      {consentLiveSession && (
        <LiveSessionConsentModal
          liveSession={consentLiveSession}
          onClose={() => {
            searchParams.delete("live_session");
            setSearchParams(searchParams);
          }}
        />
      )}
    </div>
  );
}

function RegistrationsTab({ courseId }: { courseId: number }) {
  const { data: regs, isLoading } = useQuery({
    queryKey: ["training", "courses", courseId, "registrations"],
    queryFn: () => listCourseRegistrations(courseId),
  });

  if (isLoading) return <Spinner />;
  const list = regs ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Student Registrations ({list.length})</CardTitle>
      </CardHeader>
      <CardContent>
        {list.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">No students registered yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Student</TableHead>
                <TableHead>Payment</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Registered</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium text-slate-900">
                    {r.student_name ?? r.student_email}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        r.payment_status === "paid"
                          ? "success"
                          : r.payment_status === "pending"
                            ? "warning"
                            : "danger"
                      }
                    >
                      {r.payment_status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={r.completion_status === "completed" ? "success" : "default"}>
                      {r.completion_status.replace(/_/g, " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">
                    {r.started_at ? new Date(r.started_at).toLocaleDateString() : "—"}
                  </TableCell>
                  <TableCell className="text-slate-500">
                    {new Date(r.registered_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <RegistrationActions registrationId={r.id} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// TRN-3 / TRN-5 (§2.3.2, §5/§6): per-registration assignment-report review +
// trainer<->student messaging.
function RegistrationActions({ registrationId }: { registrationId: number }) {
  const [reportsOpen, setReportsOpen] = useState(false);
  const [messagesOpen, setMessagesOpen] = useState(false);
  return (
    <div className="flex justify-end gap-1">
      <Button size="sm" variant="outline" onClick={() => setReportsOpen(true)}>
        Reports
      </Button>
      <Button size="sm" variant="outline" onClick={() => setMessagesOpen(true)}>
        Messages
      </Button>
      {reportsOpen && (
        <ReportsReviewModal registrationId={registrationId} onClose={() => setReportsOpen(false)} />
      )}
      {messagesOpen && (
        <MessagesModal registrationId={registrationId} onClose={() => setMessagesOpen(false)} />
      )}
    </div>
  );
}

function ReportsReviewModal({
  registrationId,
  onClose,
}: {
  registrationId: number;
  onClose: () => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: reports, isLoading } = useQuery({
    queryKey: ["training", "assignment-reports", registrationId],
    queryFn: () => listAssignmentReports(registrationId),
  });
  const reviewMut = useMutation({
    mutationFn: (v: { reportId: number; score: number; feedback: string }) =>
      reviewAssignmentReport(registrationId, {
        report_id: v.reportId,
        trainer_score: v.score,
        trainer_feedback: v.feedback,
      }),
    onSuccess: () => {
      toast.success("Report reviewed.");
      void queryClient.invalidateQueries({
        queryKey: ["training", "assignment-reports", registrationId],
      });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
  const list = reports ?? [];
  return (
    <Modal open onClose={onClose} title="Assignment reports" size="lg">
      {isLoading ? (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      ) : list.length === 0 ? (
        <p className="py-4 text-center text-sm text-slate-500">No reports submitted yet.</p>
      ) : (
        <div className="space-y-3">
          {list.map((rep) => (
            <ReportReviewRow
              key={rep.id}
              report={rep}
              loading={reviewMut.isPending}
              onReview={(score, feedback) => reviewMut.mutate({ reportId: rep.id, score, feedback })}
            />
          ))}
        </div>
      )}
    </Modal>
  );
}

function ReportReviewRow({
  report,
  loading,
  onReview,
}: {
  report: AssignmentReport;
  loading: boolean;
  onReview: (score: number, feedback: string) => void;
}) {
  const [score, setScore] = useState(report.trainer_score != null ? String(report.trainer_score) : "");
  const [feedback, setFeedback] = useState(report.trainer_feedback ?? "");
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-slate-900">
          {report.student_name || report.student_email}
        </span>
        <Badge variant="outline">{report.status}</Badge>
      </div>
      {report.report_file_url && (
        <a
          href={report.report_file_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary-600 hover:underline"
        >
          View submitted report ↗
        </a>
      )}
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <div>
          <label className="block text-xs text-slate-500">Score (0–10)</label>
          <input
            type="number"
            min={0}
            max={10}
            value={score}
            onChange={(e) => setScore(e.target.value)}
            className="w-20 rounded border border-slate-200 px-2 py-1 text-sm"
          />
        </div>
        <input
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Feedback"
          className="flex-1 rounded border border-slate-200 px-2 py-1 text-sm"
        />
        <Button
          size="sm"
          loading={loading}
          disabled={!score.trim()}
          onClick={() => onReview(Number(score), feedback)}
        >
          Save
        </Button>
      </div>
    </div>
  );
}

function MessagesModal({
  registrationId,
  onClose,
}: {
  registrationId: number;
  onClose: () => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const { data: messages, isLoading } = useQuery({
    queryKey: ["training", "messages", registrationId],
    queryFn: () => listMessages(registrationId),
  });
  const sendMut = useMutation({
    mutationFn: () => sendMessage(registrationId, body.trim()),
    onSuccess: () => {
      setBody("");
      void queryClient.invalidateQueries({ queryKey: ["training", "messages", registrationId] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
  const list = messages ?? [];
  return (
    <Modal open onClose={onClose} title="Messages" size="md">
      <div className="mb-3 max-h-64 space-y-2 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-4">
            <Spinner />
          </div>
        ) : list.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">No messages yet.</p>
        ) : (
          list.map((m) => (
            <div key={m.id} className="rounded-md border border-slate-100 p-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-800">{m.sender_name || m.sender_email}</span>
                <span className="text-xs text-slate-400">{new Date(m.sent_at).toLocaleString()}</span>
              </div>
              <p className="mt-0.5 text-slate-700">{m.body}</p>
            </div>
          ))
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (body.trim()) sendMut.mutate();
        }}
        className="flex gap-2"
      >
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Type a message…"
          className="flex-1 rounded border border-slate-200 px-3 py-2 text-sm"
        />
        <Button type="submit" loading={sendMut.isPending} disabled={!body.trim()}>
          Send
        </Button>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Add Live Session Form (SRS §2.5)
// ---------------------------------------------------------------------------

function AddLiveSessionForm({ courseId }: { courseId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<"online" | "offline">("online");
  const [meetingUrl, setMeetingUrl] = useState("");
  const [venue, setVenue] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [duration, setDuration] = useState("60");
  const [description, setDescription] = useState("");
  const [autoCreateZoom, setAutoCreateZoom] = useState(false);

  // Check if Zoom API is configured
  const { data: zoomConfig } = useQuery({
    queryKey: ["training", "zoom-config"],
    queryFn: () => getZoomConfig(),
  });
  const zoomConfigured = zoomConfig?.is_configured ?? false;

  const mutation = useMutation({
    mutationFn: async () => {
      let finalMeetingUrl = meetingUrl;

      // Auto-create Zoom meeting if option is selected
      if (autoCreateZoom && mode === "online" && zoomConfigured) {
        try {
          const zoomMeeting = await createZoomMeeting({
            topic: title,
            start_time: new Date(scheduledAt).toISOString(),
            duration_minutes: Number(duration),
          });
          finalMeetingUrl = zoomMeeting.join_url;
          toast.success(`Zoom meeting created: ${zoomMeeting.join_url}`);
        } catch {
          toast.error("Failed to create Zoom meeting. Using manual URL instead.");
        }
      }

      return addLiveSession(courseId, {
        title,
        mode,
        meeting_url: finalMeetingUrl,
        venue,
        scheduled_at: new Date(scheduledAt).toISOString(),
        duration_minutes: Number(duration),
        description,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
      toast.success("Live session added.");
      setTitle("");
      setMeetingUrl("");
      setVenue("");
      setScheduledAt("");
      setDuration("60");
      setDescription("");
      setAutoCreateZoom(false);
      setShow(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (!show) {
    return (
      <div className="mt-4 border-t border-slate-100 pt-3">
        <Button variant="outline" size="sm" onClick={() => setShow(true)}>
          + Add live session
        </Button>
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="mt-4 space-y-3 border-t border-slate-100 pt-4"
    >
      <div className="text-sm font-semibold text-slate-900">Add Live Session</div>
      <Input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Session title (e.g., Week 1 Q&A)"
        required
      />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="ls-mode">Mode</Label>
          <select
            id="ls-mode"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={mode}
            onChange={(e) => setMode(e.target.value as "online" | "offline")}
          >
            <option value="online">Online (Zoom)</option>
            <option value="offline">Offline (Classroom)</option>
          </select>
        </div>
        <div>
          <Label htmlFor="ls-time" required>
            Scheduled at
          </Label>
          <Input
            id="ls-time"
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            required
          />
        </div>
      </div>
      {mode === "online" ? (
        <>
          {zoomConfigured && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoCreateZoom}
                onChange={(e) => setAutoCreateZoom(e.target.checked)}
                className="h-4 w-4"
              />
              Auto-create Zoom meeting (via API)
            </label>
          )}
          <Input
            value={meetingUrl}
            onChange={(e) => setMeetingUrl(e.target.value)}
            placeholder={
              autoCreateZoom && zoomConfigured
                ? "Auto-generated by Zoom API (leave empty)"
                : "Zoom meeting URL (https://zoom.us/j/...)"
            }
            disabled={autoCreateZoom && zoomConfigured}
          />
          {!zoomConfigured && (
            <p className="text-xs text-slate-400">
              💡 To enable auto-create, set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET in
              the server environment.
            </p>
          )}
        </>
      ) : (
        <Input
          value={venue}
          onChange={(e) => setVenue(e.target.value)}
          placeholder="Venue address"
        />
      )}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="ls-dur">Duration (minutes)</Label>
          <Input
            id="ls-dur"
            type="number"
            min="15"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>
      </div>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        rows={2}
        className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
      />
      <div className="flex gap-2">
        <Button
          type="submit"
          size="sm"
          loading={mutation.isPending}
          disabled={!title || !scheduledAt}
        >
          Add session
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={() => setShow(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Add Assessment Form (SRS §2.4)
// ---------------------------------------------------------------------------

function AddAssessmentForm({ courseId }: { courseId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState("");
  const [assessmentId, setAssessmentId] = useState("");
  const [level, setLevel] = useState("end_of_session");
  const [isScored, setIsScored] = useState(true);

  // Load available assessments from the assessment module
  const { data: assessmentsData } = useQuery({
    queryKey: ["assessment", "for-training", "published"],
    queryFn: () => listAssessments({ status: "published" }),
  });

  const mutation = useMutation({
    mutationFn: () =>
      addCourseAssessment(courseId, {
        assessment: Number(assessmentId),
        level,
        title,
        is_scored: isScored,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
      toast.success("Assessment linked to course.");
      setTitle("");
      setAssessmentId("");
      setShow(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (!show) {
    return (
      <div className="mt-4 border-t border-slate-100 pt-3">
        <Button variant="outline" size="sm" onClick={() => setShow(true)}>
          + Link assessment
        </Button>
      </div>
    );
  }

  const assessments = assessmentsData?.results ?? [];

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="mt-4 space-y-3 border-t border-slate-100 pt-4"
    >
      <div className="text-sm font-semibold text-slate-900">Link Assessment to Course</div>
      <p className="text-xs text-slate-500">
        Select a published assessment from the Assessment module. It will be embedded at the
        specified level (during session, end of session/topic/lesson/course).
      </p>
      <div>
        <Label htmlFor="as-title" required>
          Title (shown to students)
        </Label>
        <Input
          id="as-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., Lesson 1 Quiz"
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="as-assessment" required>
            Assessment
          </Label>
          <select
            id="as-assessment"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={assessmentId}
            onChange={(e) => setAssessmentId(e.target.value)}
            required
          >
            <option value="">Select an assessment...</option>
            {assessments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="as-level">Level</Label>
          <select
            id="as-level"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            <option value="during_session">During Session</option>
            <option value="end_of_session">End of Session</option>
            <option value="end_of_topic">End of Topic</option>
            <option value="end_of_lesson">End of Lesson</option>
            <option value="end_of_course">End of Course</option>
          </select>
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isScored}
          onChange={(e) => setIsScored(e.target.checked)}
          className="h-4 w-4"
        />
        Scored assessment (affects course completion)
      </label>
      <div className="flex gap-2">
        <Button
          type="submit"
          size="sm"
          loading={mutation.isPending}
          disabled={!title || !assessmentId}
        >
          Link assessment
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={() => setShow(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Delete buttons for Live Sessions + Assessments
// ---------------------------------------------------------------------------

// TRN-8 (§5): trainer views the live-session consent list (who will attend).
function ConsentListButton({ liveSessionId }: { liveSessionId: number }) {
  const [open, setOpen] = useState(false);
  const { data: consents, isLoading } = useQuery({
    queryKey: ["training", "live-session-consents", liveSessionId],
    queryFn: () => listLiveSessionConsents(liveSessionId),
    enabled: open,
  });
  const list = consents ?? [];
  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        Consent list
      </Button>
      {open && (
        <Modal open onClose={() => setOpen(false)} title="Live-session consent list" size="sm">
          {isLoading ? (
            <div className="flex justify-center py-6">
              <Spinner />
            </div>
          ) : list.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">No responses yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {list.map((c) => (
                <li
                  key={c.id}
                  className="flex items-center justify-between rounded border border-slate-100 p-2"
                >
                  <span className="text-slate-700">
                    {c.student_name || c.student_email || `Student #${c.student}`}
                  </span>
                  <Badge variant={c.status === "consented" ? "success" : "danger"}>
                    {c.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Modal>
      )}
    </>
  );
}

function DeleteLiveSessionButton({
  liveSessionId,
  courseId,
}: {
  liveSessionId: number;
  courseId: number;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteLiveSession(liveSessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
      toast.success("Live session deleted.");
      setConfirming(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (!confirming) {
    return (
      <Button
        size="sm"
        variant="outline"
        onClick={() => setConfirming(true)}
        className="text-danger-600 hover:bg-danger-50"
      >
        ✕
      </Button>
    );
  }
  return (
    <div className="flex gap-1">
      <Button
        size="sm"
        variant="danger"
        onClick={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      >
        Delete?
      </Button>
      <Button size="sm" variant="outline" onClick={() => setConfirming(false)}>
        No
      </Button>
    </div>
  );
}

function DeleteAssessmentButton({
  assessmentId,
  courseId,
}: {
  assessmentId: number;
  courseId: number;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteCourseAssessment(assessmentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
      toast.success("Assessment removed from course.");
      setConfirming(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (!confirming) {
    return (
      <Button
        size="sm"
        variant="outline"
        onClick={() => setConfirming(true)}
        className="text-danger-600 hover:bg-danger-50"
      >
        ✕
      </Button>
    );
  }
  return (
    <div className="flex gap-1">
      <Button
        size="sm"
        variant="danger"
        onClick={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      >
        Delete?
      </Button>
      <Button size="sm" variant="outline" onClick={() => setConfirming(false)}>
        No
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Report 3 §6 — Completion Parameters tab (trainer sets mandatory contents)
// ---------------------------------------------------------------------------

function CompletionParametersTab({ course }: { course: TrainingCourse }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const cid = course.id;

  // Flatten all contents/assignments for the checkbox list
  const allItems: {
    content_type: CompletionParameter["content_type"];
    content_id: number;
    label: string;
  }[] = [];
  for (const lesson of course.lessons) {
    for (const topic of lesson.topics) {
      for (const session of topic.sessions) {
        for (const c of session.contents) {
          allItems.push({
            content_type: "session_content",
            content_id: c.id,
            label: `${lesson.title} → ${session.title} → ${c.title}`,
          });
        }
        for (const a of session.assignments) {
          allItems.push({
            content_type: "assignment",
            content_id: a.id,
            label: `${lesson.title} → ${session.title} → ${a.title} (assignment)`,
          });
        }
      }
    }
  }

  const { data: existing } = useQuery({
    queryKey: ["training", "completion-parameters", cid],
    queryFn: () => listCompletionParameters(cid),
  });

  const mandatorySet = new Set(
    (existing ?? []).filter((p) => p.is_mandatory).map((p) => `${p.content_type}:${p.content_id}`),
  );
  const [checked, setChecked] = useState<Set<string>>(new Set(mandatorySet));

  // Sync when loaded
  if (existing && checked.size === 0 && mandatorySet.size > 0 && checked !== mandatorySet) {
    setChecked(new Set(mandatorySet));
  }

  const toggle = (key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const params: CompletionParameter[] = allItems
        .filter((it) => checked.has(`${it.content_type}:${it.content_id}`))
        .map((it) => ({
          content_type: it.content_type,
          content_id: it.content_id,
          is_mandatory: true,
        }));
      return setCompletionParameters(cid, params);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["training", "completion-parameters", cid],
      });
      toast.success("Completion parameters saved.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Set Completion Parameters</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-slate-500">
          Check the contents a candidate MUST complete to finish the course. The completion % shown
          to candidates is computed against these mandatory items.
        </p>
        {allItems.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No course content yet. Add content in the Structure tab first.
          </p>
        ) : (
          <div className="max-h-96 space-y-1 overflow-y-auto">
            {allItems.map((it) => {
              const key = `${it.content_type}:${it.content_id}`;
              return (
                <label
                  key={key}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={checked.has(key)}
                    onChange={() => toggle(key)}
                    className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
                  />
                  <span className="text-slate-700">{it.label}</span>
                </label>
              );
            })}
          </div>
        )}
        <Button onClick={() => saveMutation.mutate()} loading={saveMutation.isPending}>
          Save parameters
        </Button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Report 3 §7 — Course Update Requests tab (trainer requests / admin approves)
// ---------------------------------------------------------------------------

function CourseUpdateRequestsTab({ courseId }: { courseId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "cj_admin";
  const [showForm, setShowForm] = useState(false);
  const [reqType, setReqType] = useState<"update" | "delete">("update");
  const [reason, setReason] = useState("");

  const { data: requests } = useQuery({
    queryKey: ["training", "course-update-requests"],
    queryFn: () => listCourseUpdateRequests(),
  });
  const courseRequests = (requests ?? []).filter((r) => r.course === courseId);

  // TRN-2 (§7): admin approves or declines a pending course-change request.
  const reviewMutation = useMutation({
    mutationFn: (v: { id: number; approve: boolean; note: string }) =>
      v.approve
        ? approveCourseUpdateRequest(v.id, v.note)
        : declineCourseUpdateRequest(v.id, v.note),
    onSuccess: () => {
      toast.success("Request reviewed.");
      void queryClient.invalidateQueries({ queryKey: ["training", "course-update-requests"] });
      void queryClient.invalidateQueries({ queryKey: ["training", "course", courseId] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const requestMutation = useMutation({
    mutationFn: () => requestCourseUpdate(courseId, { request_type: reqType, reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["training", "course-update-requests"],
      });
      toast.success("Request submitted. An admin will review it.");
      setShowForm(false);
      setReason("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Course Update Requests</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-slate-500">
          Published courses can only be modified or deleted with admin approval. Submit a request;
          an admin will approve or decline it.
        </p>

        {courseRequests.length === 0 ? (
          <p className="py-2 text-sm text-slate-500">No requests yet.</p>
        ) : (
          <div className="space-y-2">
            {courseRequests.map((r: CourseUpdateRequest) => (
              <div key={r.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium capitalize">
                    {r.request_type} request —{" "}
                    <Badge
                      variant={
                        r.status === "approved"
                          ? "success"
                          : r.status === "declined"
                            ? "danger"
                            : "warning"
                      }
                    >
                      {r.status}
                    </Badge>
                  </span>
                  <span className="text-xs text-slate-400">
                    {new Date(r.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="mt-1 text-slate-600">{r.reason}</p>
                {r.admin_note && (
                  <p className="mt-1 text-xs text-slate-500">Admin note: {r.admin_note}</p>
                )}
                {isAdmin && r.status === "pending" && (
                  <div className="mt-2 flex gap-2">
                    <Button
                      size="sm"
                      loading={reviewMutation.isPending}
                      onClick={() => {
                        const note = window.prompt("Admin note (optional):") ?? "";
                        reviewMutation.mutate({ id: r.id, approve: true, note });
                      }}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const note = window.prompt("Reason for declining (optional):") ?? "";
                        reviewMutation.mutate({ id: r.id, approve: false, note });
                      }}
                    >
                      Decline
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {!showForm ? (
          <Button variant="outline" onClick={() => setShowForm(true)}>
            + Request update / delete
          </Button>
        ) : (
          <div className="space-y-2 rounded-md border border-slate-200 p-3">
            <select
              className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
              value={reqType}
              onChange={(e) => setReqType(e.target.value as "update" | "delete")}
            >
              <option value="update">Update published course</option>
              <option value="delete">Delete published course</option>
            </select>
            <textarea
              rows={2}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
              placeholder="Reason for the change…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="flex gap-2">
              <Button
                onClick={() => requestMutation.mutate()}
                loading={requestMutation.isPending}
                disabled={!reason.trim()}
              >
                Submit request
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RescheduleLiveSessionButton({
  liveSessionId,
  courseId,
}: {
  liveSessionId: number;
  courseId: number;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [scheduledAt, setScheduledAt] = useState("");
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () => rescheduleLiveSession(liveSessionId, { scheduled_at: scheduledAt, reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
      toast.success("Session rescheduled. Registered students notified.");
      setOpen(false);
      setScheduledAt("");
      setReason("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (!open) {
    return (
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        Reschedule
      </Button>
    );
  }
  return (
    <div className="flex flex-col gap-1 rounded-md border border-slate-200 p-2">
      <input
        type="datetime-local"
        className="h-8 rounded-md border border-slate-200 px-2 text-xs"
        value={scheduledAt}
        onChange={(e) => setScheduledAt(e.target.value)}
      />
      <input
        type="text"
        placeholder="Reason (required)"
        className="h-8 rounded-md border border-slate-200 px-2 text-xs"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="flex gap-1">
        <Button
          size="sm"
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!scheduledAt || !reason.trim()}
        >
          Save
        </Button>
        <Button size="sm" variant="outline" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
