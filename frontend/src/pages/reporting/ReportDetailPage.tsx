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
  BAND_TARGET_TYPES,
  type BandTargetType,
  createBand,
  createCode,
  createCutoff,
  createPolarVariable,
  createSection,
  createSectionWithImage,
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
  updateReport,
  type GeneratedReport,
  type GroupReportData,
  type ProfilingSelectionResult,
  type Report,
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
  const [editOpen, setEditOpen] = useState(false);

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
                    {!report.include_raw_summary &&
                      !report.include_fmi &&
                      !report.include_pmi &&
                      !report.include_vmi && <span className="text-sm text-slate-400">None</span>}
                  </div>
                  {(report.pmi_d_first_assessment || report.pmi_d_second_assessment) && (
                    <div className="mt-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        PMI-D gap order
                      </div>
                      <p className="mt-1 text-sm text-slate-900">
                        {report.pmi_d_first_assessment || "—"} PMI −{" "}
                        {report.pmi_d_second_assessment || "—"} PMI
                      </p>
                    </div>
                  )}
                </div>
              )}

              {canManage && report.status === "draft" && (
                <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-4">
                  <Button variant="outline" onClick={() => setEditOpen(true)}>
                    Edit configuration
                  </Button>
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
      {editOpen && <EditConfigModal report={report} onClose={() => setEditOpen(false)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Edit Configuration Modal (REP-4) — profiling data inputs, PMI-D order,
// solution link, and shared report metadata (SRS 06 §3.1–3.4)
// ---------------------------------------------------------------------------

function EditConfigModal({ report, onClose }: { report: Report; onClose: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isProfiling = report.scope === "profiling";
  const [description, setDescription] = useState(report.description ?? "");
  const [includeRawSummary, setIncludeRawSummary] = useState(report.include_raw_summary);
  const [includeFmi, setIncludeFmi] = useState(report.include_fmi);
  const [includePmi, setIncludePmi] = useState(report.include_pmi);
  const [includeVmi, setIncludeVmi] = useState(report.include_vmi);
  const [pmiDFirst, setPmiDFirst] = useState(report.pmi_d_first_assessment ?? "");
  const [pmiDSecond, setPmiDSecond] = useState(report.pmi_d_second_assessment ?? "");

  const mutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { description };
      if (isProfiling) {
        payload.include_raw_summary = includeRawSummary;
        payload.include_fmi = includeFmi;
        payload.include_pmi = includePmi;
        payload.include_vmi = includeVmi;
        payload.pmi_d_first_assessment = pmiDFirst.trim();
        payload.pmi_d_second_assessment = pmiDSecond.trim();
      }
      return updateReport(report.id, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...REPORT_KEY, report.id] });
      toast.success("Configuration updated.");
      onClose();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const toggles: [string, boolean, (v: boolean) => void][] = [
    ["Raw summary %", includeRawSummary, setIncludeRawSummary],
    ["FMI (Final Match Index)", includeFmi, setIncludeFmi],
    ["PMI (Profile Match Index)", includePmi, setIncludePmi],
    ["VMI (Variable Match Index)", includeVmi, setIncludeVmi],
  ];

  return (
    <Modal open onClose={onClose} title="Edit report configuration" size="md">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="ec-desc">Description</Label>
          <textarea
            id="ec-desc"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        {isProfiling && (
          <>
            <div>
              <p className="mb-1 text-sm font-medium text-slate-700">Include indices</p>
              <div className="grid grid-cols-2 gap-2">
                {toggles.map(([label, val, set]) => (
                  <label key={label} className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={val}
                      onChange={(e) => set(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1 text-sm font-medium text-slate-700">
                PMI-D gap order (A1PMI − A2PMI)
              </p>
              <p className="mb-2 text-xs text-slate-500">
                Name the two assessments whose PMI is subtracted to form the gap index. Leave blank
                to omit PMI-D.
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  placeholder="A1 (minuend)"
                  value={pmiDFirst}
                  onChange={(e) => setPmiDFirst(e.target.value)}
                />
                <Input
                  placeholder="A2 (subtrahend)"
                  value={pmiDSecond}
                  onChange={(e) => setPmiDSecond(e.target.value)}
                />
              </div>
            </div>
          </>
        )}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Save changes
          </Button>
        </div>
      </form>
    </Modal>
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
  const [preview, setPreview] = useState<GeneratedReport | null>(null);
  const { data: generated, isLoading } = useQuery({
    queryKey: ["reporting", "reports", reportId, "generated"],
    queryFn: () => listGeneratedReports(reportId),
  });

  if (isLoading) return <Spinner />;
  const list = generated ?? [];

  return (
    <>
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
                        <div className="flex flex-col items-start gap-1 text-xs">
                          <Button variant="outline" size="sm" onClick={() => setPreview(g)}>
                            Preview
                          </Button>
                          <a
                            href={generatedReportPdfUrl(g.id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:underline"
                          >
                            Download PDF ↓
                          </a>
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
      {preview && preview.rendered_data && (
        <Modal
          open
          onClose={() => setPreview(null)}
          title={`Report preview — ${preview.candidate_name ?? `User ${preview.candidate}`}`}
          size="lg"
        >
          <ReportPreview data={preview.rendered_data} />
          <div className="mt-4 flex justify-end border-t border-slate-100 pt-4">
            <a href={generatedReportPdfUrl(preview.id)} target="_blank" rel="noopener noreferrer">
              <Button variant="outline">Download PDF ↓</Button>
            </a>
          </div>
        </Modal>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Report Preview (REP-2 live preview) — render generated data in-app,
// mirroring the PDF: score summary, section + question breakdowns, and
// custom layout sections incl. table and SVG bar-chart (REP-1) layouts.
// ---------------------------------------------------------------------------

type PreviewRow = Record<string, unknown>;
function _num(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return typeof v === "number" ? String(Math.round(v * 100) / 100) : String(v);
}

function ReportPreview({ data }: { data: Record<string, unknown> }) {
  const scoreSummary = data.score_summary as PreviewRow | undefined;
  const sectionBreakdown = (data.section_breakdown as PreviewRow[] | undefined) ?? [];
  const questionBreakdown = (data.question_breakdown as PreviewRow[] | undefined) ?? [];
  const sections = (data.sections as PreviewRow[] | undefined) ?? [];

  return (
    <div className="max-h-[70vh] space-y-5 overflow-auto text-sm">
      <div>
        <h3 className="text-base font-bold text-slate-900">
          {String(data.report_title ?? "Report")}
        </h3>
        <p className="text-xs text-slate-500">
          {String(data.assessment_title ?? "")}
          {data.candidate ? ` · ${String((data.candidate as PreviewRow).name ?? "")}` : ""}
        </p>
      </div>

      {scoreSummary && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Score summary
          </div>
          <p className="mt-1 text-slate-900">
            {_num(scoreSummary.total)} / {_num(scoreSummary.max)} ({_num(scoreSummary.percentage)}%){" "}
            {scoreSummary.passed !== undefined && (
              <Badge variant={scoreSummary.passed ? "success" : "default"}>
                {scoreSummary.passed ? "Pass" : "Below threshold"}
              </Badge>
            )}
          </p>
        </div>
      )}

      {sectionBreakdown.length > 0 && (
        <PreviewScoreTable
          title="Section breakdown"
          variableHeader="Variable"
          rows={sectionBreakdown}
          labelKey="section_title"
        />
      )}

      {questionBreakdown.length > 0 && (
        <PreviewScoreTable
          title="Question breakdown"
          variableHeader="Question"
          rows={questionBreakdown}
          labelKey="question_label"
        />
      )}

      {sections.map((s, i) => (
        <PreviewCustomSection key={i} section={s} />
      ))}
    </div>
  );
}

function PreviewScoreTable({
  title,
  variableHeader,
  rows,
  labelKey,
}: {
  title: string;
  variableHeader: string;
  rows: PreviewRow[];
  labelKey: string;
}) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="py-1 pr-2">{variableHeader}</th>
              <th className="py-1 pr-2">Raw</th>
              <th className="py-1 pr-2">Max</th>
              <th className="py-1 pr-2">%</th>
              <th className="py-1">Converted</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-slate-100">
                <td className="py-1 pr-2 text-slate-900">{String(r[labelKey] ?? "—")}</td>
                <td className="py-1 pr-2">{_num(r.raw_score)}</td>
                <td className="py-1 pr-2">{_num(r.max_score)}</td>
                <td className="py-1 pr-2">{_num(r.percentage)}%</td>
                <td className="py-1">
                  {_num(r.converted_score)}{" "}
                  <span className="text-slate-400">({String(r.conversion_type ?? "")})</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PreviewCustomSection({ section }: { section: PreviewRow }) {
  const title = section.title ? String(section.title) : "";
  const description = section.description ? String(section.description) : "";
  const content = section.content ? String(section.content) : "";
  const graph = section.graph as
    { title?: string; bars?: PreviewRow[]; max_value?: number } | undefined;
  const table = section.table as { headers?: PreviewRow; rows?: PreviewRow[] } | undefined;

  if (!title && !description && !content && !graph && !table) return null;

  return (
    <div className="rounded-md border border-slate-200 p-3">
      {title && <div className="font-semibold text-slate-900">{title}</div>}
      {description && <p className="mt-1 text-slate-700">{description}</p>}
      {content && <p className="mt-1 whitespace-pre-wrap text-slate-700">{content}</p>}
      {graph?.bars && graph.bars.length > 0 && <PreviewBarChart graph={graph} />}
      {table?.rows && table.rows.length > 0 && (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full border-collapse text-xs">
            <tbody>
              {table.rows.map((r, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-1 pr-2 text-slate-900">{String(r.variable ?? "—")}</td>
                  <td className="py-1 pr-2">{_num(r.score)}</td>
                  <td className="py-1">{String(r.label ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PreviewBarChart({
  graph,
}: {
  graph: { title?: string; bars?: PreviewRow[]; max_value?: number };
}) {
  const bars = graph.bars ?? [];
  const maxValue = graph.max_value && graph.max_value > 0 ? graph.max_value : 100;
  return (
    <div className="mt-2 space-y-1">
      {graph.title && <div className="text-xs font-medium text-slate-700">{graph.title}</div>}
      {bars.map((b, i) => {
        const value = typeof b.value === "number" ? b.value : 0;
        const pct = Math.max(0, Math.min(100, (value / maxValue) * 100));
        const colour =
          typeof b.colour_code === "string" && b.colour_code ? b.colour_code : "#3b82f6";
        return (
          <div key={i} className="flex items-center gap-2">
            <span className="w-28 shrink-0 truncate text-xs text-slate-600">
              {String(b.variable ?? "")}
            </span>
            <div className="h-3 flex-1 rounded bg-slate-100">
              <div className="h-3 rounded" style={{ width: `${pct}%`, background: colour }} />
            </div>
            <span className="w-10 shrink-0 text-right text-xs text-slate-600">{_num(value)}</span>
          </div>
        );
      })}
    </div>
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
  const [targetType, setTargetType] = useState<BandTargetType>("section");
  const [sectionId, setSectionId] = useState("");
  const [assessmentLabel, setAssessmentLabel] = useState("");
  const [bandNumber, setBandNumber] = useState("1");
  const [rangeMin, setRangeMin] = useState("0");
  const [rangeMax, setRangeMax] = useState("100");
  const [bandLabel, setBandLabel] = useState("");
  const [description, setDescription] = useState("");
  const [colourCode, setColourCode] = useState("#3b82f6");

  // Section is only meaningful for interpretative (section-score) bands; the
  // assessment-label scope only applies to PMI/VMI (SRS 06 §3.3-3.4).
  const isSectionBand = targetType === "section";
  const scopesByAssessment = targetType === "pmi" || targetType === "vmi";

  const createMutation = useMutation({
    mutationFn: () =>
      createBand(reportId, {
        target_type: targetType,
        section: isSectionBand ? Number(sectionId) : null,
        assessment_label: scopesByAssessment ? assessmentLabel.trim() : "",
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
  const targetLabel = (t: BandTargetType) =>
    BAND_TARGET_TYPES.find((o) => o.value === t)?.label ?? t;
  const canSubmit = isSectionBand ? Boolean(sectionId) : true;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Band Definitions (Interpretative &amp; Profiling — SRS §3.3.1, 06 §3.1–3.4)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Define score bands. Interpretative bands map a <strong>section score</strong> to a label;
          profiling bands interpret the <strong>FMI, PMI, VMI, raw summary %</strong> or the
          <strong> PMI-D gap index</strong>. The candidate&apos;s value is matched to a band, and
          the band&apos;s label + description is shown in the report.
        </p>
        {list.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Target</TableHead>
                <TableHead>Variable / Scope</TableHead>
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
                  <TableCell className="text-xs font-medium text-slate-600">
                    {targetLabel(b.target_type)}
                  </TableCell>
                  <TableCell className="font-medium">
                    {b.target_type === "section"
                      ? b.section_title || "—"
                      : b.assessment_label || "All assessments"}
                  </TableCell>
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
            <Label htmlFor="bd-t" required>
              Band target
            </Label>
            <select
              id="bd-t"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={targetType}
              onChange={(e) => {
                setTargetType(e.target.value as BandTargetType);
                setSectionId("");
              }}
            >
              {BAND_TARGET_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              {isSectionBand
                ? "Pick the variable whose section score this band interprets."
                : scopesByAssessment
                  ? "Optionally scope this band to a single assessment; leave the label blank to apply to all."
                  : targetType === "pmi_d"
                    ? "PMI-D is a gap (A1PMI − A2PMI) and may be negative — ranges can go below 0."
                    : "This band applies to the whole report for the selected index."}
            </p>
          </div>
          {isSectionBand && (
            <div className="sm:col-span-3">
              <Label htmlFor="bd-s" required>
                Variable
              </Label>
              <SectionPicker sections={sectionList} value={sectionId} onChange={setSectionId} />
            </div>
          )}
          {scopesByAssessment && (
            <div className="sm:col-span-3">
              <Label htmlFor="bd-al">Assessment label (scope)</Label>
              <Input
                id="bd-al"
                value={assessmentLabel}
                onChange={(e) => setAssessmentLabel(e.target.value)}
                placeholder="e.g., CAT — leave blank for all assessments"
              />
            </div>
          )}
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
              min={targetType === "pmi_d" ? undefined : "0"}
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
              min={targetType === "pmi_d" ? undefined : "0"}
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
            <Button type="submit" loading={createMutation.isPending} disabled={!canSubmit}>
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
  const [description, setDescription] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [order, setOrder] = useState("0");
  const [isVisible, setIsVisible] = useState(true);
  // SRS §3.1.2/§3.2.2/§3.3.2: Table/Graph layout. "table" renders an
  // end-to-end table of section scores; "graph" is recorded but scoped out.
  const [layout, setLayout] = useState<"" | "table" | "graph">("");
  const [tableTitle, setTableTitle] = useState("");

  const createMutation = useMutation({
    mutationFn: () => {
      const table_graph_config = layout
        ? { layout, ...(tableTitle ? { table_title: tableTitle } : {}) }
        : null;
      const payload = {
        section_type: sectionType,
        title,
        content,
        description,
        table_graph_config,
        order: Number(order),
        is_visible: isVisible,
      };
      return image
        ? createSectionWithImage(reportId, { ...payload, image })
        : createSection(reportId, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["reporting", "reports", reportId, "sections"],
      });
      toast.success("Section added.");
      setTitle("");
      setContent("");
      setDescription("");
      setImage(null);
      setLayout("");
      setTableTitle("");
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
                  <TableCell className="text-slate-900">
                    {s.title || "—"}
                    {s.image && (
                      <Badge variant="outline" className="ml-1">
                        image
                      </Badge>
                    )}
                    {(s.table_graph_config as { layout?: string } | null)?.layout && (
                      <Badge variant="outline" className="ml-1">
                        {(s.table_graph_config as { layout?: string }).layout}
                      </Badge>
                    )}
                  </TableCell>
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
          <div className="sm:col-span-2">
            <Label htmlFor="ls-desc">Description (SRS §2.1.2)</Label>
            <textarea
              id="ls-desc"
              rows={2}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short description shown alongside this section"
            />
          </div>
          <div>
            <Label htmlFor="ls-image">Image upload (SRS §2.1.2)</Label>
            <input
              id="ls-image"
              type="file"
              accept="image/*"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
              className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-700 hover:file:bg-primary-100"
            />
          </div>
          <div>
            <Label htmlFor="ls-layout">Table/Graph layout</Label>
            <select
              id="ls-layout"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={layout}
              onChange={(e) => setLayout(e.target.value as "" | "table" | "graph")}
            >
              <option value="">None</option>
              <option value="table">Table (section scores)</option>
              <option value="graph">Graph (bar chart of section scores)</option>
            </select>
          </div>
          {(layout === "table" || layout === "graph") && (
            <div className="sm:col-span-2">
              <Label htmlFor="ls-table-title">
                {layout === "graph" ? "Chart title" : "Table title"}
              </Label>
              <Input
                id="ls-table-title"
                value={tableTitle}
                onChange={(e) => setTableTitle(e.target.value)}
                placeholder="e.g., Your Intellectual Profile"
              />
            </div>
          )}
          {layout === "graph" && (
            <p className="text-xs text-slate-500 sm:col-span-2">
              The graph renders as a bar chart of the report&apos;s section scores, coloured by any
              matching section bands, in both the PDF and the in-app preview.
            </p>
          )}
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
