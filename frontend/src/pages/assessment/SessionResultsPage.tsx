/**
 * Session Results Page — shows scores after assessment submission.
 *
 * Fetches the session summary plus per-section score breakdown from the API.
 * cj_admin also sees a "Scoring Debug" tab with the full scoring pipeline.
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui";
import {
  getSessionDebug,
  getSessionSectionScores,
  retrieveSession,
  type SectionScore,
  type SessionDebugData,
} from "@/api/assessment";
import { useAuth } from "@/hooks/useAuth";

export default function SessionResultsPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const sid = Number(sessionId);
  const { user } = useAuth();
  const isAdmin = user?.role === "cj_admin";

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

  // Fetch debug data (cj_admin only)
  const { data: debugData, isLoading: debugLoading } = useQuery({
    queryKey: ["assessment-session-debug", sid],
    queryFn: () => getSessionDebug(sid),
    enabled: !Number.isNaN(sid) && isAdmin && session?.status === "completed",
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

      <Tabs defaultValue="results">
        <TabsList>
          <TabsTrigger value="results">Results</TabsTrigger>
          {isAdmin && <TabsTrigger value="debug">🔧 Scoring Debug</TabsTrigger>}
        </TabsList>

        {/* === RESULTS TAB === */}
        <TabsContent value="results" className="space-y-6">
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
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Status
                  </p>
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
                        <TableCell className="font-medium text-slate-900">
                          {ss.section_title}
                        </TableCell>
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
        </TabsContent>

        {/* === DEBUG TAB (cj_admin only) === */}
        {isAdmin && (
          <TabsContent value="debug">
            {debugLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : debugData ? (
              <ScoringDebugView data={debugData} />
            ) : (
              <Alert>
                <AlertDescription>
                  Debug data not available. The session may not be completed yet.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
        )}
      </Tabs>

      <div className="flex justify-center">
        <Button variant="outline" onClick={() => (window.location.href = "/assessments")}>
          Back to Assessments
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scoring Debug View — full pipeline breakdown for cj_admin
// ---------------------------------------------------------------------------

function ScoringDebugView({ data }: { data: SessionDebugData }) {
  const { session, sections, section_scores, attempts } = data;

  return (
    <div className="space-y-6">
      {/* Session Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Session Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-slate-500">Assessment Type</p>
              <p className="font-medium">{session.assessment_type}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Candidate</p>
              <p className="font-medium">{session.candidate_email}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Questions</p>
              <p className="font-medium">{session.question_count}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Attempted / Unattempted</p>
              <p className="font-medium">
                {session.attempted_count} / {session.unattempted_count}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Total Score</p>
              <p className="font-medium">
                {session.total_score?.toFixed(2)} / {session.max_score?.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Percentage</p>
              <p className="font-medium">{session.percentage?.toFixed(2)}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Duration Limit</p>
              <p className="font-medium">
                {session.total_duration_seconds
                  ? `${Math.floor(session.total_duration_seconds / 60)} min`
                  : "No limit"}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Bookmarked</p>
              <p className="font-medium">{session.bookmarked_count}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section Hierarchy */}
      <Card>
        <CardHeader>
          <CardTitle>Section Hierarchy ({sections.length} sections)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Level</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Parent</TableHead>
                <TableHead className="text-right">Raw</TableHead>
                <TableHead className="text-right">Max</TableHead>
                <TableHead className="text-right">%</TableHead>
                <TableHead>Direct Qs?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {section_scores.map((ss) => (
                <TableRow key={ss.section_id}>
                  <TableCell>
                    <Badge variant="outline">L{ss.level}</Badge>
                  </TableCell>
                  <TableCell
                    className="font-medium"
                    style={{ paddingLeft: `${(ss.level - 1) * 1.5 + 0.75}rem` }}
                  >
                    {ss.title}
                  </TableCell>
                  <TableCell className="text-xs text-slate-400">
                    {sections.find((s) => s.id === ss.parent_id)?.title ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">{ss.raw_score.toFixed(2)}</TableCell>
                  <TableCell className="text-right">{ss.max_score.toFixed(2)}</TableCell>
                  <TableCell className="text-right">{ss.percentage.toFixed(1)}%</TableCell>
                  <TableCell>
                    {ss.has_direct_questions ? (
                      <Badge variant="primary">Yes</Badge>
                    ) : (
                      <span className="text-slate-300">No (rolled up)</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Per-Question Attempts */}
      <Card>
        <CardHeader>
          <CardTitle>Question Attempts ({attempts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {attempts.map((att, idx) => (
              <div
                key={att.attempt_id}
                className={`rounded-md border p-4 ${
                  att.score_matches === false
                    ? "border-danger-200 bg-danger-50"
                    : att.status === "attempted"
                      ? "border-slate-200"
                      : "border-amber-200 bg-amber-50"
                }`}
              >
                {/* Header row */}
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-bold text-slate-900">Q{idx + 1}.</span>
                  <Badge variant="outline">{att.question_type_label}</Badge>
                  <Badge variant="default">{att.scoring_type_label}</Badge>
                  {att.section_title && (
                    <span className="text-xs text-slate-500">
                      📁 {att.section_title} (L{att.section_level})
                    </span>
                  )}
                  <Badge
                    variant={
                      att.status === "attempted"
                        ? "success"
                        : att.status === "bookmarked"
                          ? "warning"
                          : "default"
                    }
                  >
                    {att.status}
                  </Badge>
                  {att.score_matches === false && <Badge variant="danger">⚠ Score mismatch!</Badge>}
                  <span className="ml-auto text-xs text-slate-400">
                    {att.answered_at ? new Date(att.answered_at).toLocaleString() : "Not answered"}
                    {att.time_spent_seconds ? ` · ${att.time_spent_seconds}s` : ""}
                  </span>
                </div>

                {/* Question title */}
                <p className="mb-2 text-sm font-medium text-slate-900">{att.question_title}</p>

                {/* Two-column: answer vs correct */}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {/* Candidate's answer */}
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase text-slate-500">
                      Candidate's Answer
                    </p>
                    <pre className="overflow-x-auto rounded-md bg-slate-900 p-2 text-xs text-green-400">
                      {att.raw_answer ? JSON.stringify(att.raw_answer, null, 2) : "(no answer)"}
                    </pre>
                  </div>

                  {/* Correct answer */}
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase text-slate-500">
                      Correct Answer
                    </p>
                    <pre className="overflow-x-auto rounded-md bg-slate-100 p-2 text-xs text-slate-700">
                      {att.correct_answer
                        ? JSON.stringify(att.correct_answer, null, 2)
                        : "(no correct answer configured)"}
                    </pre>
                  </div>
                </div>

                {/* Score breakdown */}
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                  <div className="rounded-md bg-slate-50 p-2">
                    <p className="text-slate-500">Stored Score</p>
                    <p className="font-bold text-slate-900">
                      {att.score?.toFixed(2) ?? "—"} / {att.max_score?.toFixed(2) ?? "—"}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-2">
                    <p className="text-slate-500">Re-calculated</p>
                    <p className="font-bold text-slate-900">
                      {att.calculated_score.toFixed(2)} / {att.calculated_max.toFixed(2)}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-2">
                    <p className="text-slate-500">Default Max</p>
                    <p className="font-bold text-slate-900">{att.default_max.toFixed(2)}</p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-2">
                    <p className="text-slate-500">Match?</p>
                    <p
                      className={`font-bold ${
                        att.score_matches ? "text-success-600" : "text-danger-600"
                      }`}
                    >
                      {att.score_matches === null
                        ? "—"
                        : att.score_matches
                          ? "✓ Yes"
                          : "✗ MISMATCH"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
