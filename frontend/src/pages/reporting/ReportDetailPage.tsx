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
  DATA_INPUT_LEVELS,
  generateGroupReport,
  generateReport,
  listGeneratedReports,
  publishReport,
  REPORT_TYPES,
  retrieveReport,
  STAT_CONVERSIONS,
  selectProfilingData,
  type GroupReportData,
  type ProfilingSelectionResult,
} from "@/api/reporting";
import { listSessions } from "@/api/assessment";
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
                      <details className="text-xs">
                        <summary className="cursor-pointer text-primary-600 hover:underline">
                          View data
                        </summary>
                        <pre className="mt-2 max-h-96 overflow-auto rounded-md bg-slate-50 p-3 text-xs">
                          {JSON.stringify(g.rendered_data, null, 2)}
                        </pre>
                      </details>
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
