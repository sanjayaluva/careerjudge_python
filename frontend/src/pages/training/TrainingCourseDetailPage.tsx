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
import { Link, useParams } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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
  COURSE_TYPES,
  listCourseRegistrations,
  publishCourse,
  registerForCourse,
  retrieveCourse,
  SCHEDULE_TYPES,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

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

  const { data: course, isLoading } = useQuery({
    queryKey: ["training", "courses", cid],
    queryFn: () => retrieveCourse(cid),
    enabled: !Number.isNaN(cid),
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
              {course.lessons.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">No lessons defined yet.</p>
              ) : (
                <div className="space-y-4">
                  {course.lessons.map((lesson) => (
                    <div key={lesson.id} className="rounded-md border border-slate-200 p-4">
                      <div className="font-semibold text-slate-900">
                        {lesson.title}{" "}
                        <span className="ml-2 text-xs font-normal text-slate-500">
                          (Week {lesson.week_number})
                        </span>
                      </div>
                      {lesson.topics.length === 0 ? (
                        <p className="mt-1 text-xs text-slate-500">No topics.</p>
                      ) : (
                        <div className="mt-2 space-y-2">
                          {lesson.topics.map((topic) => (
                            <div key={topic.id} className="ml-4 border-l border-slate-200 pl-3">
                              <div className="text-sm font-medium text-slate-700">
                                {topic.title}
                              </div>
                              {topic.sessions.length === 0 ? (
                                <p className="ml-2 text-xs text-slate-500">No sessions.</p>
                              ) : (
                                <div className="mt-1 space-y-1">
                                  {topic.sessions.map((session) => (
                                    <div key={session.id} className="ml-2 text-xs">
                                      <span className="font-medium text-slate-700">
                                        {session.title}
                                      </span>
                                      {session.contents.length > 0 && (
                                        <span className="ml-2 text-slate-500">
                                          ({session.contents.length} content
                                          {session.contents.length !== 1 ? "s" : ""})
                                        </span>
                                      )}
                                      {session.assignments.length > 0 && (
                                        <span className="ml-2 text-slate-500">
                                          ({session.assignments.length} assignment
                                          {session.assignments.length !== 1 ? "s" : ""})
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
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
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === ASSESSMENTS TAB === */}
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
