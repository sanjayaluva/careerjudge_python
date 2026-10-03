/**
 * Career Profiling page — authors (CJ Admin, Psychometrician) list profiling
 * solutions of every status and create new ones; everyone else sees the
 * published solutions available to them (Report 9 #76), in Not attempted /
 * Suspended / Completed tabs (#77).
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "@/components/ui";
import {
  approveSolutionModificationRequest,
  createSolution,
  declineSolutionModificationRequest,
  listSolutionModificationRequests,
  listSolutions,
  SOLUTION_STATUSES,
  type ProfilingSolution,
} from "@/api/careerProfiling";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const CP_KEY = ["career-profiling", "solutions"];

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function CareerProfilingPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const canManage = ["cj_admin", "psychometrician"].includes(user?.role ?? "");
  // Report 9 #114: Help Desk views every solution (read-only author list).
  const canBrowseAll = canManage || user?.role === "helpdesk";

  const { data, isLoading } = useQuery({
    enabled: canBrowseAll,
    queryKey: [...CP_KEY, debouncedSearch, statusFilter],
    queryFn: () =>
      listSolutions({
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createSolution(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CP_KEY });
      setCreateOpen(false);
      toast.success("Profiling solution created.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const solutions = data?.results ?? [];

  // Report 9 #107: CJ Admin's queue of the Psychometrician's edit/delete
  // requests (same place as the question-bank and assessment queues).
  const isCjAdmin = user?.role === "cj_admin";
  const requestsQuery = useQuery({
    queryKey: ["cp-modification-requests"],
    queryFn: listSolutionModificationRequests,
    enabled: isCjAdmin,
  });
  const pendingRequests = (requestsQuery.data ?? []).filter((r) => r.status === "pending");
  const reviewRequestMutation = useMutation({
    mutationFn: (v: { id: number; approve: boolean }) =>
      v.approve
        ? approveSolutionModificationRequest(v.id)
        : declineSolutionModificationRequest(v.id),
    onSuccess: () => {
      toast.success("Request reviewed.");
      void queryClient.invalidateQueries({ queryKey: ["cp-modification-requests"] });
      void queryClient.invalidateQueries({ queryKey: CP_KEY });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Report 9 #76: a candidate (individual or any non-author) is not an
  // author — no status filter or Create button; the server returns only
  // published solutions.
  if (!canBrowseAll) return <PublishedSolutionsView />;

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex flex-col gap-4 p-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">
              Career Profiling
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {data?.count ?? 0} profiling solution{(data?.count ?? 0) !== 1 ? "s" : ""}
            </p>
          </div>
          {canManage && <Button onClick={() => setCreateOpen(true)}>Create solution</Button>}
        </div>

        <div className="flex flex-wrap items-center gap-2 px-6 pb-4">
          <Input
            type="search"
            placeholder="Search solutions..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setTimeout(() => setDebouncedSearch(e.target.value), 350);
            }}
            className="w-full sm:max-w-sm"
          />
          <select
            className="cj-select h-10 w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-sm transition-colors hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25 sm:w-44"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            {SOLUTION_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {isCjAdmin && pendingRequests.length > 0 && (
          <div className="mx-6 mb-3 rounded-md border border-warning-200 bg-warning-50 p-3">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-warning-800">
              Pending change requests ({pendingRequests.length})
            </p>
            <ul className="space-y-2">
              {pendingRequests.map((r) => (
                <li
                  key={r.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-warning-200 bg-white p-2.5 text-sm"
                >
                  <div className="min-w-0">
                    <span className="font-medium text-slate-800">
                      {r.action === "delete"
                        ? `Delete solution: ${r.solution_title}`
                        : `Rename "${r.solution_title}" to "${r.proposed_title ?? ""}"`}
                    </span>
                    <span className="block text-xs text-slate-500">
                      {r.requester_name ?? "A user"} — {r.reason}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={r.action === "delete" ? "danger" : "primary"}
                      loading={reviewRequestMutation.isPending}
                      onClick={() => reviewRequestMutation.mutate({ id: r.id, approve: true })}
                    >
                      {r.action === "delete" ? "Approve delete" : "Approve"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => reviewRequestMutation.mutate({ id: r.id, approve: false })}
                    >
                      Decline
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : solutions.length === 0 ? (
          <p className="mx-6 mb-6 rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center text-sm text-slate-500">
            No profiling solutions yet. Create one to get started.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Assessments</TableHead>
                <TableHead>Polar</TableHead>
                <TableHead>Created by</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {solutions.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium text-slate-900">
                    <Link
                      to={`/career-profiling/${s.id}`}
                      className="text-primary-600 hover:underline"
                    >
                      {s.title}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[s.status] ?? "default"}>{s.status}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">{s.assessment_count}</TableCell>
                  <TableCell>
                    {s.has_polar_assessment ? (
                      <Badge variant="warning">Polar</Badge>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-slate-500">{s.created_by_name ?? "—"}</TableCell>
                  <TableCell className="text-slate-500">
                    {new Date(s.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </PageCard>

      <CreateSolutionModal
        open={createOpen}
        loading={createMutation.isPending}
        onClose={() => setCreateOpen(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />
    </div>
  );
}

// Report 9 #77: the candidate's solutions in Not attempted / Suspended /
// Completed tabs, by his sessions on each solution's assessments.
const CANDIDATE_TABS: {
  value: "not_attempted" | "suspended" | "completed";
  label: string;
  empty: string;
}[] = [
  { value: "not_attempted", label: "Not attempted", empty: "Nothing left to start." },
  { value: "suspended", label: "Suspended", empty: "No solutions in progress." },
  { value: "completed", label: "Completed", empty: "No completed solutions yet." },
];

const ASSESSMENT_STATUS: Record<
  string,
  { label: string; variant: "default" | "warning" | "success" }
> = {
  not_attempted: { label: "Not attempted", variant: "default" },
  in_progress: { label: "In progress", variant: "warning" },
  completed: { label: "Completed", variant: "success" },
};

function PublishedSolutionsView() {
  const { data, isLoading } = useQuery({
    queryKey: [...CP_KEY, "published"],
    queryFn: () => listSolutions(),
  });
  const solutions = data?.results ?? [];
  const inTab = (tab: string) => solutions.filter((s) => (s.my_status ?? "not_attempted") === tab);

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="p-6">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Career Profiling</h1>
          <p className="mt-1 text-sm text-slate-500">
            {solutions.length} profiling solution{solutions.length !== 1 ? "s" : ""} available
          </p>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : solutions.length === 0 ? (
          <p className="mx-6 mb-6 rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center text-sm text-slate-500">
            No profiling solutions are available yet.
          </p>
        ) : (
          <Tabs defaultValue="not_attempted">
            <div className="px-6">
              <TabsList>
                {CANDIDATE_TABS.map((t) => (
                  <TabsTrigger key={t.value} value={t.value}>
                    {t.label} ({inTab(t.value).length})
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            {CANDIDATE_TABS.map((t) => {
              const rows = inTab(t.value);
              return (
                <TabsContent key={t.value} value={t.value} className="px-6 pb-6 pt-4">
                  {rows.length === 0 ? (
                    <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center text-sm text-slate-500">
                      {t.empty}
                    </p>
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                      {rows.map((s) => (
                        <SolutionCard key={s.id} solution={s} />
                      ))}
                    </div>
                  )}
                </TabsContent>
              );
            })}
          </Tabs>
        )}
      </PageCard>
    </div>
  );
}

function SolutionCard({ solution: s }: { solution: ProfilingSolution }) {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
      {s.image && <img src={s.image} alt="" className="h-40 w-full object-cover" />}
      <div className="space-y-2 p-4">
        <h2 className="text-base font-semibold text-slate-900">{s.title}</h2>
        {s.purpose && <p className="text-sm text-slate-600">{s.purpose}</p>}
        {s.description && (
          <p className="whitespace-pre-line text-sm text-slate-600">{s.description}</p>
        )}
        {s.my_assessments && s.my_assessments.length > 0 ? (
          <ul className="space-y-1 border-t border-slate-100 pt-2">
            {s.my_assessments.map((a) => {
              const st = ASSESSMENT_STATUS[a.status] ?? ASSESSMENT_STATUS.not_attempted;
              return (
                <li key={a.assessment_id} className="flex items-center justify-between gap-2">
                  <Link
                    to={`/assessments/${a.assessment_id}`}
                    className="text-sm text-primary-600 hover:underline"
                  >
                    {a.title}
                  </Link>
                  <Badge variant={st.variant}>{st.label}</Badge>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-xs text-slate-400">
            {s.assessment_count} assessment{s.assessment_count !== 1 ? "s" : ""}
          </p>
        )}
      </div>
    </div>
  );
}

function CreateSolutionModal({
  open,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [title, setTitle] = useState("");
  const [purpose, setPurpose] = useState("");
  const [description, setDescription] = useState("");
  const [hasPolar, setHasPolar] = useState(false);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create Profiling Solution"
      description="Define a new profiling solution that combines 2-3 assessments."
      size="md"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({ title, purpose, description, has_polar_assessment: hasPolar });
          setTitle("");
          setPurpose("");
          setDescription("");
          setHasPolar(false);
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="cp-title" required>
            Solution title
          </Label>
          <Input
            id="cp-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Career Aptitude Profile"
            required
          />
        </div>
        <div>
          <Label htmlFor="cp-purpose">Purpose</Label>
          <textarea
            id="cp-purpose"
            rows={2}
            className="min-h-[5rem] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder="What this solution measures..."
          />
        </div>
        <div>
          <Label htmlFor="cp-desc">Description</Label>
          <textarea
            id="cp-desc"
            rows={3}
            className="min-h-[5rem] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detailed description of the solution..."
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={hasPolar}
            onChange={(e) => setHasPolar(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
          />
          Includes a Polar assessment
        </label>
        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 pt-4 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create solution
          </Button>
        </div>
      </form>
    </Modal>
  );
}
