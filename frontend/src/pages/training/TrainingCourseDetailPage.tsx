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
  addLiveSession,
  COURSE_TYPES,
  listCourseRegistrations,
  notifyLiveSessionStudents,
  publishCourse,
  registerForCourse,
  retrieveCourse,
  SCHEDULE_TYPES,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { LiveSessionConsentModal } from "./LiveSessionConsentModal";
import { CourseStructureEditor } from "./CourseStructureEditor";

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

  const publishMutation = useMutation({
    mutationFn: () => publishCourse(cid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", cid] });
      toast.success("Course published.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const registerMutation = useMutation({
    mutationFn: () => registerForCourse(cid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "my-courses"] });
      toast.success("Registered! Payment pending.");
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

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="structure">Structure ({course.lessons.length} lessons)</TabsTrigger>
          <TabsTrigger value="live-sessions">
            Live Sessions ({course.live_sessions.length})
          </TabsTrigger>
          <TabsTrigger value="assessments">Assessments ({course.assessments.length})</TabsTrigger>
          {canManage && <TabsTrigger value="registrations">Registrations</TabsTrigger>}
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
                {!canManage && course.status === "published" && (
                  <Button
                    onClick={() => registerMutation.mutate()}
                    loading={registerMutation.isPending}
                  >
                    Register for ${course.price}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

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
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => notifyMutation.mutate(s.id)}
                              loading={notifyMutation.isPending}
                            >
                              Notify
                            </Button>
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
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === REGISTRATIONS TAB (trainer/admin only) === */}
        {canManage && (
          <TabsContent value="registrations">
            <RegistrationsTab courseId={cid} />
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
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

  const mutation = useMutation({
    mutationFn: () =>
      addLiveSession(courseId, {
        title,
        mode,
        meeting_url: meetingUrl,
        venue,
        scheduled_at: new Date(scheduledAt).toISOString(),
        duration_minutes: Number(duration),
        description,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses", courseId] });
      toast.success("Live session added.");
      setTitle("");
      setMeetingUrl("");
      setVenue("");
      setScheduledAt("");
      setDuration("60");
      setDescription("");
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
        <Input
          value={meetingUrl}
          onChange={(e) => setMeetingUrl(e.target.value)}
          placeholder="Zoom meeting URL (https://zoom.us/j/...)"
        />
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
