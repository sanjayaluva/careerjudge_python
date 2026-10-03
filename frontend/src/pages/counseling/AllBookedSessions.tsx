/**
 * All booked sessions — Help Desk's read-only view of every counselling
 * session booked in the system (Report 9 #115). The server already returns
 * all sessions to Help Desk; this lists them page by page.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  Badge,
  Button,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import { apiGetPaged } from "@/api/client";
import type { CounselingSession } from "@/api/counseling";

const PAGE_SIZE = 20;

const STATUS_VARIANT: Record<string, "success" | "primary" | "danger" | "warning"> = {
  completed: "success",
  confirmed: "primary",
  cancelled: "danger",
  pending: "warning",
};

export function AllBookedSessions() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["counseling", "all-sessions", page],
    queryFn: () =>
      apiGetPaged<CounselingSession>("/counseling/sessions/", {
        params: { page, page_size: PAGE_SIZE },
      }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  const sessions = data?.results ?? [];
  const count = data?.count ?? 0;
  if (sessions.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-8 text-center text-sm text-slate-500">
        No sessions have been booked.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-500">
        {count} booked session{count !== 1 ? "s" : ""} — view only
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Counsellor</TableHead>
            <TableHead>Counselee</TableHead>
            <TableHead>Date &amp; time</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Topic</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sessions.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-medium text-slate-900">{s.counsellor_name}</TableCell>
              <TableCell>
                <div className="text-slate-900">{s.counselee_name || s.counselee_email}</div>
                {s.counselee_name && (
                  <div className="text-xs text-slate-500">{s.counselee_email}</div>
                )}
              </TableCell>
              <TableCell className="text-slate-600">
                {s.timeslot_detail ? new Date(s.timeslot_detail.start_time).toLocaleString() : "—"}
              </TableCell>
              <TableCell>
                <Badge variant={STATUS_VARIANT[s.status] ?? "warning"}>{s.status}</Badge>
              </TableCell>
              <TableCell className="text-slate-600">{s.category_name ?? "—"}</TableCell>
              <TableCell className="text-slate-600">{s.topic || "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {(data?.previous || data?.next) && (
        <div className="flex items-center justify-end gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={!data?.previous}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-xs text-slate-500">Page {page}</span>
          <Button
            size="sm"
            variant="outline"
            disabled={!data?.next}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
