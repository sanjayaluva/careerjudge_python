/**
 * Training page — list published courses + view my registrations.
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
  useToast,
} from "@/components/ui";
import { COURSE_TYPES, listCourses, listMyCourses, registerForCourse } from "@/api/training";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const TRAINING_KEY = ["training", "courses"];

export default function TrainingPage() {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const canManage = ["cj_admin", "trainer"].includes(user?.role ?? "");

  const { data, isLoading } = useQuery({
    queryKey: [...TRAINING_KEY, debouncedSearch, "published"],
    queryFn: () =>
      listCourses({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        status: "published",
      }),
  });

  const { data: myCourses } = useQuery({
    queryKey: ["training", "my-courses"],
    queryFn: () => listMyCourses(),
  });

  const registerMutation = useMutation({
    mutationFn: (courseId: number) => registerForCourse(courseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "my-courses"] });
      toast.success("Registered for course. Payment pending.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const courses = data?.results ?? [];
  const myRegs = myCourses ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6">
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

        <Tabs defaultValue="browse">
          <TabsList className="px-6">
            <TabsTrigger value="browse">Browse Courses</TabsTrigger>
            <TabsTrigger value="my-courses">My Courses ({myRegs.length})</TabsTrigger>
          </TabsList>

          {/* === Browse Tab === */}
          <TabsContent value="browse" className="p-6 pt-4">
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
                    <TableHead>Registrations</TableHead>
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
                      <TableCell className="text-slate-500">{c.registration_count}</TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => registerMutation.mutate(c.id)}
                          loading={registerMutation.isPending}
                        >
                          Register
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>

          {/* === My Courses Tab === */}
          <TabsContent value="my-courses" className="p-6 pt-4">
            {myRegs.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                You haven&apos;t registered for any courses yet.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Course</TableHead>
                    <TableHead>Payment</TableHead>
                    <TableHead>Progress</TableHead>
                    <TableHead>Registered</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {myRegs.map((r) => (
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
                        <Badge
                          variant={r.completion_status === "completed" ? "success" : "default"}
                        >
                          {r.completion_status.replace("_", " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {new Date(r.registered_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Link to={`/training/${r.course}`}>
                          <Button size="sm" variant="outline">
                            Continue
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>
        </Tabs>
      </PageCard>
    </div>
  );
}
