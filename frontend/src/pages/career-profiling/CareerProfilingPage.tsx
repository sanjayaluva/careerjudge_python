/**
 * Career Profiling page — list profiling solutions + create new.
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
import { createSolution, listSolutions, SOLUTION_STATUSES } from "@/api/careerProfiling";
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

  const { data, isLoading } = useQuery({
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

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Career Profiling</h1>
            <p className="text-sm text-slate-500">
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
            className="max-w-sm"
          />
          <select
            className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
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

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : solutions.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
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
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
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
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
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
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
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
