/**
 * Career Profiling Solution Detail Page — tabs:
 * - Overview: solution properties + publish
 * - Assessments: select 2-3 assessments with labels
 * - Bands: define bands per variable (range + code)
 * - Criteria: define criterion band codes per career/role
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
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
  type MatchIndex,
  type ProfilingSolution,
  addSolutionAssessment,
  computeSolution,
  createBand,
  createBandDefinition,
  createCriterion,
  createMappingRule,
  createPolarMatchRule,
  createRankDefinition,
  deleteRankDefinition,
  downloadCriteriaTemplate,
  listAssessments,
  listMappingRules,
  listMatchIndices,
  listPolarMatchRules,
  listRankDefinitions,
  publishSolution,
  retrieveSolution,
  uploadCriteriaCsv,
} from "@/api/careerProfiling";
import { type AssessmentSection, listSections } from "@/api/assessment";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function ProfilingSolutionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const sid = Number(id);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();

  const canManage = ["cj_admin", "psychometrician"].includes(user?.role ?? "");

  const { data: solution, isLoading } = useQuery({
    queryKey: ["career-profiling", "solutions", sid],
    queryFn: () => retrieveSolution(sid),
    enabled: !Number.isNaN(sid),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishSolution(sid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["career-profiling", "solutions", sid] });
      toast.success("Solution published.");
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

  if (!solution) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load profiling solution.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link to="/career-profiling" className="text-sm text-primary-600 hover:underline">
          ← Back to Career Profiling
        </Link>
        <div className="mt-2 flex items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">{solution.title}</h1>
          <Badge variant={STATUS_VARIANTS[solution.status] ?? "default"}>{solution.status}</Badge>
          {solution.has_polar_assessment && <Badge variant="warning">Polar</Badge>}
        </div>
        {solution.purpose && <p className="mt-1 text-sm text-slate-500">{solution.purpose}</p>}
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="assessments">
            Assessments ({solution.selected_assessments?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="bands">Bands</TabsTrigger>
          <TabsTrigger value="mapping-rules">Mapping Rules</TabsTrigger>
          <TabsTrigger value="rank-chart">Rank Chart</TabsTrigger>
          {solution.has_polar_assessment && (
            <TabsTrigger value="polar-rules">Polar Match Rules</TabsTrigger>
          )}
          <TabsTrigger value="criteria">Criteria</TabsTrigger>
          <TabsTrigger value="match-indices">Match Indices</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Solution Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Status
                  </dt>
                  <dd className="text-sm text-slate-900">{solution.status}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Has Polar Assessment
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {solution.has_polar_assessment ? "Yes" : "No"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Assessments Selected
                  </dt>
                  <dd className="text-sm text-slate-900">
                    {solution.selected_assessments?.length ?? 0} (min 2, max 3)
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created by
                  </dt>
                  <dd className="text-sm text-slate-900">{solution.created_by_name ?? "—"}</dd>
                </div>
              </dl>

              {solution.description && (
                <div className="mt-4">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Description
                  </dt>
                  <dd className="mt-1 rounded-md bg-slate-50 p-3 text-sm text-slate-900">
                    {solution.description}
                  </dd>
                </div>
              )}

              <div className="mt-6 flex gap-2 border-t border-slate-100 pt-4">
                {solution.status === "draft" && canManage && (
                  <Button
                    loading={publishMutation.isPending}
                    disabled={(solution.selected_assessments?.length ?? 0) < 2}
                    title={
                      (solution.selected_assessments?.length ?? 0) < 2
                        ? "Select at least 2 assessments before publishing"
                        : undefined
                    }
                    onClick={() => publishMutation.mutate()}
                  >
                    Publish Solution
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Assessments Tab */}
        <TabsContent value="assessments">
          <AssessmentsTab solutionId={sid} solution={solution} canManage={canManage} />
        </TabsContent>

        {/* Bands Tab */}
        <TabsContent value="bands">
          <BandsTab solutionId={sid} solution={solution} canManage={canManage} />
        </TabsContent>

        {/* Standard Mapping Rules Tab — SRS §4.1.2 (n×n grid) */}
        <TabsContent value="mapping-rules">
          <StandardMappingRulesTab solutionId={sid} canManage={canManage} />
        </TabsContent>

        {/* Criteria Tab */}
        <TabsContent value="criteria">
          <CriteriaTab solutionId={sid} solution={solution} canManage={canManage} />
        </TabsContent>

        {/* Rank Chart Tab — SRS §4.1.3 + §4.2.3 */}
        <TabsContent value="rank-chart">
          <RankChartTab solutionId={sid} solution={solution} canManage={canManage} />
        </TabsContent>

        {/* Polar Match Rules Tab — SRS §4.2.2 (polar solutions only) */}
        {solution.has_polar_assessment && (
          <TabsContent value="polar-rules">
            <PolarMatchRulesTab solutionId={sid} canManage={canManage} />
          </TabsContent>
        )}

        {/* Match Indices Tab — view computed results per candidate */}
        <TabsContent value="match-indices">
          <MatchIndicesTab solutionId={sid} canManage={canManage} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Assessments Tab
// ---------------------------------------------------------------------------

function AssessmentsTab({
  solutionId,
  solution,
  canManage,
}: {
  solutionId: number;
  solution: ProfilingSolution;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [addOpen, setAddOpen] = useState(false);

  const { data: availableAssessments } = useQuery({
    queryKey: ["assessments", "for-profiling"],
    queryFn: () => listAssessments({ status: "published" }),
  });

  const addMutation = useMutation({
    mutationFn: (payload: { assessment: number; label: string; is_polar?: boolean }) =>
      addSolutionAssessment(solutionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId],
      });
      setAddOpen(false);
      toast.success("Assessment added.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const selectedIds = new Set((solution.selected_assessments ?? []).map((sa) => sa.assessment));

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            Selected Assessments ({solution.selected_assessments?.length ?? 0}/3)
          </CardTitle>
          {canManage && (solution.selected_assessments?.length ?? 0) < 3 && (
            <Button size="sm" onClick={() => setAddOpen(true)}>
              + Add Assessment
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {(solution.selected_assessments?.length ?? 0) === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No assessments selected yet. Add at least 2 to publish this solution.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Label</TableHead>
                <TableHead>Assessment</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Polar</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {solution.selected_assessments?.map((sa) => (
                <TableRow key={sa.id}>
                  <TableCell className="font-medium text-slate-900">{sa.label}</TableCell>
                  <TableCell className="text-slate-700">
                    {sa.assessment_detail?.title ?? `Assessment #${sa.assessment}`}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{sa.assessment_detail?.assessment_type ?? "—"}</Badge>
                  </TableCell>
                  <TableCell>
                    {sa.is_polar ? <Badge variant="warning">Polar</Badge> : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add Assessment" size="sm">
        <AddAssessmentForm
          available={availableAssessments?.results ?? []}
          alreadySelectedIds={selectedIds}
          loading={addMutation.isPending}
          onCancel={() => setAddOpen(false)}
          onSubmit={(assessment, label, isPolar) =>
            addMutation.mutate({ assessment, label, is_polar: isPolar })
          }
        />
      </Modal>
    </Card>
  );
}

function AddAssessmentForm({
  available,
  alreadySelectedIds,
  loading,
  onCancel,
  onSubmit,
}: {
  available: { id: number; title: string; assessment_type: string }[];
  alreadySelectedIds: Set<number>;
  loading: boolean;
  onCancel: () => void;
  onSubmit: (assessment: number, label: string, isPolar: boolean) => void;
}) {
  const [assessmentId, setAssessmentId] = useState<number | null>(null);
  const [label, setLabel] = useState("");
  const [isPolar, setIsPolar] = useState(false);

  const filtered = available.filter((a) => !alreadySelectedIds.has(a.id));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (assessmentId !== null) onSubmit(assessmentId, label, isPolar);
      }}
      className="space-y-4"
    >
      <div>
        <Label htmlFor="sa-assessment" required>
          Assessment
        </Label>
        <select
          id="sa-assessment"
          className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
          value={assessmentId ?? ""}
          onChange={(e) => setAssessmentId(Number(e.target.value))}
          required
        >
          <option value="">Select an assessment...</option>
          {filtered.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title} ({a.assessment_type})
            </option>
          ))}
        </select>
      </div>
      <div>
        <Label htmlFor="sa-label" required>
          Label (short name for reports)
        </Label>
        <Input
          id="sa-label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g., CAT, CIA"
          required
        />
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={isPolar}
          onChange={(e) => setIsPolar(e.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
        />
        This is a Polar assessment
      </label>
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={loading}>
          Add
        </Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Bands Tab
// ---------------------------------------------------------------------------

function BandsTab({
  solutionId,
  solution,
  canManage,
}: {
  solutionId: number;
  solution: ProfilingSolution;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [addOpen, setAddOpen] = useState(false);
  // CP-2: which band definition we're adding a band row to.
  const [addRowFor, setAddRowFor] = useState<{ bandDefId: number; nextNumber: number } | null>(
    null,
  );

  const createBandMutation = useMutation({
    mutationFn: (payload: { selected_assessment: number; section: number }) =>
      createBandDefinition(solutionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId],
      });
      setAddOpen(false);
      toast.success("Band definition created.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const createBandRowMutation = useMutation({
    mutationFn: (payload: {
      band_definition: number;
      band_number: number;
      range_min: number;
      range_max: number;
      band_code: string;
      sub_variable_name?: string;
    }) => createBand(solutionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId],
      });
      setAddRowFor(null);
      toast.success("Band added.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Flatten all band definitions across assessments
  const allBandDefs =
    solution.selected_assessments?.flatMap((sa) =>
      (sa.band_definitions ?? []).map((bd) => ({
        ...bd,
        assessmentLabel: sa.label,
      })),
    ) ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Band Definitions ({allBandDefs.length})</CardTitle>
          {canManage && (
            <Button size="sm" onClick={() => setAddOpen(true)}>
              + Define Band
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {allBandDefs.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No band definitions yet. Define bands for assessment variables to enable mapping.
          </p>
        ) : (
          <div className="space-y-4">
            {allBandDefs.map((bd) => (
              <div key={bd.id} className="rounded-md border border-slate-200 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Badge variant="primary">{bd.assessmentLabel}</Badge>
                  <span className="text-sm font-medium text-slate-900">{bd.section_title}</span>
                </div>
                {bd.bands.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>#</TableHead>
                        <TableHead>Range</TableHead>
                        <TableHead>Code</TableHead>
                        {bd.bands.some((b) => b.sub_variable_name) && (
                          <TableHead>Sub-variable</TableHead>
                        )}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {bd.bands.map((b) => (
                        <TableRow key={b.id}>
                          <TableCell className="text-slate-500">{b.band_number}</TableCell>
                          <TableCell className="text-slate-700">
                            {b.range_min} - {b.range_max}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{b.band_code}</Badge>
                          </TableCell>
                          {bd.bands.some((x) => x.sub_variable_name) && (
                            <TableCell className="text-slate-500">
                              {b.sub_variable_name || "—"}
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <p className="text-xs text-slate-400">No bands defined yet.</p>
                )}
                {canManage && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2"
                    onClick={() =>
                      setAddRowFor({ bandDefId: bd.id, nextNumber: bd.bands.length + 1 })
                    }
                  >
                    + Add band
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>

      {addOpen && (
        <CreateBandDefinitionModal
          selectedAssessments={solution.selected_assessments ?? []}
          loading={createBandMutation.isPending}
          onClose={() => setAddOpen(false)}
          onSubmit={(saId, sectionId) =>
            createBandMutation.mutate({ selected_assessment: saId, section: sectionId })
          }
        />
      )}

      {addRowFor && (
        <CreateBandRowModal
          bandDefId={addRowFor.bandDefId}
          nextNumber={addRowFor.nextNumber}
          loading={createBandRowMutation.isPending}
          onClose={() => setAddRowFor(null)}
          onSubmit={(payload) => createBandRowMutation.mutate(payload)}
        />
      )}
    </Card>
  );
}

function CreateBandRowModal({
  bandDefId,
  nextNumber,
  loading,
  onClose,
  onSubmit,
}: {
  bandDefId: number;
  nextNumber: number;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    band_definition: number;
    band_number: number;
    range_min: number;
    range_max: number;
    band_code: string;
    sub_variable_name?: string;
  }) => void;
}) {
  const [bandNumber, setBandNumber] = useState(String(nextNumber));
  const [rangeMin, setRangeMin] = useState("");
  const [rangeMax, setRangeMax] = useState("");
  const [bandCode, setBandCode] = useState("");
  const [subVar, setSubVar] = useState("");
  const valid = bandNumber.trim() && rangeMin.trim() && rangeMax.trim() && bandCode.trim();
  return (
    <Modal open onClose={onClose} title="Add band" size="sm">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({
            band_definition: bandDefId,
            band_number: Number(bandNumber),
            range_min: Number(rangeMin),
            range_max: Number(rangeMax),
            band_code: bandCode.trim(),
            ...(subVar.trim() ? { sub_variable_name: subVar.trim() } : {}),
          });
        }}
        className="space-y-3"
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Band #</label>
            <Input
              type="number"
              value={bandNumber}
              onChange={(e) => setBandNumber(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Band code</label>
            <Input
              value={bandCode}
              onChange={(e) => setBandCode(e.target.value)}
              placeholder="e.g. A"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Range min</label>
            <Input
              type="number"
              value={rangeMin}
              onChange={(e) => setRangeMin(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Range max</label>
            <Input
              type="number"
              value={rangeMax}
              onChange={(e) => setRangeMax(e.target.value)}
              required
            />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Sub-variable (optional)
          </label>
          <Input
            value={subVar}
            onChange={(e) => setSubVar(e.target.value)}
            placeholder="For polar variables only"
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading} disabled={!valid}>
            Add band
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CreateBandDefinitionModal({
  selectedAssessments,
  loading,
  onClose,
  onSubmit,
}: {
  selectedAssessments: ProfilingSolution["selected_assessments"];
  loading: boolean;
  onClose: () => void;
  onSubmit: (selectedAssessmentId: number, sectionId: number) => void;
}) {
  const [saId, setSaId] = useState<number | null>(null);
  const [sectionId, setSectionId] = useState("");

  // CP-3: fetch the selected assessment's variables so the user picks from a
  // list instead of typing a raw Section ID.
  const assessmentId = selectedAssessments?.find((sa) => sa.id === saId)?.assessment ?? null;
  const { data: sections } = useQuery({
    queryKey: ["band-def-sections", assessmentId],
    queryFn: () => (assessmentId ? listSections(assessmentId) : Promise.resolve([])),
    enabled: Boolean(assessmentId),
  });
  const sectionOptions: { id: number; label: string }[] = [];
  const walkSections = (list: AssessmentSection[], depth: number) => {
    for (const s of list) {
      sectionOptions.push({ id: s.id, label: `${"— ".repeat(depth)}${s.title} (L${s.level})` });
      if (s.subsections?.length) walkSections(s.subsections, depth + 1);
    }
  };
  walkSections(sections ?? [], 0);
  useEffect(() => {
    setSectionId("");
  }, [saId]);

  return (
    <Modal open onClose={onClose} title="Define Band" size="sm">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (saId !== null && sectionId) onSubmit(saId, Number(sectionId));
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="bd-sa" required>
            Assessment
          </Label>
          <select
            id="bd-sa"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={saId ?? ""}
            onChange={(e) => setSaId(Number(e.target.value))}
            required
          >
            <option value="">Select assessment...</option>
            {selectedAssessments?.map((sa) => (
              <option key={sa.id} value={sa.id}>
                {sa.label} ({sa.assessment_detail?.title})
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="bd-section" required>
            Variable
          </Label>
          <select
            id="bd-section"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm disabled:opacity-50"
            value={sectionId}
            onChange={(e) => setSectionId(e.target.value)}
            disabled={!assessmentId}
            required
          >
            <option value="">
              {assessmentId ? "Select a variable..." : "Choose an assessment first"}
            </option>
            {sectionOptions.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-400">
            Pick the variable (section) to define bands for.
          </p>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Criteria Tab
// ---------------------------------------------------------------------------

function CriteriaTab({
  solutionId,
  solution,
  canManage,
}: {
  solutionId: number;
  solution: ProfilingSolution;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [addOpen, setAddOpen] = useState(false);

  // Variables (sections) with their defined band codes — used to render a
  // validated dropdown instead of free text (D5: criterion band dropdown).
  const variableOptions =
    solution.selected_assessments?.flatMap((sa) =>
      (sa.band_definitions ?? []).map((bd) => ({
        sectionId: bd.section,
        label: `${sa.label} • ${bd.section_title}`,
        bandCodes: (bd.bands ?? []).map((b) => b.band_code),
      })),
    ) ?? [];

  const { data: criteria } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId, "criteria"],
    queryFn: () => import("@/api/careerProfiling").then((m) => m.listCriteria(solutionId)),
    enabled: !Number.isNaN(solutionId),
  });

  const createCriterionMutation = useMutation({
    mutationFn: (payload: {
      career_title: string;
      section: number;
      criterion_band_code: string;
      weight?: number;
    }) => createCriterion(solutionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "criteria"],
      });
      setAddOpen(false);
      toast.success("Mapping criterion created.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // SRS §4.1.4: bulk criterion definition via CSV template upload.
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadCriteriaCsv(solutionId, file),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "criteria"],
      });
      toast.success(
        `Upload complete: ${result.created_count} created, ${result.updated_count} updated` +
          (result.error_count ? `, ${result.error_count} error(s) — see console.` : "."),
      );
      if (result.error_count) {
        console.warn("Criteria upload errors:", result.errors, result.unmatched_variables);
      }
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const handleDownloadTemplate = async () => {
    const blob = await downloadCriteriaTemplate(solutionId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `criteria_template_solution_${solutionId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Group criteria by career title
  const careerGroups: Record<string, NonNullable<typeof criteria>> = {};
  for (const c of criteria ?? []) {
    if (!careerGroups[c.career_title]) careerGroups[c.career_title] = [];
    careerGroups[c.career_title]!.push(c);
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Mapping Criteria ({criteria?.length ?? 0})</CardTitle>
          {canManage && (
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => void handleDownloadTemplate()}>
                Download Template
              </Button>
              <label className="cursor-pointer">
                <span className="inline-flex h-9 items-center rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
                  {uploadMutation.isPending ? "Uploading…" : "Upload CSV"}
                </span>
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  disabled={uploadMutation.isPending}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) uploadMutation.mutate(file);
                    e.target.value = "";
                  }}
                />
              </label>
              <Button size="sm" onClick={() => setAddOpen(true)}>
                + Add Criterion
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {(criteria?.length ?? 0) === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No mapping criteria yet. Define criterion band codes for careers/roles.
          </p>
        ) : (
          <div className="space-y-4">
            {Object.entries(careerGroups).map(([career, crits]) => (
              <div key={career} className="rounded-md border border-slate-200 p-4">
                <p className="mb-2 text-sm font-medium text-slate-900">{career}</p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Variable</TableHead>
                      <TableHead>Criterion Band</TableHead>
                      <TableHead>Weight</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {crits!.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell className="text-slate-700">{c.section_title}</TableCell>
                        <TableCell>
                          <Badge variant="primary">{c.criterion_band_code}</Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">{c.weight}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      {addOpen && (
        <CreateCriterionModal
          loading={createCriterionMutation.isPending}
          variableOptions={variableOptions}
          onClose={() => setAddOpen(false)}
          onSubmit={(career, sectionId, code, weight) =>
            createCriterionMutation.mutate({
              career_title: career,
              section: Number(sectionId),
              criterion_band_code: code,
              weight: weight || 1.0,
            })
          }
        />
      )}
    </Card>
  );
}

function CreateCriterionModal({
  loading,
  variableOptions,
  onClose,
  onSubmit,
}: {
  loading: boolean;
  variableOptions: { sectionId: number; label: string; bandCodes: string[] }[];
  onClose: () => void;
  onSubmit: (career: string, sectionId: string, code: string, weight: number) => void;
}) {
  const [career, setCareer] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [code, setCode] = useState("");
  const [weight, setWeight] = useState("1.0");

  // D5: criterion_band_code is a dropdown constrained to the band codes
  // actually defined for the selected variable (not free text).
  const selectedVariable = variableOptions.find((v) => String(v.sectionId) === sectionId);
  const bandCodes = selectedVariable?.bandCodes ?? [];

  return (
    <Modal open onClose={onClose} title="Add Mapping Criterion" size="sm">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(career, sectionId, code, parseFloat(weight));
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="mc-career" required>
            Career / Role title
          </Label>
          <Input
            id="mc-career"
            value={career}
            onChange={(e) => setCareer(e.target.value)}
            placeholder="e.g., Computer Programmer"
            required
          />
        </div>
        <div>
          <Label htmlFor="mc-section" required>
            Variable
          </Label>
          <select
            id="mc-section"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={sectionId}
            onChange={(e) => {
              setSectionId(e.target.value);
              setCode(""); // reset band code — the choices depend on the variable
            }}
            required
          >
            <option value="">Select a variable…</option>
            {variableOptions.map((v) => (
              <option key={v.sectionId} value={v.sectionId}>
                {v.label}
              </option>
            ))}
          </select>
          {variableOptions.length === 0 && (
            <p className="mt-1 text-xs text-amber-600">
              No banded variables yet — define bands first (Bands tab).
            </p>
          )}
        </div>
        <div>
          <Label htmlFor="mc-code" required>
            Criterion Band Code
          </Label>
          <select
            id="mc-code"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 disabled:bg-slate-50 disabled:text-slate-400"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={!sectionId || bandCodes.length === 0}
            required
          >
            <option value="">
              {sectionId ? "Select a band code…" : "Select a variable first"}
            </option>
            {bandCodes.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="mc-weight">Weight</Label>
          <Input
            id="mc-weight"
            type="number"
            step="0.1"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Add
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Match Indices Tab — view computed results per candidate + recompute button
// ---------------------------------------------------------------------------

function MatchIndicesTab({ solutionId, canManage }: { solutionId: number; canManage: boolean }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedCandidate, setSelectedCandidate] = useState<MatchIndex | null>(null);

  const { data: indices, isLoading } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId, "match-indices"],
    queryFn: () => listMatchIndices(solutionId),
  });

  const computeMutation = useMutation({
    mutationFn: () => computeSolution(solutionId),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "match-indices"],
      });
      toast.success(`Computed ${data.length} match index record(s).`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;

  const list = indices ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Match Indices — Computed Results</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            Once the solution is published, compute the match indices for the authenticated user.
            For admins (cj_admin / psychometrician), use the API directly with{" "}
            <code className="rounded bg-slate-100 px-1">candidate_id</code> in the body to compute
            for other users.
          </p>
          {canManage && (
            <div className="flex justify-end">
              <Button onClick={() => computeMutation.mutate()} loading={computeMutation.isPending}>
                Compute match indices for me
              </Button>
            </div>
          )}
          {list.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">
              No match indices computed yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Career stream</TableHead>
                  <TableHead>Career</TableHead>
                  <TableHead>FMI</TableHead>
                  <TableHead>VMI</TableHead>
                  <TableHead>Computed</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.map((mi) => (
                  <TableRow key={mi.id}>
                    <TableCell className="font-medium text-slate-900">
                      {mi.candidate_name ?? `User ${mi.candidate}`}
                    </TableCell>
                    <TableCell className="text-slate-500">{mi.career_stream || "—"}</TableCell>
                    <TableCell className="text-slate-900">{mi.career_title}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          mi.final_match_index != null && mi.final_match_index >= 75
                            ? "success"
                            : mi.final_match_index != null && mi.final_match_index >= 50
                              ? "warning"
                              : "default"
                        }
                      >
                        {mi.final_match_index != null ? mi.final_match_index.toFixed(2) : "—"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {mi.variable_mapping_index != null
                        ? mi.variable_mapping_index.toFixed(2)
                        : "—"}
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {new Date(mi.computed_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => setSelectedCandidate(mi)}>
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selectedCandidate && (
        <MatchIndexDetailsModal
          matchIndex={selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
        />
      )}
    </div>
  );
}

function MatchIndexDetailsModal({
  matchIndex,
  onClose,
}: {
  matchIndex: MatchIndex;
  onClose: () => void;
}) {
  const details = matchIndex.variable_details ?? [];
  return (
    <Modal open onClose={onClose} title={`VMI breakdown — ${matchIndex.career_title}`} size="lg">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Final Match Index
            </div>
            <div className="mt-1 text-lg font-bold text-slate-900">
              {matchIndex.final_match_index != null ? matchIndex.final_match_index.toFixed(2) : "—"}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Variable Mapping Index
            </div>
            <div className="mt-1 text-lg font-bold text-slate-900">
              {matchIndex.variable_mapping_index != null
                ? matchIndex.variable_mapping_index.toFixed(2)
                : "—"}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Variables
            </div>
            <div className="mt-1 text-lg font-bold text-slate-900">{details.length}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Candidate
            </div>
            <div className="mt-1 text-sm font-semibold text-slate-900">
              {matchIndex.candidate_name ?? `User ${matchIndex.candidate}`}
            </div>
          </div>
        </div>

        {details.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No per-variable breakdown available.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Variable</TableHead>
                <TableHead>Assessment</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Criterion</TableHead>
                <TableHead>Candidate</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Weight</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>VMI</TableHead>
                <TableHead>PMI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {details.map((v, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium text-slate-900">{v.variable}</TableCell>
                  <TableCell className="text-slate-500">{v.assessment}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{v.mode}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">{v.criterion_band}</TableCell>
                  <TableCell className="text-slate-500">{v.candidate_band}</TableCell>
                  <TableCell className="text-slate-500">
                    {v.mapping_score ?? v.match_value ?? "—"}
                  </TableCell>
                  <TableCell className="text-slate-500">{v.weight.toFixed(2)}</TableCell>
                  <TableCell className="text-slate-500">{v.product_score.toFixed(2)}</TableCell>
                  <TableCell className="text-slate-900">{v.vmi.toFixed(2)}</TableCell>
                  <TableCell className="text-slate-500">
                    {v.pmi != null ? v.pmi.toFixed(2) : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        <div className="flex justify-end border-t border-slate-100 pt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Rank Chart Tab — SRS §4.1.3 (standard) + §4.2.3 (polar)
// ---------------------------------------------------------------------------

function RankChartTab({
  solutionId,
  solution,
  canManage,
}: {
  solutionId: number;
  solution: ProfilingSolution;
  canManage: boolean;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();

  const { data: rankDefs, isLoading } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId, "rank-definitions"],
    queryFn: () => listRankDefinitions(solutionId),
  });

  const deleteMutation = useMutation({
    mutationFn: (rdId: number) => deleteRankDefinition(solutionId, rdId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "rank-definitions"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId],
      });
      toast.success("Rank chart deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;

  const list = rankDefs ?? [];
  const selectedAssessments = solution.selected_assessments ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Rank Order Chart (SRS §4.1.3 + §4.2.3)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            A rank chart assigns a weight (rank value) to each variable's rank order. Rank1 receives
            the max value; RankN receives the lowest. For polar assessments, the chart is
            2-dimensional: each (match_code, rank_order) pair has its own value — note that for LM
            (Low Match), the value increases with rank order (opposite of HM).
          </p>
          {list.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">
              No rank charts defined yet. Use the buttons below to create one per selected
              assessment.
            </p>
          ) : (
            <div className="space-y-4">
              {list.map((rd) => {
                const sa = selectedAssessments.find((s) => s.id === rd.selected_assessment);
                return (
                  <div key={rd.id} className="rounded-md border border-slate-200 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-slate-900">
                          {sa?.label ?? `Assessment ${rd.selected_assessment}`}
                        </div>
                        <div className="text-xs text-slate-500">
                          {rd.is_polar ? "Polar mode (2D chart)" : "Standard mode (1D chart)"}
                        </div>
                      </div>
                      {canManage && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteMutation.mutate(rd.id)}
                          loading={deleteMutation.isPending}
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                    {!rd.is_polar ? (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Rank order</TableHead>
                            <TableHead>Rank value (weight)</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rd.rank_values.map((rv) => (
                            <TableRow key={rv.id}>
                              <TableCell className="font-medium">Rank{rv.rank_order}</TableCell>
                              <TableCell>{rv.rank_value}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Match code</TableHead>
                            <TableHead>Rank order</TableHead>
                            <TableHead>Rank value (weight)</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rd.polar_rank_values.map((pv) => (
                            <TableRow key={pv.id}>
                              <TableCell>
                                <Badge
                                  variant={
                                    pv.match_code === "HM"
                                      ? "success"
                                      : pv.match_code === "MM"
                                        ? "warning"
                                        : "danger"
                                  }
                                >
                                  {pv.match_code}
                                </Badge>
                              </TableCell>
                              <TableCell className="font-medium">Rank{pv.rank_order}</TableCell>
                              <TableCell>{pv.rank_value}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          {canManage && (
            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
              {selectedAssessments.map((sa) => (
                <RankChartCreateButton
                  key={sa.id}
                  solutionId={solutionId}
                  selectedAssessmentId={sa.id}
                  selectedAssessmentLabel={sa.label}
                  isPolar={sa.is_polar || solution.has_polar_assessment}
                  hasExisting={list.some((rd) => rd.selected_assessment === sa.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RankChartCreateButton({
  solutionId,
  selectedAssessmentId,
  selectedAssessmentLabel,
  isPolar,
  hasExisting,
}: {
  solutionId: number;
  selectedAssessmentId: number;
  selectedAssessmentLabel: string;
  isPolar: boolean;
  hasExisting: boolean;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  // Standard mode: dynamic list of rank values
  const [rankValues, setRankValues] = useState<{ rank_order: number; rank_value: string }[]>([
    { rank_order: 1, rank_value: "2.0" },
    { rank_order: 2, rank_value: "1.8" },
  ]);
  // Polar mode: dynamic list of (match_code, rank_order, rank_value)
  const [polarValues, setPolarValues] = useState<
    { match_code: "HM" | "MM" | "LM"; rank_order: number; rank_value: string }[]
  >([
    { match_code: "HM", rank_order: 1, rank_value: "7.0" },
    { match_code: "MM", rank_order: 1, rank_value: "7.0" },
    { match_code: "LM", rank_order: 1, rank_value: "3.0" },
  ]);

  const createMutation = useMutation({
    mutationFn: () => {
      if (!isPolar) {
        return createRankDefinition(solutionId, {
          selected_assessment: selectedAssessmentId,
          is_polar: false,
          rank_values: rankValues.map((rv) => ({
            rank_order: rv.rank_order,
            rank_value: Number(rv.rank_value),
          })),
        });
      }
      return createRankDefinition(solutionId, {
        selected_assessment: selectedAssessmentId,
        is_polar: true,
        polar_rank_values: polarValues.map((pv) => ({
          match_code: pv.match_code,
          rank_order: pv.rank_order,
          rank_value: Number(pv.rank_value),
        })),
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "rank-definitions"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId],
      });
      toast.success("Rank chart created.");
      setOpen(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (hasExisting) {
    return null; // hide the button if a chart already exists for this assessment
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        + Rank chart for {selectedAssessmentLabel}
      </Button>
      {open && (
        <Modal
          open
          onClose={() => setOpen(false)}
          title={`Rank chart — ${selectedAssessmentLabel}`}
          description={isPolar ? "Polar mode (2D chart)" : "Standard mode (1D chart)"}
          size="lg"
        >
          <div className="space-y-4">
            {!isPolar ? (
              <>
                <div className="space-y-2">
                  {rankValues.map((rv, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="w-20 text-sm text-slate-600">Rank{rv.rank_order}</span>
                      <Input
                        type="number"
                        step="0.1"
                        value={rv.rank_value}
                        onChange={(e) => {
                          const next = [...rankValues];
                          next[i] = { ...rv, rank_value: e.target.value };
                          setRankValues(next);
                        }}
                        className="max-w-[120px]"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRankValues(rankValues.filter((_, idx) => idx !== i))}
                      >
                        Remove
                      </Button>
                    </div>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setRankValues([
                      ...rankValues,
                      { rank_order: rankValues.length + 1, rank_value: "1.0" },
                    ])
                  }
                >
                  + Add rank
                </Button>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  {polarValues.map((pv, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <select
                        className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm"
                        value={pv.match_code}
                        onChange={(e) => {
                          const next = [...polarValues];
                          next[i] = {
                            ...pv,
                            match_code: e.target.value as "HM" | "MM" | "LM",
                          };
                          setPolarValues(next);
                        }}
                      >
                        <option value="HM">HM</option>
                        <option value="MM">MM</option>
                        <option value="LM">LM</option>
                      </select>
                      <span className="text-sm text-slate-600">Rank</span>
                      <Input
                        type="number"
                        min="1"
                        value={pv.rank_order}
                        onChange={(e) => {
                          const next = [...polarValues];
                          next[i] = { ...pv, rank_order: Number(e.target.value) };
                          setPolarValues(next);
                        }}
                        className="max-w-[80px]"
                      />
                      <Input
                        type="number"
                        step="0.1"
                        value={pv.rank_value}
                        onChange={(e) => {
                          const next = [...polarValues];
                          next[i] = { ...pv, rank_value: e.target.value };
                          setPolarValues(next);
                        }}
                        className="max-w-[120px]"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPolarValues(polarValues.filter((_, idx) => idx !== i))}
                      >
                        Remove
                      </Button>
                    </div>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setPolarValues([
                      ...polarValues,
                      { match_code: "HM", rank_order: 1, rank_value: "1.0" },
                    ])
                  }
                >
                  + Add entry
                </Button>
              </>
            )}
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => createMutation.mutate()} loading={createMutation.isPending}>
                Create rank chart
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Polar Match Rules Tab — SRS §4.2.2 (polar solutions only)
// ---------------------------------------------------------------------------

function StandardMappingRulesTab({
  solutionId,
  canManage,
}: {
  solutionId: number;
  canManage: boolean;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedBd, setSelectedBd] = useState<number | null>(null);

  const { data: rules, isLoading } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId, "mapping-rules"],
    queryFn: () => listMappingRules(solutionId),
  });
  const { data: solution } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId],
    queryFn: () => retrieveSolution(solutionId),
  });

  const saveMutation = useMutation({
    mutationFn: (payload: {
      band_definition: number;
      criterion_band_code: string;
      user_band_code: string;
      value: number;
    }) => createMappingRule(solutionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "mapping-rules"],
      });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;

  const bandDefs =
    solution?.selected_assessments?.flatMap((sa) =>
      sa.band_definitions.map((bd) => ({
        id: bd.id,
        label: `${sa.label} > ${bd.section_title}`,
        bandCodes: bd.bands.map((b) => b.band_code),
      })),
    ) ?? [];
  const activeBd = bandDefs.find((b) => b.id === selectedBd) ?? bandDefs[0];
  const codes = activeBd?.bandCodes ?? [];
  const valueFor = (crit: string, usr: string) =>
    (rules ?? []).find(
      (r) =>
        r.band_definition === activeBd?.id &&
        r.criterion_band_code === crit &&
        r.user_band_code === usr,
    )?.value;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Standard Mapping Rules (SRS §4.1.2)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Assign the mapping value for each (criterion band, user band) combination of a standard
          variable. Rows are the criterion band; columns are the candidate's band.
        </p>
        {bandDefs.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            Define bands first — the mapping grid is built from a variable's bands.
          </p>
        ) : (
          <>
            <div>
              <Label htmlFor="mr-bd">Variable</Label>
              <select
                id="mr-bd"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={activeBd?.id ?? ""}
                onChange={(e) => setSelectedBd(Number(e.target.value))}
              >
                {bandDefs.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>
            {codes.length === 0 ? (
              <p className="text-sm text-slate-500">This variable has no bands yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="border-collapse text-sm">
                  <thead>
                    <tr>
                      <th className="border border-slate-200 bg-slate-50 p-2 text-xs text-slate-500">
                        criterion \ user
                      </th>
                      {codes.map((uc) => (
                        <th
                          key={uc}
                          className="border border-slate-200 bg-slate-50 p-2 text-xs font-medium"
                        >
                          {uc}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {codes.map((cc) => (
                      <tr key={cc}>
                        <th className="border border-slate-200 bg-slate-50 p-2 text-xs font-medium">
                          {cc}
                        </th>
                        {codes.map((uc) => (
                          <td key={uc} className="border border-slate-200 p-1">
                            <input
                              type="number"
                              min={0}
                              disabled={!canManage || !activeBd}
                              defaultValue={valueFor(cc, uc) ?? ""}
                              className="w-16 rounded border border-slate-200 px-1.5 py-0.5 text-xs"
                              onBlur={(e) => {
                                if (!activeBd) return;
                                const raw = e.target.value.trim();
                                if (raw === "") return;
                                const value = Number(raw);
                                if (Number.isNaN(value) || value < 0 || value === valueFor(cc, uc))
                                  return;
                                saveMutation.mutate({
                                  band_definition: activeBd.id,
                                  criterion_band_code: cc,
                                  user_band_code: uc,
                                  value,
                                });
                              }}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function PolarMatchRulesTab({ solutionId, canManage }: { solutionId: number; canManage: boolean }) {
  const toast = useToast();
  const queryClient = useQueryClient();

  const { data: rules, isLoading } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId, "polar-match-rules"],
    queryFn: () => listPolarMatchRules(solutionId),
  });

  // Also fetch band definitions so we can show the variable name per rule
  const { data: solution } = useQuery({
    queryKey: ["career-profiling", "solutions", solutionId],
    queryFn: () => retrieveSolution(solutionId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: {
      band_definition: number;
      criterion_band_code: string;
      user_band_code: string;
      match_code: "HM" | "MM" | "LM";
      match_value: number;
    }) => createPolarMatchRule(solutionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["career-profiling", "solutions", solutionId, "polar-match-rules"],
      });
      toast.success("Polar match rule created.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;

  const list = rules ?? [];

  // Build a map of band_definition_id -> (variable name, band codes)
  const bandDefs =
    solution?.selected_assessments?.flatMap((sa) =>
      sa.band_definitions.map((bd) => ({
        id: bd.id,
        label: `${sa.label} > ${bd.section_title}`,
        bandCodes: bd.bands.map((b) => b.band_code),
      })),
    ) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Polar Match Rules (SRS §4.2.2)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          For polar assessments, the mapping value is NOT band-distance based. Instead, the
          psychometrician defines a rule table mapping (criterion_band_code, user_band_code) →
          (match_code, match_value): HM = High Match (5), MM = Moderate Match (3), LM = Low Match
          (1).
        </p>

        {list.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No polar match rules defined yet. Use the form below to add one.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Variable</TableHead>
                <TableHead>Criterion band</TableHead>
                <TableHead>User band</TableHead>
                <TableHead>Match code</TableHead>
                <TableHead>Match value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((r) => {
                const bd = bandDefs.find((b) => b.id === r.band_definition);
                return (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium text-slate-900">
                      {bd?.label ?? `BandDef ${r.band_definition}`}
                    </TableCell>
                    <TableCell className="text-slate-500">{r.criterion_band_code}</TableCell>
                    <TableCell className="text-slate-500">{r.user_band_code}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          r.match_code === "HM"
                            ? "success"
                            : r.match_code === "MM"
                              ? "warning"
                              : "danger"
                        }
                      >
                        {r.match_code}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-900">{r.match_value}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}

        {canManage && bandDefs.length > 0 && (
          <PolarMatchRuleForm
            bandDefs={bandDefs}
            loading={createMutation.isPending}
            onSubmit={(payload) => createMutation.mutate(payload)}
          />
        )}
      </CardContent>
    </Card>
  );
}

function PolarMatchRuleForm({
  bandDefs,
  loading,
  onSubmit,
}: {
  bandDefs: { id: number; label: string; bandCodes: string[] }[];
  loading: boolean;
  onSubmit: (payload: {
    band_definition: number;
    criterion_band_code: string;
    user_band_code: string;
    match_code: "HM" | "MM" | "LM";
    match_value: number;
  }) => void;
}) {
  const [bdId, setBdId] = useState("");
  const [criterionBand, setCriterionBand] = useState("");
  const [userBand, setUserBand] = useState("");
  const [matchCode, setMatchCode] = useState<"HM" | "MM" | "LM">("HM");
  const [matchValue, setMatchValue] = useState("5");

  const selectedBd = bandDefs.find((b) => b.id === Number(bdId));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!bdId || !criterionBand || !userBand) return;
        onSubmit({
          band_definition: Number(bdId),
          criterion_band_code: criterionBand,
          user_band_code: userBand,
          match_code: matchCode,
          match_value: Number(matchValue),
        });
      }}
      className="space-y-3 border-t border-slate-100 pt-4"
    >
      <div className="text-sm font-semibold text-slate-900">Add a polar match rule</div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
        <div>
          <Label htmlFor="bd" required>
            Variable
          </Label>
          <select
            id="bd"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
            value={bdId}
            onChange={(e) => {
              setBdId(e.target.value);
              setCriterionBand("");
              setUserBand("");
            }}
            required
          >
            <option value="">Select...</option>
            {bandDefs.map((b) => (
              <option key={b.id} value={b.id}>
                {b.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="cb" required>
            Criterion band
          </Label>
          <select
            id="cb"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
            value={criterionBand}
            onChange={(e) => setCriterionBand(e.target.value)}
            required
            disabled={!selectedBd}
          >
            <option value="">Select...</option>
            {selectedBd?.bandCodes.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="ub" required>
            User band
          </Label>
          <select
            id="ub"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
            value={userBand}
            onChange={(e) => setUserBand(e.target.value)}
            required
            disabled={!selectedBd}
          >
            <option value="">Select...</option>
            {selectedBd?.bandCodes.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="mc">Match code</Label>
          <select
            id="mc"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
            value={matchCode}
            onChange={(e) => setMatchCode(e.target.value as "HM" | "MM" | "LM")}
          >
            <option value="HM">HM (High Match)</option>
            <option value="MM">MM (Moderate Match)</option>
            <option value="LM">LM (Low Match)</option>
          </select>
        </div>
        <div>
          <Label htmlFor="mv">Match value</Label>
          <Input
            id="mv"
            type="number"
            min="0"
            max="5"
            value={matchValue}
            onChange={(e) => setMatchValue(e.target.value)}
          />
        </div>
      </div>
      <div className="flex justify-end">
        <Button type="submit" loading={loading} disabled={!bdId || !criterionBand || !userBand}>
          Add rule
        </Button>
      </div>
    </form>
  );
}
