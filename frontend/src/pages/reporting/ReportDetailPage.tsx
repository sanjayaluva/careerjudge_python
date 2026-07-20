/**
 * Report Detail Page — tabs:
 * - Properties: report metadata + publish button
 * - Generate: pick a completed session and generate the report
 * - Generated: list of generated reports for this definition
 * - Group: (group reports only) pick multiple sessions + view aggregation
 * - HFMI/LFMI: (profiling reports only) data selection per SRS 06 §2.2
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
  createBand,
  createCode,
  createCutoff,
  createPolarVariable,
  createSection,
  DATA_INPUT_LEVELS,
  generateGroupReport,
  generateReport,
  generatedReportPdfUrl,
  listBands,
  listCodes,
  listCutoffs,
  listGeneratedReports,
  listPolarVariables,
  listSections,
  publishReport,
  REPORT_TYPES,
  reorderSections,
  retrieveReport,
  SECTION_TYPES,
  STAT_CONVERSIONS,
  selectProfilingData,
  type GroupReportData,
  type ProfilingSelectionResult,
} from "@/api/reporting";
import { listSections as listAssessmentSections, listSessions } from "@/api/assessment";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const REPORT_KEY = ["reporting", "reports"];
const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const rid = Number(id);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const canManage = ["cj_admin", "psychometrician", "counsellor"].includes(user?.role ?? "");

  const { data: report, isLoading } = useQuery({
    queryKey: [...REPORT_KEY, rid],
    queryFn: () => retrieveReport(rid),
    enabled: !Number.isNaN(rid),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishReport(rid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...REPORT_KEY, rid] });
      toast.success("Report published.");
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
  if (!report) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load report.</AlertDescription>
      </Alert>
    );
  }

  const typeLabel =
    REPORT_TYPES.find((t) => t.value === report.report_type)?.label ?? report.report_type;
  const levelLabel =
    DATA_INPUT_LEVELS.find((l) => l.value === report.data_input_level)?.label ??
    report.data_input_level;
  const convLabel =
    STAT_CONVERSIONS.find((c) => c.value === report.stat_conversion)?.label ??
    report.stat_conversion;

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link to="/reports" className="text-sm text-primary-600 hover:underline">
          ← Back to Reports
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">{report.title}</h1>
          <Badge variant="outline">{typeLabel}</Badge>
          <Badge variant="outline">{report.scope}</Badge>
          <Badge variant={STATUS_VARIANTS[report.status] ?? "default"}>{report.status}</Badge>
        </div>
        {report.objective && (
          <p className="mt-2 max-w-3xl text-sm text-slate-600">{report.objective}</p>
        )}
      </div>

      <Tabs defaultValue="properties">
        <TabsList>
          <TabsTrigger value="properties">Properties</TabsTrigger>
          {canManage && report.status === "draft" && (
            <>
              {report.report_type === "descriptive" && (
                <TabsTrigger value="cutoffs">Cutoffs</TabsTrigger>
              )}
              {report.report_type === "interpretative" && (
                <TabsTrigger value="bands">Bands</TabsTrigger>
              )}
              {report.report_type === "typological" && (
                <TabsTrigger value="codes">Codes</TabsTrigger>
              )}
              <TabsTrigger value="polar">Polar Variables</TabsTrigger>
              <TabsTrigger value="layout">Layout</TabsTrigger>
            </>
          )}
          <TabsTrigger value="generate">Generate</TabsTrigger>
          <TabsTrigger value="generated">Generated</TabsTrigger>
          {report.report_type === "group" && <TabsTrigger value="group">Group</TabsTrigger>}
          {report.scope === "profiling" && <TabsTrigger value="hfmi">HFMI / LFMI</TabsTrigger>}
        </TabsList>

        {/* === PROPERTIES TAB === */}
        <TabsContent value="properties">
          <Card>
            <CardHeader>
              <CardTitle>Report Properties</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2">
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Scope
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{report.scope}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Report type
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{typeLabel}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Assessment
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{report.assessment_title ?? "—"}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Profiling solution
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">
                    {report.profiling_solution_title ?? "—"}
                  </dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Data input level
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{levelLabel}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Statistical conversion
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{convLabel}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created by
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{report.created_by_name ?? "—"}</dd>
                </div>
                <div className="py-1">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Created
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">
                    {new Date(report.created_at).toLocaleString()}
                  </dd>
                </div>
              </dl>

              {report.description && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Description
                  </div>
                  <p className="mt-1 text-sm text-slate-900">{report.description}</p>
                </div>
              )}

              {/* Profiling report flags */}
              {report.scope === "profiling" && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Profiling data inputs
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {report.include_raw_summary && <Badge variant="outline">Raw Summary</Badge>}
                    {report.include_fmi && <Badge variant="outline">FMI</Badge>}
                    {report.include_pmi && <Badge variant="outline">PMI</Badge>}
                    {report.include_vmi && <Badge variant="outline">VMI</Badge>}
                  </div>
                </div>
              )}

              {canManage && report.status === "draft" && (
                <div className="mt-6 flex justify-end border-t border-slate-100 pt-4">
                  <Button
                    onClick={() => publishMutation.mutate()}
                    loading={publishMutation.isPending}
                  >
                    Publish report
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === CONFIG TABS (draft reports only, type-specific) === */}
        {canManage && report.status === "draft" && (
          <>
            {report.report_type === "descriptive" && (
              <TabsContent value="cutoffs">
                <CutoffsTab reportId={rid} assessmentId={report.assessment} />
              </TabsContent>
            )}
            {report.report_type === "interpretative" && (
              <TabsContent value="bands">
                <BandsConfigTab reportId={rid} assessmentId={report.assessment} />
              </TabsContent>
            )}
            {report.report_type === "typological" && (
              <TabsContent value="codes">
                <CodesTab reportId={rid} assessmentId={report.assessment} />
              </TabsContent>
            )}
            <TabsContent value="polar">
              <PolarVariablesTab reportId={rid} assessmentId={report.assessment} />
            </TabsContent>
            <TabsContent value="layout">
              <LayoutTab reportId={rid} />
            </TabsContent>
          </>
        )}

        {/* === GENERATE TAB (single session) === */}
        <TabsContent value="generate">
          <GenerateTab reportId={rid} assessmentId={report.assessment} />
        </TabsContent>

        {/* === GENERATED LIST TAB === */}
        <TabsContent value="generated">
          <GeneratedTab reportId={rid} />
        </TabsContent>

        {/* === GROUP REPORT TAB (group reports only) === */}
        {report.report_type === "group" && (
          <TabsContent value="group">
            <GroupReportTab reportId={rid} assessmentId={report.assessment} />
          </TabsContent>
        )}

        {/* === HFMI / LFMI TAB (profiling reports only) === */}
        {report.scope === "profiling" && (
          <TabsContent value="hfmi">
            <HfmiLfmiTab reportId={rid} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Generate Tab — pick a completed session, generate the report
// ---------------------------------------------------------------------------

function GenerateTab({
  reportId,
  assessmentId,
}: {
  reportId: number;
  assessmentId: number | null;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedSession, setSelectedSession] = useState("");

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["assessment", "sessions-for-report", assessmentId],
    queryFn: () => listSessions(assessmentId as number),
    enabled: assessmentId !== null,
  });

  const generateMutation = useMutation({
    mutationFn: (sessionId: number) => generateReport(reportId, sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reporting", "reports", reportId] });
      toast.success("Report generated.");
      setSelectedSession("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const completedSessions = (sessions ?? []).filter((s) => s.status === "completed");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generate Report for a Session</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Spinner />
        ) : completedSessions.length === 0 ? (
          <p className="text-sm text-slate-500">
            No completed sessions available for this assessment yet.
          </p>
        ) : (
          <>
            <div>
              <Label htmlFor="session" required>
                Completed session
              </Label>
              <select
                id="session"
                className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={selectedSession}
                onChange={(e) => setSelectedSession(e.target.value)}
              >
                <option value="">Select a session...</option>
                {completedSessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} — {s.candidate_name ?? `User ${s.candidate}`} —{" "}
                    {s.percentage != null ? `${s.percentage}%` : "in progress"} —{" "}
                    {s.completed_at ? new Date(s.completed_at).toLocaleString() : ""}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end">
              <Button
                onClick={() => generateMutation.mutate(Number(selectedSession))}
                loading={generateMutation.isPending}
                disabled={!selectedSession}
              >
                Generate report
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Generated Tab — list all generated reports for this definition
// ---------------------------------------------------------------------------

function GeneratedTab({ reportId }: { reportId: number }) {
  const { data: generated, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "generated"],
    queryFn: () => listGeneratedReports(reportId),
  });

  if (isLoading) return <Spinner />;
  const list = generated ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generated Reports ({list.length})</CardTitle>
      </CardHeader>
      <CardContent>
        {list.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No reports generated yet. Use the Generate tab to create one.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Candidate</TableHead>
                <TableHead>Session</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Generated at</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((g) => (
                <TableRow key={g.id}>
                  <TableCell className="font-medium text-slate-900">
                    {g.candidate_name ?? `User ${g.candidate}`}
                  </TableCell>
                  <TableCell className="text-slate-500">#{g.session}</TableCell>
                  <TableCell>
                    <Badge variant={g.status === "generated" ? "success" : "warning"}>
                      {g.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">
                    {new Date(g.generated_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {g.status === "generated" && g.rendered_data && (
                      <div className="flex flex-col gap-1 text-xs">
                        <a
                          href={generatedReportPdfUrl(g.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary-600 hover:underline"
                        >
                          Download PDF ↓
                        </a>
                        <details>
                          <summary className="cursor-pointer text-slate-600 hover:underline">
                            View JSON
                          </summary>
                          <pre className="mt-2 max-h-96 overflow-auto rounded-md bg-slate-50 p-3 text-xs">
                            {JSON.stringify(g.rendered_data, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                    {g.status === "failed" && g.error_message && (
                      <span className="text-xs text-danger-600">{g.error_message}</span>
                    )}
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
// Group Report Tab — pick multiple sessions, view aggregated data
// ---------------------------------------------------------------------------

function GroupReportTab({
  reportId,
  assessmentId,
}: {
  reportId: number;
  assessmentId: number | null;
}) {
  const toast = useToast();
  const [selectedSessionIds, setSelectedSessionIds] = useState<number[]>([]);
  const [groupData, setGroupData] = useState<GroupReportData | null>(null);

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["assessment", "sessions-for-group", assessmentId],
    queryFn: () => listSessions(assessmentId as number),
    enabled: assessmentId !== null,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateGroupReport(reportId, selectedSessionIds),
    onSuccess: (data) => {
      setGroupData(data);
      toast.success(`Group report generated for ${data.candidate_count} candidate(s).`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const completedSessions = (sessions ?? []).filter((s) => s.status === "completed");

  const toggleSession = (id: number) => {
    setSelectedSessionIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Select Sessions to Aggregate</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <Spinner />
          ) : completedSessions.length === 0 ? (
            <p className="text-sm text-slate-500">No completed sessions available.</p>
          ) : (
            <>
              <div className="text-sm text-slate-600">
                {selectedSessionIds.length} session(s) selected of {completedSessions.length}{" "}
                available.
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10"></TableHead>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Percentage</TableHead>
                    <TableHead>Completed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {completedSessions.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedSessionIds.includes(s.id)}
                          onChange={() => toggleSession(s.id)}
                          className="h-4 w-4"
                        />
                      </TableCell>
                      <TableCell className="font-medium text-slate-900">
                        {s.candidate_name ?? `User ${s.candidate}`}
                      </TableCell>
                      <TableCell className="text-slate-500">{s.total_score ?? "—"}</TableCell>
                      <TableCell className="text-slate-500">
                        {s.percentage != null ? `${s.percentage}%` : "—"}
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {s.completed_at ? new Date(s.completed_at).toLocaleString() : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex justify-end">
                <Button
                  onClick={() => generateMutation.mutate()}
                  loading={generateMutation.isPending}
                  disabled={selectedSessionIds.length < 2}
                >
                  Generate group report
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {groupData && <GroupReportView data={groupData} />}
    </div>
  );
}

function GroupReportView({ data }: { data: GroupReportData }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Group Report — {data.assessment_title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary stats */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatBox label="Candidates" value={String(data.candidate_count)} />
          <StatBox label="Avg score" value={`${data.average_score} / ${data.max_score ?? "?"}`} />
          <StatBox label="Avg %" value={`${data.average_percentage}%`} />
          <StatBox
            label="Pass rate"
            value={`${data.pass_rate}% (${data.pass_count}/${data.candidate_count})`}
          />
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatBox label="Min %" value={`${data.min_percentage}%`} />
          <StatBox label="Max %" value={`${data.max_percentage}%`} />
          <StatBox label="Min score" value={String(data.min_score)} />
          <StatBox label="Max score" value={String(data.max_score)} />
        </div>

        {/* Distribution */}
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Distribution</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <DistBox
              label="Fail (0-40)"
              count={data.distribution["fail (0-40)"]}
              color="bg-red-100 text-red-800"
            />
            <DistBox
              label="Below avg (40-60)"
              count={data.distribution["below_avg (40-60)"]}
              color="bg-orange-100 text-orange-800"
            />
            <DistBox
              label="Average (60-80)"
              count={data.distribution["average (60-80)"]}
              color="bg-yellow-100 text-yellow-800"
            />
            <DistBox
              label="Above avg (80-100)"
              count={data.distribution["above_avg (80-100)"]}
              color="bg-emerald-100 text-emerald-800"
            />
          </div>
        </div>

        {/* Section averages */}
        {data.section_averages.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Section averages</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Section</TableHead>
                  <TableHead>Average %</TableHead>
                  <TableHead>Min %</TableHead>
                  <TableHead>Max %</TableHead>
                  <TableHead>Candidates</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.section_averages.map((s) => (
                  <TableRow key={s.section_id}>
                    <TableCell className="font-medium text-slate-900">{s.section_title}</TableCell>
                    <TableCell>{s.average_percentage}%</TableCell>
                    <TableCell className="text-slate-500">{s.min_percentage}%</TableCell>
                    <TableCell className="text-slate-500">{s.max_percentage}%</TableCell>
                    <TableCell className="text-slate-500">{s.candidate_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Candidates list */}
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Candidates</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>%</TableHead>
                <TableHead>Session</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.candidates.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium text-slate-900">{c.name}</TableCell>
                  <TableCell className="text-slate-500">{c.email}</TableCell>
                  <TableCell className="text-slate-500">{c.total_score ?? "—"}</TableCell>
                  <TableCell className="text-slate-500">
                    {c.percentage != null ? `${c.percentage}%` : "—"}
                  </TableCell>
                  <TableCell className="text-slate-500">#{c.session_id}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function DistBox({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className={`rounded-md p-3 ${color}`}>
      <div className="text-xs font-medium">{label}</div>
      <div className="mt-1 text-lg font-bold">{count}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HFMI/LFMI Tab — profiling data selection per SRS 06 §2.2
// ---------------------------------------------------------------------------

function HfmiLfmiTab({ reportId }: { reportId: number }) {
  const toast = useToast();
  const [candidateId, setCandidateId] = useState("");
  const [dataType, setDataType] = useState<"HFMI" | "LFMI">("HFMI");
  const [extractionMode, setExtractionMode] = useState<"user" | "system">("system");
  const [fmiMin, setFmiMin] = useState("85");
  const [fmiMax, setFmiMax] = useState("100");
  const [nCategories, setNCategories] = useState("1");
  const [nCriterions, setNCriterions] = useState("5");
  const [result, setResult] = useState<ProfilingSelectionResult | null>(null);

  // List of users to pick a candidate from — reuse assessments list to find
  // any assessment; the actual candidate picker would be a user-search.
  // For now we accept the candidate ID directly.
  const selectMutation = useMutation({
    mutationFn: () => {
      const payload: Parameters<typeof selectProfilingData>[1] = {
        candidate_id: Number(candidateId),
        data_type: dataType,
        extraction_mode: extractionMode,
      };
      if (extractionMode === "user") {
        payload.fmi_range = [Number(fmiMin), Number(fmiMax)];
      } else {
        payload.n_categories = Number(nCategories);
        payload.n_criterions = Number(nCriterions);
      }
      return selectProfilingData(reportId, payload);
    },
    onSuccess: (data) => {
      setResult(data);
      toast.success(
        `Selected ${data.selected_count} career(s) of ${data.total_available} available.`,
      );
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>HFMI / LFMI Data Selection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            Per SRS 06 §2.2: select either Highest-FMI (HFMI) or Lowest-FMI (LFMI) data, then choose
            how to extract them. The system will filter the candidate&apos;s match indices
            accordingly.
          </p>
          <div>
            <Label htmlFor="candidate" required>
              Candidate ID
            </Label>
            <Input
              id="candidate"
              type="number"
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              placeholder="e.g., 42"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="dtype">Data type</Label>
              <select
                id="dtype"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={dataType}
                onChange={(e) => setDataType(e.target.value as "HFMI" | "LFMI")}
              >
                <option value="HFMI">HFMI — Highest FMIs</option>
                <option value="LFMI">LFMI — Lowest FMIs</option>
              </select>
            </div>
            <div>
              <Label htmlFor="emode">Extraction mode</Label>
              <select
                id="emode"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={extractionMode}
                onChange={(e) => setExtractionMode(e.target.value as "user" | "system")}
              >
                <option value="system">System-initiated (auto top-N)</option>
                <option value="user">User-initiated (FMI range filter)</option>
              </select>
            </div>
          </div>
          {extractionMode === "user" ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="fmin">FMI min</Label>
                <Input
                  id="fmin"
                  type="number"
                  value={fmiMin}
                  onChange={(e) => setFmiMin(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="fmax">FMI max</Label>
                <Input
                  id="fmax"
                  type="number"
                  value={fmiMax}
                  onChange={(e) => setFmiMax(e.target.value)}
                />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="ncat">Number of categories (streams)</Label>
                <Input
                  id="ncat"
                  type="number"
                  min="1"
                  value={nCategories}
                  onChange={(e) => setNCategories(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="ncr">Careers per category</Label>
                <Input
                  id="ncr"
                  type="number"
                  min="1"
                  value={nCriterions}
                  onChange={(e) => setNCriterions(e.target.value)}
                />
              </div>
            </div>
          )}
          <div className="flex justify-end">
            <Button
              onClick={() => selectMutation.mutate()}
              loading={selectMutation.isPending}
              disabled={!candidateId}
            >
              Select data
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>
              {result.data_type} Result — {result.selected_count} of {result.total_available}{" "}
              careers
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.selected.length === 0 ? (
              <p className="py-4 text-center text-sm text-slate-500">
                No careers matched the selection criteria.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Stream</TableHead>
                    <TableHead>Career</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>FMI</TableHead>
                    <TableHead>VMI</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.selected.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="text-slate-500">{c.career_stream || "—"}</TableCell>
                      <TableCell className="font-medium text-slate-900">{c.career_title}</TableCell>
                      <TableCell className="text-slate-500">{c.career_code || "—"}</TableCell>
                      <TableCell>
                        <Badge variant={dataType === "HFMI" ? "success" : "warning"}>
                          {c.fmi != null ? c.fmi.toFixed(2) : "—"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {c.vmi != null ? c.vmi.toFixed(2) : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared: section picker for cutoffs/bands/codes/polar config tabs
// ---------------------------------------------------------------------------

function useAssessmentSections(assessmentId: number | null) {
  return useQuery({
    queryKey: ["assessment", "sections", assessmentId],
    queryFn: () => listAssessmentSections(assessmentId as number),
    enabled: assessmentId !== null,
  });
}

function SectionPicker({
  sections,
  value,
  onChange,
}: {
  sections: { id: number; title: string; level: number }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <select
      className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required
    >
      <option value="">Select a variable...</option>
      {sections.map((s) => (
        <option key={s.id} value={s.id}>
          {s.title} (L{s.level})
        </option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Cutoffs Tab (descriptive reports — SRS §3.1.1)
// ---------------------------------------------------------------------------

function CutoffsTab({ reportId, assessmentId }: { reportId: number; assessmentId: number | null }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: cutoffs, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "cutoffs"],
    queryFn: () => listCutoffs(reportId),
  });
  const { data: sections } = useAssessmentSections(assessmentId);
  const [sectionId, setSectionId] = useState("");
  const [cutoffScore, setCutoffScore] = useState("50");
  const [cutoffLabel, setCutoffLabel] = useState("");
  const [aboveDesc, setAboveDesc] = useState("");
  const [belowDesc, setBelowDesc] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      createCutoff(reportId, {
        section: Number(sectionId),
        cutoff_score: Number(cutoffScore),
        cutoff_label: cutoffLabel,
        above_description: aboveDesc,
        below_description: belowDesc,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "cutoffs"],
      });
      toast.success("Cutoff created.");
      setSectionId("");
      setCutoffScore("50");
      setCutoffLabel("");
      setAboveDesc("");
      setBelowDesc("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;
  const list = cutoffs ?? [];
  const sectionList = sections ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cutoffs (Descriptive Report — SRS §3.1.1)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Define a cutoff score per variable. The candidate&apos;s score is compared against the
          cutoff, and the appropriate above/below description is shown in the report.
        </p>
        {list.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Variable</TableHead>
                <TableHead>Cutoff</TableHead>
                <TableHead>Label</TableHead>
                <TableHead>Above description</TableHead>
                <TableHead>Below description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">{c.section_title}</TableCell>
                  <TableCell>{c.cutoff_score}</TableCell>
                  <TableCell className="text-slate-500">{c.cutoff_label || "—"}</TableCell>
                  <TableCell className="text-slate-500">{c.above_description || "—"}</TableCell>
                  <TableCell className="text-slate-500">{c.below_description || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-2"
        >
          <div>
            <Label htmlFor="co-s" required>
              Variable
            </Label>
            <SectionPicker sections={sectionList} value={sectionId} onChange={setSectionId} />
          </div>
          <div>
            <Label htmlFor="co-c" required>
              Cutoff score
            </Label>
            <Input
              id="co-c"
              type="number"
              min="0"
              max="100"
              value={cutoffScore}
              onChange={(e) => setCutoffScore(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="co-l">Cutoff label</Label>
            <Input
              id="co-l"
              value={cutoffLabel}
              onChange={(e) => setCutoffLabel(e.target.value)}
              placeholder="e.g., Average Performance"
            />
          </div>
          <div>
            <Label htmlFor="co-a">Above-cutoff description</Label>
            <textarea
              id="co-a"
              rows={2}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={aboveDesc}
              onChange={(e) => setAboveDesc(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="co-b">Below-cutoff description</Label>
            <textarea
              id="co-b"
              rows={2}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={belowDesc}
              onChange={(e) => setBelowDesc(e.target.value)}
            />
          </div>
          <div className="flex justify-end sm:col-span-2">
            <Button type="submit" loading={createMutation.isPending} disabled={!sectionId}>
              Add cutoff
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Bands Config Tab (interpretative reports — SRS §3.3.1)
// ---------------------------------------------------------------------------

function BandsConfigTab({
  reportId,
  assessmentId,
}: {
  reportId: number;
  assessmentId: number | null;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: bands, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "bands"],
    queryFn: () => listBands(reportId),
  });
  const { data: sections } = useAssessmentSections(assessmentId);
  const [sectionId, setSectionId] = useState("");
  const [bandNumber, setBandNumber] = useState("1");
  const [rangeMin, setRangeMin] = useState("0");
  const [rangeMax, setRangeMax] = useState("100");
  const [bandLabel, setBandLabel] = useState("");
  const [description, setDescription] = useState("");
  const [colourCode, setColourCode] = useState("#3b82f6");

  const createMutation = useMutation({
    mutationFn: () =>
      createBand(reportId, {
        section: Number(sectionId),
        band_number: Number(bandNumber),
        range_min: Number(rangeMin),
        range_max: Number(rangeMax),
        band_label: bandLabel,
        description,
        colour_code: colourCode,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "bands"],
      });
      toast.success("Band created.");
      setSectionId("");
      setBandNumber(String(Number(bandNumber) + 1));
      setBandLabel("");
      setDescription("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;
  const list = bands ?? [];
  const sectionList = sections ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Band Definitions (Interpretative — SRS §3.3.1)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Define score bands per variable. The candidate&apos;s score is matched to a band, and the
          band&apos;s label + description is shown in the report.
        </p>
        {list.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Variable</TableHead>
                <TableHead>Band #</TableHead>
                <TableHead>Range</TableHead>
                <TableHead>Label</TableHead>
                <TableHead>Color</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((b) => (
                <TableRow key={b.id}>
                  <TableCell className="font-medium">{b.section_title}</TableCell>
                  <TableCell>{b.band_number}</TableCell>
                  <TableCell className="text-slate-500">
                    {b.range_min}–{b.range_max}
                  </TableCell>
                  <TableCell>{b.band_label || "—"}</TableCell>
                  <TableCell>
                    {b.colour_code && (
                      <span
                        className="inline-block h-4 w-4 rounded border border-slate-200"
                        style={{ background: b.colour_code }}
                      />
                    )}
                  </TableCell>
                  <TableCell className="text-slate-500">{b.description || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-3"
        >
          <div className="sm:col-span-3">
            <Label htmlFor="bd-s" required>
              Variable
            </Label>
            <SectionPicker sections={sectionList} value={sectionId} onChange={setSectionId} />
          </div>
          <div>
            <Label htmlFor="bd-n" required>
              Band number
            </Label>
            <Input
              id="bd-n"
              type="number"
              min="1"
              value={bandNumber}
              onChange={(e) => setBandNumber(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="bd-min" required>
              Range min
            </Label>
            <Input
              id="bd-min"
              type="number"
              min="0"
              max="100"
              value={rangeMin}
              onChange={(e) => setRangeMin(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="bd-max" required>
              Range max
            </Label>
            <Input
              id="bd-max"
              type="number"
              min="0"
              max="100"
              value={rangeMax}
              onChange={(e) => setRangeMax(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="bd-l">Band label</Label>
            <Input
              id="bd-l"
              value={bandLabel}
              onChange={(e) => setBandLabel(e.target.value)}
              placeholder="e.g., High"
            />
          </div>
          <div>
            <Label htmlFor="bd-c">Colour code</Label>
            <input
              id="bd-c"
              type="color"
              value={colourCode}
              onChange={(e) => setColourCode(e.target.value)}
              className="h-10 w-full rounded-md border border-slate-200"
            />
          </div>
          <div className="sm:col-span-3">
            <Label htmlFor="bd-d">Description</Label>
            <textarea
              id="bd-d"
              rows={2}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end sm:col-span-3">
            <Button type="submit" loading={createMutation.isPending} disabled={!sectionId}>
              Add band
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Codes Tab (typological reports — SRS §3.2.1)
// ---------------------------------------------------------------------------

function CodesTab({ reportId, assessmentId }: { reportId: number; assessmentId: number | null }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: codes, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "codes"],
    queryFn: () => listCodes(reportId),
  });
  const { data: sections } = useAssessmentSections(assessmentId);
  const [sectionId, setSectionId] = useState("");
  const [code, setCode] = useState("");
  const [topN, setTopN] = useState("3");

  const createMutation = useMutation({
    mutationFn: () =>
      createCode(reportId, {
        section: Number(sectionId),
        code,
        top_n: Number(topN),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "codes"],
      });
      toast.success("Code created.");
      setSectionId("");
      setCode("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;
  const list = codes ?? [];
  const sectionList = sections ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Typological Codes (SRS §3.2.1)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Assign an alphabet or number to each variable. The top-scoring variables&apos; codes are
          concatenated to form the candidate&apos;s personality/intellectual type profile.
        </p>
        {list.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Variable</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Top N</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">{c.section_title}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{c.code}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">{c.top_n}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-3"
        >
          <div className="sm:col-span-3">
            <Label htmlFor="cd-s" required>
              Variable
            </Label>
            <SectionPicker sections={sectionList} value={sectionId} onChange={setSectionId} />
          </div>
          <div>
            <Label htmlFor="cd-c" required>
              Code
            </Label>
            <Input
              id="cd-c"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g., A or 1"
              maxLength={10}
            />
          </div>
          <div>
            <Label htmlFor="cd-n">Top N</Label>
            <Input
              id="cd-n"
              type="number"
              min="1"
              value={topN}
              onChange={(e) => setTopN(e.target.value)}
            />
          </div>
          <div className="flex justify-end sm:col-span-3">
            <Button type="submit" loading={createMutation.isPending} disabled={!sectionId || !code}>
              Add code
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Polar Variables Tab (SRS §4 — opposite variable computation)
// ---------------------------------------------------------------------------

function PolarVariablesTab({
  reportId,
  assessmentId,
}: {
  reportId: number;
  assessmentId: number | null;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: polarVars, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "polar"],
    queryFn: () => listPolarVariables(reportId),
  });
  const { data: sections } = useAssessmentSections(assessmentId);
  const [sectionId, setSectionId] = useState("");
  const [oppositeName, setOppositeName] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      createPolarVariable(reportId, {
        section: Number(sectionId),
        opposite_name: oppositeName,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "polar"],
      });
      toast.success("Polar variable created.");
      setSectionId("");
      setOppositeName("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;
  const list = polarVars ?? [];
  const sectionList = sections ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Polar Variables (SRS §4)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          For polar assessments, each variable has an opposite (e.g., Extroversion ↔ Introversion).
          The opposite score is computed as 100 − primary score.
        </p>
        {list.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Primary variable</TableHead>
                <TableHead>Opposite variable</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.section_title}</TableCell>
                  <TableCell className="text-slate-500">{p.opposite_name}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-2"
        >
          <div>
            <Label htmlFor="pv-s" required>
              Primary variable
            </Label>
            <SectionPicker sections={sectionList} value={sectionId} onChange={setSectionId} />
          </div>
          <div>
            <Label htmlFor="pv-o" required>
              Opposite variable name
            </Label>
            <Input
              id="pv-o"
              value={oppositeName}
              onChange={(e) => setOppositeName(e.target.value)}
              placeholder="e.g., Introversion"
            />
          </div>
          <div className="flex justify-end sm:col-span-2">
            <Button
              type="submit"
              loading={createMutation.isPending}
              disabled={!sectionId || !oppositeName}
            >
              Add polar variable
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Layout Tab (SRS §3_layout — report section ordering)
// ---------------------------------------------------------------------------

function LayoutTab({ reportId }: { reportId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: sections, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "sections"],
    queryFn: () => listSections(reportId),
  });
  const [sectionType, setSectionType] = useState("narrative");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [order, setOrder] = useState("0");
  const [isVisible, setIsVisible] = useState(true);

  const createMutation = useMutation({
    mutationFn: () =>
      createSection(reportId, {
        section_type: sectionType,
        title,
        content,
        table_graph_config: null,
        order: Number(order),
        is_visible: isVisible,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "sections"],
      });
      toast.success("Section added.");
      setTitle("");
      setContent("");
      setOrder(String(Number(order) + 1));
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedIds: number[]) => reorderSections(reportId, orderedIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "sections"],
      });
      toast.success("Order saved.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (isLoading) return <Spinner />;
  const list = sections ?? [];

  const move = (index: number, direction: "up" | "down") => {
    const newOrder = [...list.map((s) => s.id)];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= newOrder.length) return;
    [newOrder[index], newOrder[targetIndex]] = [newOrder[targetIndex], newOrder[index]];
    reorderMutation.mutate(newOrder);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Report Layout (SRS §3_layout)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Define the order of sections in the report. Use the up/down arrows to reorder. Custom
          narrative sections are rendered as styled callout boxes in the PDF.
        </p>
        {list.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            No layout sections yet. Add one below.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Order</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Visible</TableHead>
                <TableHead className="w-24">Move</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((s, i) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.order}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{s.section_type}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-900">{s.title || "—"}</TableCell>
                  <TableCell>
                    <Badge variant={s.is_visible ? "success" : "default"}>
                      {s.is_visible ? "yes" : "no"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => move(i, "up")}
                        disabled={i === 0 || reorderMutation.isPending}
                      >
                        ↑
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => move(i, "down")}
                        disabled={i === list.length - 1 || reorderMutation.isPending}
                      >
                        ↓
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-2"
        >
          <div>
            <Label htmlFor="ls-t" required>
              Section type
            </Label>
            <select
              id="ls-t"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={sectionType}
              onChange={(e) => setSectionType(e.target.value)}
            >
              {SECTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="ls-o">Order</Label>
            <Input
              id="ls-o"
              type="number"
              min="0"
              value={order}
              onChange={(e) => setOrder(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="ls-title">Title</Label>
            <Input
              id="ls-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Section title (optional)"
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="ls-content">Content / narrative text</Label>
            <textarea
              id="ls-content"
              rows={3}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Free text for narrative sections, or JSON config for charts"
            />
          </div>
          <div className="flex items-center gap-2 sm:col-span-2">
            <input
              id="ls-v"
              type="checkbox"
              checked={isVisible}
              onChange={(e) => setIsVisible(e.target.checked)}
              className="h-4 w-4"
            />
            <Label htmlFor="ls-v" className="mb-0">
              Visible in report
            </Label>
          </div>
          <div className="flex justify-end sm:col-span-2">
            <Button type="submit" loading={createMutation.isPending}>
              Add section
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
