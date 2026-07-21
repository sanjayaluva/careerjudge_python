/**
 * Training Course Editor — create or edit a course.
 *
 * Route: /training/new (create) or /training/:id/edit (edit)
 *
 * Form fields:
 *  - Title (required)
 *  - Objective
 *  - Description
 *  - Category (dropdown)
 *  - Course type (online-standard / online-live / offline-live)
 *  - Schedule type (scheduled / non-scheduled)
 *  - Duration days (scheduled only)
 *  - Price
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

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
  useToast,
} from "@/components/ui";
import {
  COURSE_TYPES,
  SCHEDULE_TYPES,
  createCategory,
  createCourse,
  listCategories,
  retrieveCourse,
  updateCourse,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const TRAINING_KEY = ["training", "courses"];

export default function TrainingCourseEditorPage() {
  const { id } = useParams<{ id: string }>();
  const cid = Number(id);
  const isEditMode = !Number.isNaN(cid);
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManage = ["cj_admin", "trainer"].includes(user?.role ?? "");

  // Load categories for the dropdown
  const { data: categories } = useQuery({
    queryKey: ["training", "categories"],
    queryFn: () => listCategories(),
  });

  // Load existing course if editing
  const { data: course, isLoading } = useQuery({
    queryKey: ["training", "courses", cid],
    queryFn: () => retrieveCourse(cid),
    enabled: isEditMode,
  });

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      isEditMode ? updateCourse(cid, payload) : createCourse(payload),
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: TRAINING_KEY });
      toast.success(isEditMode ? "Course updated." : "Course created.");
      navigate(`/training/${saved.id}`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isEditMode && isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <button onClick={() => navigate(-1)} className="text-sm text-primary-600 hover:underline">
          ← Back
        </button>
        <h1 className="mt-2 text-xl font-bold text-slate-900">
          {isEditMode ? "Edit Course" : "Create Course"}
        </h1>
      </div>

      {isEditMode && course?.status !== "draft" && (
        <Alert variant="warning">
          <AlertDescription>
            This course is published. Edits are limited to admin users only.
          </AlertDescription>
        </Alert>
      )}

      <CourseForm
        course={isEditMode ? course : undefined}
        categories={categories ?? []}
        loading={saveMutation.isPending}
        onSubmit={(payload) => saveMutation.mutate(payload)}
      />

      {canManage && <CategoryManager />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Category Manager — create new training categories inline
// ---------------------------------------------------------------------------

function CategoryManager() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [newCategory, setNewCategory] = useState("");

  const { data: categories } = useQuery({
    queryKey: ["training", "categories"],
    queryFn: () => listCategories(),
  });

  const createMutation = useMutation({
    mutationFn: () => createCategory({ name: newCategory }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "categories"] });
      toast.success("Category created.");
      setNewCategory("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Categories</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-slate-500">
          Manage training categories. Courses are organized under these categories.
        </p>
        {(categories ?? []).length > 0 && (
          <div className="flex flex-wrap gap-2">
            {(categories ?? []).map((c) => (
              <Badge key={c.id} variant="outline">
                {c.name}
              </Badge>
            ))}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="flex items-end gap-2"
        >
          <div className="flex-1">
            <Label htmlFor="new-cat" required>
              New category name
            </Label>
            <Input
              id="new-cat"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              placeholder="e.g., Leadership"
              required
            />
          </div>
          <Button type="submit" loading={createMutation.isPending} disabled={!newCategory}>
            Add category
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function CourseForm({
  course,
  categories,
  loading,
  onSubmit,
}: {
  course?: {
    title: string;
    objective: string;
    description: string;
    category: number | null;
    course_type: string;
    schedule_type: string;
    duration_days: number | null;
    price: string;
  };
  categories: { id: number; name: string }[];
  loading: boolean;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [title, setTitle] = useState(course?.title ?? "");
  const [objective, setObjective] = useState(course?.objective ?? "");
  const [description, setDescription] = useState(course?.description ?? "");
  const [categoryId, setCategoryId] = useState(course?.category ? String(course.category) : "");
  const [courseType, setCourseType] = useState(course?.course_type ?? "online_standard");
  const [scheduleType, setScheduleType] = useState(course?.schedule_type ?? "non_scheduled");
  const [durationDays, setDurationDays] = useState(
    course?.duration_days ? String(course.duration_days) : "30",
  );
  const [price, setPrice] = useState(course?.price ?? "0");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Course Details</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const payload: Record<string, unknown> = {
              title,
              objective,
              description,
              course_type: courseType,
              schedule_type: scheduleType,
              price,
            };
            if (categoryId) payload.category = Number(categoryId);
            if (scheduleType === "scheduled") {
              payload.duration_days = Number(durationDays);
            }
            onSubmit(payload);
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="title" required>
              Title
            </Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Python Programming Basics"
              required
            />
          </div>

          <div>
            <Label htmlFor="objective">Objective</Label>
            <textarea
              id="objective"
              rows={2}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="What will students learn?"
            />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              rows={3}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed course description..."
            />
          </div>

          <div>
            <Label htmlFor="category">Category</Label>
            <select
              id="category"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">No category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="course-type">Course type</Label>
              <select
                id="course-type"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={courseType}
                onChange={(e) => setCourseType(e.target.value)}
              >
                {COURSE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="schedule-type">Schedule type</Label>
              <select
                id="schedule-type"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={scheduleType}
                onChange={(e) => setScheduleType(e.target.value)}
              >
                {SCHEDULE_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {scheduleType === "scheduled" && (
            <div>
              <Label htmlFor="duration" required>
                Duration (days)
              </Label>
              <Input
                id="duration"
                type="number"
                min="1"
                value={durationDays}
                onChange={(e) => setDurationDays(e.target.value)}
                placeholder="e.g., 30"
                required
              />
              <p className="mt-1 text-xs text-slate-500">
                Total time allowed for course completion. The countdown starts when a student
                registers.
              </p>
            </div>
          )}

          <div>
            <Label htmlFor="price" required>
              Price (USD)
            </Label>
            <Input
              id="price"
              type="number"
              min="0"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              required
            />
            <p className="mt-1 text-xs text-slate-500">
              Set to 0 for free courses. Students pay this on registration.
            </p>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            <Button type="button" variant="outline" onClick={() => window.history.back()}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              {course ? "Save changes" : "Create course"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
