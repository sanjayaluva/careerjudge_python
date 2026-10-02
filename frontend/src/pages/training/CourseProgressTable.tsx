/**
 * Learners' course progress at a glance — Report 8.1 #62 (the trainer, on his
 * course's Registrations tab) and Report 9 #17 (Corp Admin / Corp Exclusive /
 * Group Admin, for their members in a licensed course). One row per learner:
 * status, completion %, items done of total, started, last activity and
 * assessment scores.
 */
import type { ReactNode } from "react";

import {
  Badge,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import {
  completionStatusLabel,
  completionStatusVariant,
  type LearnerProgress,
} from "@/api/training";

const date = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString() : "—");

export function CourseProgressTable({
  rows,
  showPayment = false,
  actions,
}: {
  rows: LearnerProgress[];
  showPayment?: boolean;
  /** Extra per-learner buttons (the trainer's Reports / Messages). */
  actions?: (row: LearnerProgress) => ReactNode;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Learner</TableHead>
          {showPayment && <TableHead>Payment</TableHead>}
          <TableHead>Status</TableHead>
          <TableHead>Completion</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Last activity</TableHead>
          <TableHead>Assessment scores</TableHead>
          {actions && <TableHead className="text-right">Actions</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.registration_id}>
            <TableCell className="align-top">
              <div className="font-medium text-slate-900">{r.full_name || r.email}</div>
              {r.full_name && <div className="text-xs text-slate-500">{r.email}</div>}
            </TableCell>
            {showPayment && (
              <TableCell className="align-top">
                <Badge
                  variant={
                    r.payment_status === "paid"
                      ? "success"
                      : r.payment_status === "pending"
                        ? "warning"
                        : "danger"
                  }
                >
                  {r.payment_status}
                </Badge>
              </TableCell>
            )}
            <TableCell className="align-top">
              <Badge variant={completionStatusVariant(r.completion_status)}>
                {completionStatusLabel(r.completion_status)}
              </Badge>
            </TableCell>
            <TableCell className="min-w-[8rem] align-top">
              <div className="text-sm font-medium text-slate-900">{r.completion_percentage}%</div>
              <div
                className="mt-1 h-1.5 w-full rounded-full bg-slate-100"
                role="progressbar"
                aria-valuenow={r.completion_percentage}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-1.5 rounded-full bg-primary-500"
                  style={{ width: `${Math.min(100, r.completion_percentage)}%` }}
                />
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {r.completed_count} of {r.total_count} items
              </div>
            </TableCell>
            <TableCell className="align-top text-slate-500">{date(r.started_at)}</TableCell>
            <TableCell className="align-top text-slate-500">{date(r.last_activity_at)}</TableCell>
            <TableCell className="align-top text-xs text-slate-600">
              {r.assessment_scores.length === 0 ? (
                <span className="text-slate-400">—</span>
              ) : (
                <ul className="space-y-0.5">
                  {r.assessment_scores.map((s) => (
                    <li key={s.course_assessment_id}>
                      {s.title}:{" "}
                      {s.status === "completed" && s.percentage != null ? (
                        <span className="font-medium text-slate-900">{s.percentage}%</span>
                      ) : (
                        <span className="text-slate-400">not attempted</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </TableCell>
            {actions && <TableCell className="text-right align-top">{actions(r)}</TableCell>}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
