/**
 * Session Results Page — shows scores after assessment submission.
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
} from "@/components/ui";
import { retrieveSession } from "@/api/assessment";

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
  const passed = percentage >= 40; // TODO: configurable pass mark

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

      {/* Section scores (if available) */}
      <Card>
        <CardHeader>
          <CardTitle>Section Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-slate-500">
            Detailed section scores will appear here once the scoring engine generates them. The
            session has been submitted and scored successfully.
          </p>
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
