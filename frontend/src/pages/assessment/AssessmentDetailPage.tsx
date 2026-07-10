/**
 * Assessment Detail Page — shows assessment config with tabs:
 * - Overview: assessment properties + edit
 * - Sections: hierarchical section tree + CRUD
 * - Questions: assign question bank questions to sections
 * - Sessions: list sessions for this assessment
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
  Input,
  Label,
  Modal,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui";
import {
  type AssessmentDetail,
  type AssessmentSection,
  ATTEMPT_RULES,
  NAVIGATION_RULES,
  createSection,
  publishAssessment,
  retrieveAssessment,
  startSession,
} from "@/api/assessment";
import { extractApiError } from "@/api/client";
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
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [sectionModal, setSectionModal] = useState<{
    open: boolean;
    parent: number | null;
  }>({ open: false, parent: null });

  const canManage = ["cj_admin", "corp_admin", "psychometrician"].includes(user?.role ?? "");

  const { data: assessment, isLoading } = useQuery({
    queryKey: ["assessments", aid],
    queryFn: () => retrieveAssessment(aid),
    enabled: !Number.isNaN(aid),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishAssessment(aid),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["assessments", aid] }),
    onError: (err) => setError(extractApiError(err)),
  });

  const startSessionMutation = useMutation({
    mutationFn: () => startSession(aid),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["assessments", aid] }),
    onError: (err) => setError(extractApiError(err)),
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
      setSectionModal({ open: false, parent: null });
    },
    onError: (err) => setError(extractApiError(err)),
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

  return (
    <div className="space-y-6 p-6">
      {error && (
        <Alert variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

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
          <TabsTrigger value="sections">Sections ({a.sections.length})</TabsTrigger>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
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

              <div className="mt-6 flex gap-2 border-t border-slate-100 pt-4">
                {a.status === "draft" && canManage && (
                  <Button
                    loading={publishMutation.isPending}
                    onClick={() => publishMutation.mutate()}
                  >
                    Publish Assessment
                  </Button>
                )}
                {a.status === "published" && (
                  <Button
                    loading={startSessionMutation.isPending}
                    onClick={() => startSessionMutation.mutate()}
                  >
                    Start Session
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* === SECTIONS TAB === */}
        <TabsContent value="sections">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Sections (Variable Structure)</CardTitle>
                {canManage && a.status === "draft" && (
                  <Button size="sm" onClick={() => setSectionModal({ open: true, parent: null })}>
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
                      canManage={canManage && a.status === "draft"}
                      onAddSubsection={(parentId) =>
                        setSectionModal({ open: true, parent: parentId })
                      }
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === SESSIONS TAB === */}
        <TabsContent value="sessions">
          <Card>
            <CardHeader>
              <CardTitle>Assessment Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="py-4 text-center text-sm text-slate-500">
                Session management will be available here once the assessment is published and
                candidates start taking it.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <CreateSectionModal
        open={sectionModal.open}
        parentId={sectionModal.parent}
        loading={sectionCreateMutation.isPending}
        onClose={() => setSectionModal({ open: false, parent: null })}
        onSubmit={(payload) => sectionCreateMutation.mutate(payload)}
      />
    </div>
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
}: {
  section: AssessmentSection;
  depth: number;
  canManage: boolean;
  onAddSubsection: (parentId: number) => void;
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
        </div>
        {canManage && depth < 3 && (
          <Button variant="ghost" size="sm" onClick={() => onAddSubsection(section.id)}>
            + Sub-section
          </Button>
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
          />
        ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Create Section Modal
// ---------------------------------------------------------------------------

function CreateSectionModal({
  open,
  parentId,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  parentId: number | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    parent?: number | null;
    description?: string;
    level?: number;
  }) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={parentId ? "Add Sub-Section" : "Add Section"}
      description={
        parentId
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
            level: parentId ? 2 : 1, // TODO: calculate level from parent
          });
          setTitle("");
          setDescription("");
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
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create section
          </Button>
        </div>
      </form>
    </Modal>
  );
}
