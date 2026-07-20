/**
 * Reports page — list report definitions + create new.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  Input,
  Label,
  Modal,
  PageCard,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  useToast,
} from "@/components/ui";
import {
  createReport,
  listReports,
  REPORT_STATUSES,
  REPORT_TYPES,
  DATA_INPUT_LEVELS,
  STAT_CONVERSIONS,
} from "@/api/reporting";
import { listAssessments } from "@/api/assessment";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const REPORT_KEY = ["reporting", "reports"];
const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function ReportsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const canManage = ["cj_admin", "psychometrician", "counsellor"].includes(user?.role ?? "");

  const { data, isLoading } = useQuery({
    queryKey: [...REPORT_KEY, debouncedSearch, statusFilter],
    queryFn: () =>
      listReports({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createReport(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: REPORT_KEY });
      setCreateOpen(false);
      toast.success("Report created.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const reports = data?.results ?? [];

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Reports</h1>
            <p className="text-sm text-slate-500">
              {data?.count ?? 0} report{(data?.count ?? 0) !== 1 ? "s" : ""}
            </p>
          </div>
          {canManage && <Button onClick={() => setCreateOpen(true)}>Create report</Button>}
        </div>
        <div className="flex flex-wrap items-center gap-2 px-6 pb-4">
          <Input
            type="search"
            placeholder="Search reports..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setTimeout(() => setDebouncedSearch(e.target.value), 350);
            }}
            className="max-w-sm"
          />
          <select
            className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            {REPORT_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : reports.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No reports yet. Create one to get started.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead>Assessment</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created by</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium text-slate-900">
                    <Link to={`/reports/${r.id}`} className="text-primary-600 hover:underline">
                      {r.title}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {REPORT_TYPES.find((t) => t.value === r.report_type)?.label ?? r.report_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">{r.scope}</TableCell>
                  <TableCell className="text-slate-500">{r.assessment_title ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[r.status] ?? "default"}>{r.status}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">{r.created_by_name ?? "—"}</TableCell>
                  <TableCell className="text-slate-500">
                    {new Date(r.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </PageCard>
      {createOpen && (
        <CreateReportModal
          loading={createMutation.isPending}
          onClose={() => setCreateOpen(false)}
          onSubmit={(payload) => createMutation.mutate(payload)}
        />
      )}
    </div>
  );
}

function CreateReportModal({
  loading,
  onClose,
  onSubmit,
}: {
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [reportType, setReportType] = useState("descriptive");
  const [scope, setScope] = useState("general");
  const [assessmentId, setAssessmentId] = useState("");
  const [dataInputLevel, setDataInputLevel] = useState("level1");
  const [statConversion, setStatConversion] = useState("percentage");

  const { data: assessments } = useQuery({
    queryKey: ["assessments", "for-report"],
    queryFn: () => listAssessments({ status: "published" }),
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Create Report"
      description="Define a new report."
      size="md"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const payload: Record<string, unknown> = {
            title,
            objective,
            report_type: reportType,
            scope,
            data_input_level: dataInputLevel,
            stat_conversion: statConversion,
          };
          if (scope === "general" && assessmentId) {
            payload.assessment = Number(assessmentId);
          }
          onSubmit(payload);
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="r-title" required>
            Report title
          </Label>
          <Input
            id="r-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Career Aptitude Report"
            required
          />
        </div>
        <div>
          <Label htmlFor="r-objective">Objective</Label>
          <textarea
            id="r-objective"
            rows={2}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="r-type">Report type</Label>
            <select
              id="r-type"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              {REPORT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="r-scope">Scope</Label>
            <select
              id="r-scope"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              <option value="general">General (single assessment)</option>
              <option value="profiling">Profiling (multiple assessments)</option>
            </select>
          </div>
        </div>
        {scope === "general" && (
          <div>
            <Label htmlFor="r-assessment" required>
              Assessment
            </Label>
            <select
              id="r-assessment"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={assessmentId}
              onChange={(e) => setAssessmentId(e.target.value)}
              required
            >
              <option value="">Select an assessment...</option>
              {(assessments?.results ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="r-level">Data input level</Label>
            <select
              id="r-level"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={dataInputLevel}
              onChange={(e) => setDataInputLevel(e.target.value)}
            >
              {DATA_INPUT_LEVELS.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="r-conv">Statistical conversion</Label>
            <select
              id="r-conv"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={statConversion}
              onChange={(e) => setStatConversion(e.target.value)}
            >
              {STAT_CONVERSIONS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create report
          </Button>
        </div>
      </form>
    </Modal>
  );
}
