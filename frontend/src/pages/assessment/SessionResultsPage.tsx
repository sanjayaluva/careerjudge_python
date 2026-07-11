/**
 * Session Results Page — shows scores after assessment submission.
 *
 * Fetches the session summary plus per-section score breakdown from the API.
 *
 * Route: /assessments/sessions/:sessionId/results
 */
import { useQuery } from "@tanstack/react-query";
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
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import { getSessionSectionScores, retrieveSession, type SectionScore } from "@/api/assessment";

export default function SessionResultsPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const sid = Number(sessionId);

  const {
    data: session,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["assessment-session", sid],
    queryFn: () => retrieveSession(sid),
    enabled: !Number.isNaN(sid),
  });

  // Fetch section score breakdown (only meaningful for completed sessions)
  const { data: sectionScores, isLoading: scoresLoading } = useQuery({
    queryKey: ["assessment-session-section-scores", sid],
    queryFn: () => getSessionSectionScores(sid),
    enabled: !Number.isNaN(sid) && session?.status === "completed",
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load session results.</AlertDescription>
      </Alert>
    );
  }

  const percentage = session.percentage ?? 0;
  const passed = percentage >= 40;
  const hasSectionScores = (sectionScores?.length ?? 0) > 0;

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link to="/assessments" className="text-sm text-primary-600 hover:underline">
          ← Back to Assessments
        </Link>
        <h1 className="mt-2 text-xl font-bold text-slate-900">Assessment Results</h1>
        <p className="text-sm text-slate-500">{session.assessment_title}</p>
      </div>

      {/* Score summary */}
      <Card>
        <CardHeader>
          <CardTitle>Score Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-md border border-slate-200 p-4 text-center">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Total Score
              </p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {session.total_score?.toFixed(1) ?? "—"}
              </p>
              <p className="text-sm text-slate-400">/ {session.max_score?.toFixed(1) ?? "—"}</p>
            </div>
            <div className="rounded-md border border-slate-200 p-4 text-center">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Percentage
              </p>
              <p className="mt-1 text-3xl font-bold text-slate-900">{percentage.toFixed(1)}%</p>
            </div>
            <div className="rounded-md border border-slate-200 p-4 text-center">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</p>
              <div className="mt-2">
                <Badge variant={passed ? "success" : "warning"}>
                  {passed ? "Passed" : "Below threshold"}
                </Badge>
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-md bg-slate-50 p-3 text-sm">
              <span className="text-slate-500">Started:</span>{" "}
              <span className="text-slate-900">
                {new Date(session.started_at).toLocaleString()}
              </span>
            </div>
            <div className="rounded-md bg-slate-50 p-3 text-sm">
              <span className="text-slate-500">Completed:</span>{" "}
              <span className="text-slate-900">
                {session.completed_at ? new Date(session.completed_at).toLocaleString() : "—"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section Score Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Section Score Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          {scoresLoading ? (
            <div className="flex justify-center py-6">
              <Spinner />
            </div>
          ) : hasSectionScores ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Section</TableHead>
                  <TableHead className="text-right">Raw Score</TableHead>
                  <TableHead className="text-right">Max Score</TableHead>
                  <TableHead className="text-right">Percentage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sectionScores!.map((ss: SectionScore) => (
                  <TableRow key={ss.id}>
                    <TableCell className="font-medium text-slate-900">{ss.section_title}</TableCell>
                    <TableCell className="text-right">{ss.raw_score.toFixed(2)}</TableCell>
                    <TableCell className="text-right">{ss.max_score.toFixed(2)}</TableCell>
                    <TableCell className="text-right">
                      <Badge
                        variant={
                          ss.percentage >= 60
                            ? "success"
                            : ss.percentage >= 40
                              ? "warning"
                              : "danger"
                        }
                      >
                        {ss.percentage.toFixed(1)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="py-4 text-sm text-slate-500">
              No section scores available. This session may not have been scored yet.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Session info */}
      <Card>
        <CardHeader>
          <CardTitle>Session Details</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Field</TableHead>
                <TableHead>Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="text-slate-500">Session ID</TableCell>
                <TableCell>{session.id}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-slate-500">Candidate</TableCell>
                <TableCell>{session.candidate_name ?? session.candidate}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-slate-500">Status</TableCell>
                <TableCell>
                  <Badge variant={session.status === "completed" ? "success" : "default"}>
                    {session.status}
                  </Badge>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-slate-500">Raw Score</TableCell>
                <TableCell>{session.total_score?.toFixed(2) ?? "—"}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-slate-500">Max Score</TableCell>
                <TableCell>{session.max_score?.toFixed(2) ?? "—"}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-slate-500">Percentage</TableCell>
                <TableCell>{session.percentage?.toFixed(2) ?? "—"}%</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button variant="outline" onClick={() => (window.location.href = "/assessments")}>
          Back to Assessments
        </Button>
      </div>
    </div>
  );
}
