/**
 * Training page — list published courses + view my registrations (My Courses:
 * New / Ongoing / Completed, Report 9 #79).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  Input,
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
  Modal,
  useToast,
} from "@/components/ui";
import {
  COURSE_TYPES,
  completionStatusLabel,
  completionStatusVariant,
  deleteCourse,
  listCourses,
  listMyCourses,
  registerForCourse,
  type CourseRegistration,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { PrivateSpaceNote } from "@/components/PrivateSpaceNote";
import { useAuth } from "@/hooks/useAuth";
import { usePrivateSpace } from "@/hooks/usePrivateSpace";
import { RegistrationFormModal, type RegistrationForm } from "./RegistrationFormModal";

const TRAINING_KEY = ["training", "courses"];

export default function TrainingPage() {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  // Report 9 #47: the Corporate Exclusive Admin builds his organization's
  // private courses (CJ courses licensed to him stay read-only).
  const { isPrivateAuthor, ownsItem } = usePrivateSpace();
  const canManage = ["cj_admin", "trainer", "corp_exclusive"].includes(user?.role ?? "");
  // Report 9 #116: only learners register (CJ Admin may too, to test a course).
  const canRegister = ["individual", "cj_admin"].includes(user?.role ?? "");
  const [deleting, setDeleting] = useState<{
    id: number;
    title: string;
    status: string;
    registration_count: number;
  } | null>(null);
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteCourse(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TRAINING_KEY });
      toast.success("Course deleted.");
      setDeleting(null);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const { data, isLoading } = useQuery({
    queryKey: [...TRAINING_KEY, debouncedSearch, "published"],
    queryFn: () =>
      listCourses({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        status: "published",
      }),
  });

  // Trainers see ALL their courses (including drafts) in a separate tab
  const { data: myCoursesData } = useQuery({
    queryKey: [...TRAINING_KEY, debouncedSearch, "all"],
    queryFn: () =>
      listCourses({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
      }),
    enabled: canManage,
  });

  const { data: myCourses } = useQuery({
    queryKey: ["training", "my-courses"],
    queryFn: () => listMyCourses(),
  });

  // Report 8 #13: Register opens the registration form first.
  const [registerFor, setRegisterFor] = useState<{ id: number; title: string } | null>(null);
  const registerMutation = useMutation({
    mutationFn: (v: { courseId: number; form: RegistrationForm }) =>
      registerForCourse(v.courseId, undefined, v.form),
    onSuccess: (data) => {
      setRegisterFor(null);
      void queryClient.invalidateQueries({ queryKey: ["training", "my-courses"] });
      void queryClient.invalidateQueries({ queryKey: TRAINING_KEY });
      // Report 3 §1.3: paid courses return a Stripe checkout URL — redirect.
      if (data.checkout_url) {
        toast.success("Redirecting to payment…");
        window.location.href = data.checkout_url;
        return;
      }
      toast.success(
        data.payment_status === "paid"
          ? "Registered! You can start the course now."
          : "Registered for course. Payment pending.",
      );
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const courses = data?.results ?? [];
  const allCourses = (myCoursesData?.results ?? []).filter((c) => !isPrivateAuthor || ownsItem(c));
  const myRegs = myCourses ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6 pb-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Training</h1>
            <p className="text-sm text-slate-500">
              {data?.count ?? 0} published course{(data?.count ?? 0) !== 1 ? "s" : ""}
            </p>
          </div>
          {canManage && (
            <Link to="/training/new">
              <Button>Create course</Button>
            </Link>
          )}
        </div>

        <div className="px-6 pb-4 empty:hidden">
          <PrivateSpaceNote what="training courses" />
        </div>
        <Tabs defaultValue="browse">
          <div className="px-6">
            <TabsList>
              <TabsTrigger value="browse">Browse Courses</TabsTrigger>
              {canManage && (
                <TabsTrigger value="manage">Manage Courses ({allCourses.length})</TabsTrigger>
              )}
              <TabsTrigger value="my-courses">My Courses ({myRegs.length})</TabsTrigger>
            </TabsList>
          </div>

          {/* === Browse Tab === */}
          <TabsContent value="browse" className="px-6 py-4">
            <Input
              type="search"
              placeholder="Search courses..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setTimeout(() => setDebouncedSearch(e.target.value), 350);
              }}
              className="max-w-sm"
            />
            {isLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : courses.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                No published courses available yet.
              </p>
            ) : (
              <Table className="mt-4">
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Price</TableHead>
                    {/* Report 9 #83: learners don't see who / how many registered. */}
                    {canManage && <TableHead>Registrations</TableHead>}
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {courses.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium text-slate-900">
                        <Link to={`/training/${c.id}`} className="text-primary-600 hover:underline">
                          {c.title}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {COURSE_TYPES.find((t) => t.value === c.course_type)?.label ??
                            c.course_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">{c.category_name ?? "—"}</TableCell>
                      <TableCell className="text-slate-500">${c.price}</TableCell>
                      {canManage && (
                        <TableCell className="text-slate-500">{c.registration_count}</TableCell>
                      )}
                      <TableCell>
                        {myRegs.some((r) => r.course === c.id) ? (
                          <Badge variant="success">Registered</Badge>
                        ) : !canRegister ? null : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setRegisterFor({ id: c.id, title: c.title })}
                          >
                            Register
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>

          {/* === Manage Courses Tab (trainers/admins only) === */}
          {canManage && (
            <TabsContent value="manage" className="px-6 py-4">
              {allCourses.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-500">
                  No courses yet. Click &quot;Create course&quot; to get started.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Registrations</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allCourses.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell className="font-medium text-slate-900">
                          <Link
                            to={`/training/${c.id}`}
                            className="text-primary-600 hover:underline"
                          >
                            {c.title}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {COURSE_TYPES.find((t) => t.value === c.course_type)?.label ??
                              c.course_type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              c.status === "published"
                                ? "success"
                                : c.status === "archived"
                                  ? "warning"
                                  : "default"
                            }
                          >
                            {c.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">${c.price}</TableCell>
                        <TableCell className="text-slate-500">{c.registration_count}</TableCell>
                        <TableCell className="text-slate-500">
                          {new Date(c.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Link to={`/training/${c.id}/edit`}>
                              <Button size="sm" variant="outline">
                                Edit
                              </Button>
                            </Link>
                            {/* R8-34: CJ Admin deletes any course; R8-35: a
                                trainer deletes their own draft. */}
                            {(user?.role === "cj_admin" ||
                              ownsItem(c) ||
                              (c.status === "draft" && c.created_by === user?.id)) && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-danger-600"
                                onClick={() => setDeleting(c)}
                              >
                                Delete
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </TabsContent>
          )}

          {/* === My Courses Tab (Report 9 #79) === */}
          <TabsContent value="my-courses" className="px-6 py-4">
            <MyCoursesTabs registrations={myRegs} />
          </TabsContent>
        </Tabs>
      </PageCard>
      <Modal
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title="Delete course"
        size="sm"
      >
        <p className="text-sm text-slate-700">
          Delete <strong>{deleting?.title}</strong>? This removes its structure, content and
          registrations and cannot be undone.
          {deleting && deleting.registration_count > 0 && (
            <span className="mt-2 block text-warning-700">
              ⚠ {deleting.registration_count} student(s) are registered.
            </span>
          )}
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDeleting(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deleting && deleteMutation.mutate(deleting.id)}
          >
            Delete course
          </Button>
        </div>
      </Modal>
      <RegistrationFormModal
        open={registerFor !== null}
        courseTitle={registerFor?.title ?? ""}
        submitting={registerMutation.isPending}
        onClose={() => setRegisterFor(null)}
        onSubmit={(form) =>
          registerFor && registerMutation.mutate({ courseId: registerFor.id, form })
        }
      />
    </div>
  );
}

// Report 9 #79: My Courses split by completion status — New (not started,
// "Begin Course"), Ongoing (in progress, "Resume Course") and Completed
// (completed, or the duration ran out: "Show Results"). A registration is
// "not started" until the learner opens the course (Report 8.1 #62).
const MY_COURSE_GROUPS: {
  value: string;
  label: string;
  statuses: string[];
  action: string;
  empty: string;
}[] = [
  {
    value: "new",
    label: "New Courses",
    statuses: ["not_started"],
    action: "Begin Course",
    empty: "No new courses. Register for one under Browse Courses.",
  },
  {
    value: "ongoing",
    label: "Ongoing Courses",
    statuses: ["in_progress"],
    action: "Resume Course",
    empty: "No courses in progress.",
  },
  {
    value: "completed",
    label: "Completed Courses",
    statuses: ["completed", "expired"],
    action: "Show Results",
    empty: "No completed courses yet.",
  },
];

function MyCoursesTabs({ registrations }: { registrations: CourseRegistration[] }) {
  if (registrations.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        You haven&apos;t registered for any courses yet.
      </p>
    );
  }
  const firstWithCourses =
    MY_COURSE_GROUPS.find((g) =>
      registrations.some((r) => g.statuses.includes(r.completion_status)),
    )?.value ?? "new";
  return (
    <Tabs defaultValue={firstWithCourses}>
      <TabsList>
        {MY_COURSE_GROUPS.map((g) => (
          <TabsTrigger key={g.value} value={g.value}>
            {g.label} (
            {registrations.filter((r) => g.statuses.includes(r.completion_status)).length})
          </TabsTrigger>
        ))}
      </TabsList>
      {MY_COURSE_GROUPS.map((g) => {
        const rows = registrations.filter((r) => g.statuses.includes(r.completion_status));
        return (
          <TabsContent key={g.value} value={g.value} className="pt-4">
            {rows.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">{g.empty}</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Course</TableHead>
                    <TableHead>Payment</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Registered</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium text-slate-900">
                        <Link
                          to={`/training/${r.course}`}
                          className="text-primary-600 hover:underline"
                        >
                          {r.course_title}
                        </Link>
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
                        <Badge variant={completionStatusVariant(r.completion_status)}>
                          {completionStatusLabel(r.completion_status)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {new Date(r.registered_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {/* The course opens on Learn: the player starts or
                            resumes it, and shows the results once finished. */}
                        <Link to={`/training/${r.course}`}>
                          <Button
                            size="sm"
                            variant={g.value === "completed" ? "outline" : "primary"}
                          >
                            {g.action}
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>
        );
      })}
    </Tabs>
  );
}
