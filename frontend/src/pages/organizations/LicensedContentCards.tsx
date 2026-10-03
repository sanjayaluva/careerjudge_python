/**
 * Report 9 (1 Oct 2026): content CJ Admin licenses to an organization, and
 * what its managers (Corp Admin, Corp Exclusive, Group Admin, Channel Partner)
 * do with it on behalf of their members — User Details pp.3–5 "View Trainings
 * → Assign Training", "Schedule/Reschedule Training", "View Counsellors →
 * Schedule/Reschedule Counselling".
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

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
  Modal,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import { listAllAssessments } from "@/api/assessment";
import { listAllSolutions } from "@/api/careerProfiling";
import { extractApiError } from "@/api/client";
import type { CounselingSession } from "@/api/counseling";
import {
  assignCourse,
  bookCounselingForMember,
  cancelCourseSchedule,
  cancelMemberCounseling,
  createAssignment,
  createCourseSchedule,
  deleteAssignment,
  getLicensedCourseProgress,
  listAssignments,
  listCourseSchedules,
  listLicensedCourses,
  listOrgCounselingSessions,
  listOrgCounsellorSlots,
  listOrgCounsellors,
  rescheduleCourseSchedule,
  rescheduleMemberCounseling,
  unassignCourse,
  type OrganizationAssignment,
  type OrganizationMember,
} from "@/api/organizations";
import { listAllCourses } from "@/api/training";
import { CourseProgressTable } from "@/pages/training/CourseProgressTable";

const ORG_KEY = (id: number) => ["organizations", id];
const SELECT =
  "h-10 rounded-md border border-slate-300 bg-white px-2 text-sm shadow-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25";

type ItemType = OrganizationAssignment["item_type"];

function useAssignments(orgId: number) {
  return useQuery({
    queryKey: [...ORG_KEY(orgId), "assignments"],
    queryFn: () => listAssignments(orgId),
    enabled: !Number.isNaN(orgId),
  });
}

/** Members a manager can act for: the organization's individuals, not its
 * admins (the members list is already limited to a Group Admin's group). */
function learners(members: OrganizationMember[]) {
  return members.filter((m) => !m.is_admin && m.user.role === "individual");
}

const memberName = (m: { full_name?: string | null; email: string }) => m.full_name || m.email;

function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <Alert variant="error" className="mb-3">
      <AlertDescription>{error}</AlertDescription>
    </Alert>
  );
}

// ---------------------------------------------------------------------------
// Licensed content (#98/#100-#103): CJ Admin licenses published assessments
// and courses, and switches counselling on/off, for this organization.
// ---------------------------------------------------------------------------

export function LicensedContentCard({ orgId, canLicense }: { orgId: number; canLicense: boolean }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const { data: assignments = [] } = useAssignments(orgId);

  // Only CJ Admin picks from the catalogues (every page of them); managers
  // read item titles.
  const { data: catalogueAssessments = [] } = useQuery({
    queryKey: ["assessments", "published", "all"],
    queryFn: () => listAllAssessments({ status: "published" }),
    enabled: canLicense,
  });
  const { data: catalogueCourses = [] } = useQuery({
    queryKey: ["training", "courses", "published", "all"],
    queryFn: () => listAllCourses({ status: "published" }),
    enabled: canLicense,
  });
  // Report 9 #97/#99/#102: published profiling solutions are licensed too.
  const { data: catalogueSolutions = [] } = useQuery({
    queryKey: ["career-profiling", "solutions", "published", "all"],
    queryFn: () => listAllSolutions({ status: "published" }),
    enabled: canLicense,
  });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
    setError(null);
  };
  const assignMutation = useMutation({
    mutationFn: (p: { item_type: ItemType; item_id?: number }) => createAssignment(orgId, p),
    onSuccess: refresh,
    onError: (err) => setError(extractApiError(err)),
  });
  const removeMutation = useMutation({
    mutationFn: (assignmentId: number) => deleteAssignment(orgId, assignmentId),
    onSuccess: refresh,
    onError: (err) => setError(extractApiError(err)),
  });

  const counselling = assignments.find((a) => a.item_type === "counseling");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Licensed content</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <p className="text-sm text-slate-500">
          {canLicense
            ? "Members and managers of this organization see only the assessments, courses and profiling solutions licensed here. Licensed courses and counselling cost the members nothing."
            : "What CJ Admin has licensed to your organization. You can assign and schedule these for your members below."}
        </p>
        <ErrorNote error={error} />
        <LicenceSection
          heading="Assessments"
          noun="assessment"
          rows={assignments.filter((a) => a.item_type === "assessment")}
          options={catalogueAssessments.map((a) => ({ id: a.id, title: a.title }))}
          canLicense={canLicense}
          busy={assignMutation.isPending || removeMutation.isPending}
          onAssign={(id) => assignMutation.mutate({ item_type: "assessment", item_id: id })}
          onRemove={(id) => removeMutation.mutate(id)}
        />
        <LicenceSection
          heading="Courses"
          noun="course"
          rows={assignments.filter((a) => a.item_type === "training_course")}
          options={catalogueCourses.map((c) => ({ id: c.id, title: c.title }))}
          canLicense={canLicense}
          busy={assignMutation.isPending || removeMutation.isPending}
          onAssign={(id) => assignMutation.mutate({ item_type: "training_course", item_id: id })}
          onRemove={(id) => removeMutation.mutate(id)}
        />
        <LicenceSection
          heading="Profiling solutions"
          noun="profiling solution"
          rows={assignments.filter((a) => a.item_type === "profiling_solution")}
          options={catalogueSolutions.map((s) => ({ id: s.id, title: s.title }))}
          canLicense={canLicense}
          busy={assignMutation.isPending || removeMutation.isPending}
          onAssign={(id) => assignMutation.mutate({ item_type: "profiling_solution", item_id: id })}
          onRemove={(id) => removeMutation.mutate(id)}
        />
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Counselling</h3>
          <div className="flex flex-wrap items-center gap-3">
            {counselling ? (
              <Badge variant="success">Licensed</Badge>
            ) : (
              <Badge variant="default">Not licensed</Badge>
            )}
            <span className="text-sm text-slate-500">
              {counselling
                ? "Managers can book counselling sessions for their members."
                : "Managers cannot book counselling for their members."}
            </span>
            {canLicense &&
              (counselling ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-danger-600 hover:bg-danger-50 hover:text-danger-700"
                  loading={removeMutation.isPending}
                  onClick={() => removeMutation.mutate(counselling.id)}
                >
                  Revoke
                </Button>
              ) : (
                <Button
                  size="sm"
                  loading={assignMutation.isPending}
                  onClick={() => assignMutation.mutate({ item_type: "counseling" })}
                >
                  License counselling
                </Button>
              ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function LicenceSection({
  heading,
  noun,
  rows,
  options,
  canLicense,
  busy,
  onAssign,
  onRemove,
}: {
  heading: string;
  noun: string;
  rows: OrganizationAssignment[];
  options: { id: number; title: string }[];
  canLicense: boolean;
  busy: boolean;
  onAssign: (itemId: number) => void;
  onRemove: (assignmentId: number) => void;
}) {
  const [selected, setSelected] = useState("");
  const licensed = new Set(rows.map((r) => r.item_id));
  const available = options.filter((o) => !licensed.has(o.id));
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-900">{heading}</h3>
      {canLicense && (
        <div className="mb-3 flex items-center gap-2">
          <select
            aria-label={`Published ${noun} to license`}
            className={`${SELECT} flex-1`}
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Select a published {noun}…</option>
            {available.map((o) => (
              <option key={o.id} value={o.id}>
                {o.title}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            disabled={!selected || busy}
            onClick={() => {
              onAssign(Number(selected));
              setSelected("");
            }}
          >
            Assign
          </Button>
        </div>
      )}
      {rows.length === 0 ? (
        <p className="py-1 text-sm text-slate-500">No {noun}s licensed yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="capitalize">{noun}</TableHead>
              <TableHead>Assigned by</TableHead>
              {canLicense && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((a) => (
              <TableRow key={a.id}>
                <TableCell className="font-medium text-slate-900">{a.item_title}</TableCell>
                <TableCell className="text-slate-500">{a.assigned_by_name || "—"}</TableCell>
                {canLicense && (
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-danger-600 hover:bg-danger-50 hover:text-danger-700"
                      disabled={busy}
                      onClick={() => onRemove(a.id)}
                    >
                      Remove
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Licensed courses → assign / unassign members (#15/#28/#59)
// ---------------------------------------------------------------------------

export function LicensedCoursesCard({
  orgId,
  members,
  canAct,
}: {
  orgId: number;
  members: OrganizationMember[];
  canAct: boolean;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [picked, setPicked] = useState<Record<number, string>>({});
  const [progressFor, setProgressFor] = useState<number | null>(null);
  const KEY = [...ORG_KEY(orgId), "licensed-courses"];
  const { data: courses = [], isLoading } = useQuery({
    queryKey: KEY,
    queryFn: () => listLicensedCourses(orgId),
    enabled: !Number.isNaN(orgId),
  });
  const people = learners(members);

  const done = (message: string) => {
    void queryClient.invalidateQueries({ queryKey: KEY });
    setError(null);
    setNotice(message);
  };
  const assignMutation = useMutation({
    mutationFn: (p: { courseId: number; userId: number }) =>
      assignCourse(orgId, p.courseId, [p.userId]),
    onSuccess: (_d, p) => {
      setPicked((prev) => ({ ...prev, [p.courseId]: "" }));
      done("Course assigned. The member has been notified.");
    },
    onError: (err) => setError(extractApiError(err)),
  });
  const unassignMutation = useMutation({
    mutationFn: (p: { courseId: number; userId: number }) =>
      unassignCourse(orgId, p.courseId, p.userId),
    onSuccess: () => done("Course unassigned. The member has been notified."),
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Licensed courses</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-slate-500">
          Assign a licensed course to a member to enrol them — the organization&apos;s licence
          covers the fee. A course can be unassigned until the member starts it.
        </p>
        <ErrorNote error={error} />
        {notice && !error && <p className="mb-3 text-sm text-success-700">{notice}</p>}
        {isLoading ? null : courses.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-8 text-center text-sm text-slate-500">
            No courses have been licensed to this organization yet.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Course</TableHead>
                <TableHead>Assigned members</TableHead>
                {canAct && <TableHead className="text-right">Assign to</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {courses.map((c) => {
                const enrolled = new Set(c.members.map((m) => m.user_id));
                const eligible = people.filter((m) => !enrolled.has(m.user.id));
                return (
                  <TableRow key={c.id}>
                    <TableCell className="align-top font-medium text-slate-900">
                      {c.title}
                      {c.members.length > 0 && (
                        <div className="mt-1">
                          <Button size="sm" variant="outline" onClick={() => setProgressFor(c.id)}>
                            Progress
                          </Button>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="align-top">
                      {c.members.length === 0 ? (
                        <span className="text-sm text-slate-500">Nobody yet</span>
                      ) : (
                        <ul className="space-y-1">
                          {c.members.map((m) => (
                            <li key={m.registration_id} className="flex items-center gap-2 text-sm">
                              <span className="text-slate-900">{memberName(m)}</span>
                              <Badge variant="outline">
                                {m.completion_status.replace(/_/g, " ")}
                              </Badge>
                              {!m.assigned_by_organization && (
                                <span className="text-xs text-slate-500">(self-registered)</span>
                              )}
                              {canAct && m.can_unassign && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-danger-600 hover:bg-danger-50 hover:text-danger-700"
                                  disabled={unassignMutation.isPending}
                                  onClick={() =>
                                    unassignMutation.mutate({ courseId: c.id, userId: m.user_id })
                                  }
                                >
                                  Unassign
                                </Button>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </TableCell>
                    {canAct && (
                      <TableCell className="text-right align-top">
                        <div className="flex justify-end gap-2">
                          <select
                            aria-label={`Member to assign ${c.title} to`}
                            className={SELECT}
                            value={picked[c.id] ?? ""}
                            onChange={(e) => setPicked({ ...picked, [c.id]: e.target.value })}
                          >
                            <option value="">Member…</option>
                            {eligible.map((m) => (
                              <option key={m.user.id} value={m.user.id}>
                                {memberName(m.user)}
                              </option>
                            ))}
                          </select>
                          <Button
                            size="sm"
                            disabled={!picked[c.id] || assignMutation.isPending}
                            onClick={() =>
                              assignMutation.mutate({
                                courseId: c.id,
                                userId: Number(picked[c.id]),
                              })
                            }
                          >
                            Assign
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
        {progressFor !== null && (
          <CourseProgressModal
            orgId={orgId}
            courseId={progressFor}
            onClose={() => setProgressFor(null)}
          />
        )}
      </CardContent>
    </Card>
  );
}

// Report 9 #17: the course progress of the members assigned / registered
// (his group's for a Group Admin) — status, completion %, items done, start,
// last activity and assessment scores.
function CourseProgressModal({
  orgId,
  courseId,
  onClose,
}: {
  orgId: number;
  courseId: number;
  onClose: () => void;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: [...ORG_KEY(orgId), "licensed-courses", courseId, "progress"],
    queryFn: () => getLicensedCourseProgress(orgId, courseId),
  });
  return (
    <Modal
      open
      onClose={onClose}
      size="xl"
      title={data ? `Course progress — ${data.course.title}` : "Course progress"}
    >
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : error ? (
        <ErrorNote error={extractApiError(error)} />
      ) : !data || data.learners.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-8 text-center text-sm text-slate-500">
          None of your members is registered in this course yet.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <CourseProgressTable rows={data.learners} />
        </div>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Scheduled courses (#16/#29/#60) — parallel to "Scheduled assessments"
// ---------------------------------------------------------------------------

export function CourseSchedulesCard({
  orgId,
  groups,
  canSchedule,
}: {
  orgId: number;
  groups: { id: number; name: string }[];
  canSchedule: boolean;
}) {
  const queryClient = useQueryClient();
  const [courseId, setCourseId] = useState("");
  const [when, setWhen] = useState("");
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [moving, setMoving] = useState<{ id: number; when: string } | null>(null);
  const KEY = [...ORG_KEY(orgId), "course-schedules"];

  const { data: schedules = [] } = useQuery({
    queryKey: KEY,
    queryFn: () => listCourseSchedules(orgId),
    enabled: !Number.isNaN(orgId),
  });
  const { data: courses = [] } = useQuery({
    queryKey: [...ORG_KEY(orgId), "licensed-courses"],
    queryFn: () => listLicensedCourses(orgId),
    enabled: !Number.isNaN(orgId),
  });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: KEY });
    setError(null);
  };
  const createMutation = useMutation({
    mutationFn: () =>
      createCourseSchedule(orgId, {
        course: Number(courseId),
        scheduled_at: new Date(when).toISOString(),
        ...(groupId ? { group: Number(groupId) } : {}),
      }),
    onSuccess: () => {
      refresh();
      setCourseId("");
      setWhen("");
      setGroupId("");
    },
    onError: (err) => setError(extractApiError(err)),
  });
  const rescheduleMutation = useMutation({
    mutationFn: (m: { id: number; when: string }) =>
      rescheduleCourseSchedule(orgId, m.id, { scheduled_at: new Date(m.when).toISOString() }),
    onSuccess: () => {
      refresh();
      setMoving(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });
  const cancelMutation = useMutation({
    mutationFn: (id: number) => cancelCourseSchedule(orgId, id),
    onSuccess: refresh,
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scheduled courses</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-slate-500">
          Schedule a licensed course for members — they are notified when it is scheduled,
          rescheduled or cancelled.
        </p>
        <ErrorNote error={error} />
        {canSchedule && courses.length === 0 && (
          <p className="mb-3 text-sm text-slate-500">
            No courses have been licensed to this organization yet, so none can be scheduled.
          </p>
        )}
        {canSchedule && (
          <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-4">
            <select
              aria-label="Course"
              className={SELECT}
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
            >
              <option value="">Course…</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
            <input
              type="datetime-local"
              aria-label="Date and time"
              className={SELECT}
              value={when}
              onChange={(e) => setWhen(e.target.value)}
            />
            <select
              aria-label="Members"
              className={SELECT}
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
            >
              <option value="">All members</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={!courseId || !when || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              Schedule
            </Button>
          </div>
        )}
        {schedules.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-8 text-center text-sm text-slate-500">
            No courses scheduled yet.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Course</TableHead>
                <TableHead>When</TableHead>
                <TableHead>Target</TableHead>
                {canSchedule && <TableHead className="text-right">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {schedules.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium text-slate-900">{s.course_title}</TableCell>
                  <TableCell className="text-slate-500">
                    {moving?.id === s.id ? (
                      <input
                        type="datetime-local"
                        aria-label="New date and time"
                        className="h-8 rounded-md border border-slate-300 bg-white px-2 text-sm shadow-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                        value={moving.when}
                        onChange={(e) => setMoving({ id: s.id, when: e.target.value })}
                      />
                    ) : (
                      new Date(s.scheduled_at).toLocaleString()
                    )}
                  </TableCell>
                  <TableCell className="text-slate-500">{s.group_name || "All members"}</TableCell>
                  {canSchedule && (
                    <TableCell className="text-right">
                      {moving?.id === s.id ? (
                        <>
                          <Button
                            size="sm"
                            disabled={!moving.when}
                            loading={rescheduleMutation.isPending}
                            onClick={() => rescheduleMutation.mutate(moving)}
                          >
                            Save
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setMoving(null)}>
                            Back
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setMoving({ id: s.id, when: "" })}
                          >
                            Reschedule
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-danger-600 hover:bg-danger-50 hover:text-danger-700"
                            loading={cancelMutation.isPending}
                            onClick={() => cancelMutation.mutate(s.id)}
                          >
                            Cancel schedule
                          </Button>
                        </>
                      )}
                    </TableCell>
                  )}
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
// Counselling for members (#18/#19/#30/#31/#61)
// ---------------------------------------------------------------------------

const slotLabel = (start: string) => new Date(start).toLocaleString();

export function MemberCounsellingCard({
  orgId,
  members,
  canAct,
}: {
  orgId: number;
  members: OrganizationMember[];
  canAct: boolean;
}) {
  const queryClient = useQueryClient();
  const {
    data: assignments = [],
    isSuccess,
    isError,
    error: assignmentsError,
  } = useAssignments(orgId);
  const licensed = assignments.some((a) => a.item_type === "counseling");
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    counselee: "",
    counsellor: "",
    timeslot: "",
    topic: "",
    mode: "online" as "online" | "offline",
  });
  const KEY = [...ORG_KEY(orgId), "counseling-sessions"];

  const { data: sessions = [] } = useQuery({
    queryKey: KEY,
    queryFn: () => listOrgCounselingSessions(orgId),
    enabled: licensed,
  });
  const { data: counsellors = [] } = useQuery({
    queryKey: [...ORG_KEY(orgId), "counsellors"],
    queryFn: () => listOrgCounsellors(orgId),
    enabled: licensed && canAct,
  });
  const { data: slots = [] } = useQuery({
    queryKey: [...ORG_KEY(orgId), "counsellor-slots", Number(form.counsellor)],
    queryFn: () => listOrgCounsellorSlots(orgId, Number(form.counsellor)),
    enabled: licensed && canAct && !!form.counsellor,
  });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: KEY });
    void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "counsellor-slots"] });
    setError(null);
  };
  const bookMutation = useMutation({
    mutationFn: () =>
      bookCounselingForMember(orgId, {
        counselee: Number(form.counselee),
        counsellor: Number(form.counsellor),
        timeslot: Number(form.timeslot),
        topic: form.topic.trim(),
        mode: form.mode,
      }),
    onSuccess: () => {
      refresh();
      setForm({ ...form, timeslot: "", topic: "" });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  // A failed load says so instead of hiding the card silently.
  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Counselling for members</CardTitle>
        </CardHeader>
        <CardContent>
          <ErrorNote
            error={`Could not load this organization's counselling licence. ${extractApiError(assignmentsError)}`}
          />
        </CardContent>
      </Card>
    );
  }
  if (!isSuccess) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Counselling for members</CardTitle>
      </CardHeader>
      <CardContent>
        {!licensed ? (
          <p className="text-sm text-slate-500">
            Counselling is not licensed to this organization. CJ Admin can license it under Licensed
            content.
          </p>
        ) : (
          <>
            <p className="mb-3 text-sm text-slate-500">
              Book a session with a counsellor for a member — no fee for the member (licensed). The
              counsellor confirms it; the member and counsellor are notified of every change.
            </p>
            <ErrorNote error={error} />
            {canAct && (
              <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
                <select
                  aria-label="Member"
                  className={SELECT}
                  value={form.counselee}
                  onChange={(e) => setForm({ ...form, counselee: e.target.value })}
                >
                  <option value="">Member…</option>
                  {learners(members).map((m) => (
                    <option key={m.user.id} value={m.user.id}>
                      {memberName(m.user)}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Counsellor"
                  className={SELECT}
                  value={form.counsellor}
                  onChange={(e) => setForm({ ...form, counsellor: e.target.value, timeslot: "" })}
                >
                  <option value="">Counsellor…</option>
                  {counsellors.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.full_name}
                      {c.category_names?.length ? ` — ${c.category_names.join(", ")}` : ""}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Time slot"
                  className={SELECT}
                  value={form.timeslot}
                  disabled={!form.counsellor}
                  onChange={(e) => setForm({ ...form, timeslot: e.target.value })}
                >
                  <option value="">
                    {form.counsellor && slots.length === 0 ? "No open slots" : "Time slot…"}
                  </option>
                  {slots.map((s) => (
                    <option key={s.id} value={s.id}>
                      {slotLabel(s.start_time)}
                    </option>
                  ))}
                </select>
                <Input
                  aria-label="Topic"
                  placeholder="Topic / issue for counselling"
                  className="sm:col-span-2"
                  value={form.topic}
                  onChange={(e) => setForm({ ...form, topic: e.target.value })}
                />
                <div className="flex flex-wrap gap-2">
                  <select
                    aria-label="Mode"
                    className={`${SELECT} flex-1`}
                    value={form.mode}
                    onChange={(e) =>
                      setForm({ ...form, mode: e.target.value as "online" | "offline" })
                    }
                  >
                    <option value="online">Online</option>
                    <option value="offline">Offline</option>
                  </select>
                  <Button
                    size="sm"
                    className="h-10"
                    disabled={
                      !form.counselee ||
                      !form.timeslot ||
                      !form.topic.trim() ||
                      bookMutation.isPending
                    }
                    onClick={() => bookMutation.mutate()}
                  >
                    Book
                  </Button>
                </div>
              </div>
            )}
            {sessions.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-8 text-center text-sm text-slate-500">
                No sessions booked for members yet.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Member</TableHead>
                    <TableHead>Counsellor</TableHead>
                    <TableHead>When</TableHead>
                    <TableHead>Status</TableHead>
                    {canAct && <TableHead className="text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <MemberSessionRow
                      key={s.id}
                      orgId={orgId}
                      session={s}
                      canAct={canAct}
                      onChanged={refresh}
                      onError={setError}
                    />
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function MemberSessionRow({
  orgId,
  session,
  canAct,
  onChanged,
  onError,
}: {
  orgId: number;
  session: CounselingSession;
  canAct: boolean;
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const [mode, setMode] = useState<"idle" | "reschedule" | "cancel">("idle");
  const [slotId, setSlotId] = useState("");
  const [reason, setReason] = useState("");
  const { data: slots = [] } = useQuery({
    queryKey: [...ORG_KEY(orgId), "counsellor-slots", session.counsellor],
    queryFn: () => listOrgCounsellorSlots(orgId, session.counsellor),
    enabled: mode === "reschedule",
  });
  const finish = () => {
    setMode("idle");
    setSlotId("");
    setReason("");
    onChanged();
  };
  const rescheduleMutation = useMutation({
    mutationFn: () => rescheduleMemberCounseling(orgId, session.id, Number(slotId)),
    onSuccess: finish,
    onError: (err) => onError(extractApiError(err)),
  });
  const cancelMutation = useMutation({
    mutationFn: () => cancelMemberCounseling(orgId, session.id, reason.trim()),
    onSuccess: finish,
    onError: (err) => onError(extractApiError(err)),
  });
  const open = session.status === "pending" || session.status === "confirmed";

  return (
    <TableRow>
      <TableCell className="font-medium text-slate-900">
        {session.counselee_name || session.counselee_email}
      </TableCell>
      <TableCell className="text-slate-500">{session.counsellor_name}</TableCell>
      <TableCell className="text-slate-500">
        {session.timeslot_detail ? slotLabel(session.timeslot_detail.start_time) : "—"}
      </TableCell>
      <TableCell>
        <Badge variant={session.status === "cancelled" ? "danger" : "outline"}>
          {session.status}
        </Badge>
      </TableCell>
      {canAct && (
        <TableCell className="text-right">
          {!open ? null : mode === "reschedule" ? (
            <div className="flex justify-end gap-2">
              <select
                aria-label="New time slot"
                className={SELECT}
                value={slotId}
                onChange={(e) => setSlotId(e.target.value)}
              >
                <option value="">{slots.length === 0 ? "No open slots" : "New slot…"}</option>
                {slots.map((s) => (
                  <option key={s.id} value={s.id}>
                    {slotLabel(s.start_time)}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                disabled={!slotId}
                loading={rescheduleMutation.isPending}
                onClick={() => rescheduleMutation.mutate()}
              >
                Save
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setMode("idle")}>
                Back
              </Button>
            </div>
          ) : mode === "cancel" ? (
            <div className="flex justify-end gap-2">
              <Input
                aria-label="Reason for cancelling"
                placeholder="Reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <Button
                variant="danger"
                size="sm"
                disabled={!reason.trim()}
                loading={cancelMutation.isPending}
                onClick={() => cancelMutation.mutate()}
              >
                Cancel session
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setMode("idle")}>
                Back
              </Button>
            </div>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => setMode("reschedule")}>
                Reschedule
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger-600 hover:bg-danger-50 hover:text-danger-700"
                onClick={() => setMode("cancel")}
              >
                Cancel
              </Button>
            </>
          )}
        </TableCell>
      )}
    </TableRow>
  );
}
