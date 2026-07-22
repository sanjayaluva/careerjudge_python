/**
 * Course Player — student-facing course delivery experience (SRS §6).
 *
 * Features:
 * - Sequential content navigation (lesson → topic → session → content)
 * - Video/audio/text playback with InteractiveVideoPlayer for videos
 * - Auto-track progress: marks content as completed on playback end
 * - Assessment launch buttons at session/topic/lesson/course levels
 * - Assignment report submission form
 * - Progress dashboard: completion %, time spent, time left, resume
 * - Live session join links + consent
 *
 * The player reads the course structure (nested lessons → topics →
 * sessions → contents + assignments) and renders a sequential learning
 * experience. Students navigate through content; each piece auto-tracks
 * completion + time spent.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Label,
  Spinner,
  useToast,
} from "@/components/ui";
import {
  getProgressSummary,
  listAssignmentReports,
  listMyCourses,
  submitAssignmentReport,
  updateProgress,
  type InteractiveQuestion,
  type ProgressSummary,
  type SessionContent,
  type TopicSession,
  type TrainingCourse,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { InteractiveVideoPlayer } from "./InteractiveVideoPlayer";

// Flatten all content into a sequential list for navigation
interface FlatContent {
  lessonTitle: string;
  topicTitle: string;
  sessionTitle: string;
  content: SessionContent;
  session: TopicSession;
}

export function CoursePlayer({ course }: { course: TrainingCourse }) {
  const toast = useToast();

  // Get the student's registration for this course
  const { data: mySessions } = useQuery({
    queryKey: ["training", "my-courses"],
    queryFn: () => listMyCourses(),
  });

  const registration = useMemo(
    () => mySessions?.find((r) => r.course === course.id),
    [mySessions, course.id],
  );

  // Get progress summary
  const { data: progressSummary, isLoading: progressLoading } = useQuery({
    queryKey: ["training", "progress-summary", registration?.id],
    queryFn: () => getProgressSummary(registration!.id),
    enabled: !!registration,
  });

  // Flatten all content into sequential list
  const flatContent = useMemo<FlatContent[]>(() => {
    const items: FlatContent[] = [];
    for (const lesson of course.lessons) {
      for (const topic of lesson.topics) {
        for (const session of topic.sessions) {
          for (const content of session.contents) {
            items.push({
              lessonTitle: lesson.title,
              topicTitle: topic.title,
              sessionTitle: session.title,
              content,
              session,
            });
          }
        }
      }
    }
    return items;
  }, [course.lessons]);

  // Current content index (for sequential navigation)
  const [currentIdx, setCurrentIdx] = useState(0);
  const current = flatContent[currentIdx];

  if (!registration) {
    return (
      <Alert variant="warning">
        <AlertDescription>
          You need to register for this course before you can start learning.
        </AlertDescription>
      </Alert>
    );
  }

  if (registration.payment_status !== "paid") {
    return (
      <Alert variant="warning">
        <AlertDescription>
          Payment is pending. Once your payment is confirmed, you&apos;ll get access to the course
          content.
        </AlertDescription>
      </Alert>
    );
  }

  if (flatContent.length === 0) {
    return (
      <div className="space-y-4">
        <ProgressDashboard summary={progressSummary} loading={progressLoading} />
        <Alert>
          <AlertDescription>
            This course doesn&apos;t have any content yet. Please check back later.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Progress Dashboard */}
      <ProgressDashboard summary={progressSummary} loading={progressLoading} />

      {/* Main Content Player */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Content area (2/3) */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{current.content.title}</CardTitle>
                  <p className="mt-1 text-sm text-slate-500">
                    {current.lessonTitle} → {current.topicTitle} → {current.sessionTitle}
                  </p>
                </div>
                <Badge variant="outline">
                  {currentIdx + 1} / {flatContent.length}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <ContentPlayer
                content={current.content}
                registrationId={registration.id}
                onComplete={() => {
                  // Move to next content
                  if (currentIdx < flatContent.length - 1) {
                    setCurrentIdx(currentIdx + 1);
                  } else {
                    toast.success("🎉 You've completed all course content!");
                  }
                }}
              />

              {/* Navigation */}
              <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}
                  disabled={currentIdx === 0}
                >
                  ← Previous
                </Button>
                <span className="text-sm text-slate-500">
                  Content {currentIdx + 1} of {flatContent.length}
                </span>
                <Button
                  onClick={() => setCurrentIdx(Math.min(flatContent.length - 1, currentIdx + 1))}
                  disabled={currentIdx === flatContent.length - 1}
                >
                  Next →
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Assignments for current session */}
          {current.session.assignments.length > 0 && (
            <AssignmentsPanel session={current.session} registrationId={registration.id} />
          )}

          {/* Assessments for current session */}
          {course.assessments.filter((a) => a.session === current.session.id).length > 0 && (
            <AssessmentsPanel course={course} sessionId={current.session.id} />
          )}
        </div>

        {/* Sidebar: content list (1/3) */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Course Outline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 space-y-1 overflow-y-auto">
                {flatContent.map((item, idx) => (
                  <button
                    key={item.content.id}
                    onClick={() => setCurrentIdx(idx)}
                    className={`block w-full rounded-md px-3 py-2 text-left text-xs transition-colors ${
                      idx === currentIdx ? "bg-primary-50 text-primary-900" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="font-medium">{item.content.title}</div>
                    <div className="text-slate-400">
                      {item.lessonTitle} → {item.sessionTitle}
                    </div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Live sessions */}
          {course.live_sessions.filter((s) => s.status === "scheduled").length > 0 && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">Upcoming Live Sessions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {course.live_sessions
                  .filter((s) => s.status === "scheduled")
                  .map((s) => (
                    <div key={s.id} className="rounded-md border border-slate-100 p-2">
                      <div className="text-sm font-medium text-slate-900">{s.title}</div>
                      <div className="text-xs text-slate-500">
                        {new Date(s.scheduled_at).toLocaleString()}
                      </div>
                      {s.mode === "online" && s.meeting_url && (
                        <a
                          href={s.meeting_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 inline-block text-xs text-primary-600 hover:underline"
                        >
                          Join Zoom ↗
                        </a>
                      )}
                    </div>
                  ))}
              </CardContent>
            </Card>
          )}

          {/* Course-level assessment */}
          {course.assessments.filter((a) => a.level === "end_of_course").length > 0 && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">Final Assessment</CardTitle>
              </CardHeader>
              <CardContent>
                {course.assessments
                  .filter((a) => a.level === "end_of_course")
                  .map((a) => (
                    <div key={a.id} className="space-y-2">
                      <div className="text-sm font-medium text-slate-900">{a.title}</div>
                      <Button
                        size="sm"
                        onClick={() =>
                          window.open(`/assessment/${a.assessment}/session/new`, "_blank")
                        }
                      >
                        Take final assessment
                      </Button>
                    </div>
                  ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Content Player — renders video/audio/text + tracks progress
// ---------------------------------------------------------------------------

function ContentPlayer({
  content,
  registrationId,
  onComplete,
}: {
  content: SessionContent;
  registrationId: number;
  onComplete: () => void;
}) {
  const queryClient = useQueryClient();
  const startTimeRef = useRef<number>(Date.now());

  const trackProgress = useMutation({
    mutationFn: (isCompleted: boolean) => {
      const timeSpent = Math.round((Date.now() - startTimeRef.current) / 1000);
      return updateProgress(registrationId, {
        content_type: "session_content",
        content_id: content.id,
        is_completed: isCompleted,
        time_spent_seconds: timeSpent,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["training", "progress-summary", registrationId],
      });
    },
  });

  // Mark as completed + move to next
  const markComplete = () => {
    trackProgress.mutate(true);
    onComplete();
  };

  if (content.content_format === "video" && content.content_url) {
    return (
      <div className="space-y-3">
        <InteractiveVideoPlayer
          contentUrl={content.content_url}
          questions={content.interactive_questions as InteractiveQuestion[]}
        />
        <Button onClick={markComplete} loading={trackProgress.isPending}>
          ✓ Mark as completed
        </Button>
      </div>
    );
  }

  if (content.content_format === "audio" && content.content_url) {
    return (
      <div className="space-y-3">
        <audio controls className="w-full" src={content.content_url} onEnded={markComplete}>
          Your browser does not support audio playback.
        </audio>
        <Button onClick={markComplete} loading={trackProgress.isPending}>
          ✓ Mark as completed
        </Button>
      </div>
    );
  }

  if (content.content_format === "text") {
    return (
      <div className="space-y-3">
        <div className="prose max-w-none rounded-md border border-slate-100 bg-slate-50 p-4 text-sm">
          {content.text_content || content.content_url || "No text content available."}
        </div>
        <Button onClick={markComplete} loading={trackProgress.isPending}>
          ✓ Mark as completed &amp; Continue
        </Button>
      </div>
    );
  }

  // Fallback: just a link
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-500">
        Content: {content.title} ({content.content_format})
      </p>
      {content.content_url && (
        <a
          href={content.content_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 hover:underline"
        >
          Open content ↗
        </a>
      )}
      <Button onClick={markComplete} loading={trackProgress.isPending}>
        ✓ Mark as completed
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Progress Dashboard
// ---------------------------------------------------------------------------

function ProgressDashboard({ summary, loading }: { summary?: ProgressSummary; loading: boolean }) {
  if (loading || !summary) {
    return (
      <Card>
        <CardContent className="py-4">
          <Spinner />
        </CardContent>
      </Card>
    );
  }

  const pct = summary.completion_percentage;
  const hoursSpent = Math.floor(summary.total_time_spent_seconds / 3600);
  const minsSpent = Math.floor((summary.total_time_spent_seconds % 3600) / 60);

  const hoursLeft = summary.time_left_seconds ? Math.floor(summary.time_left_seconds / 3600) : null;
  const minsLeft = summary.time_left_seconds
    ? Math.floor((summary.time_left_seconds % 3600) / 60)
    : null;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {/* Completion */}
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Completion
            </div>
            <div className="mt-1 text-2xl font-bold text-slate-900">{pct}%</div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-primary-500 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-400">
              {summary.completed_count}/{summary.total_count} items
            </div>
          </div>

          {/* Time spent */}
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Time Spent
            </div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {hoursSpent}h {minsSpent}m
            </div>
          </div>

          {/* Time left (scheduled courses only) */}
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Time Left
            </div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {hoursLeft !== null ? `${hoursLeft}h ${minsLeft}m` : "∞"}
            </div>
            {summary.is_expired && (
              <Badge variant="danger" className="mt-1">
                Expired
              </Badge>
            )}
          </div>

          {/* Status */}
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</div>
            <div className="mt-1">
              <Badge
                variant={
                  summary.completion_status === "completed"
                    ? "success"
                    : summary.completion_status === "in_progress"
                      ? "primary"
                      : "default"
                }
              >
                {summary.completion_status.replace(/_/g, " ")}
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Assignments Panel — shows assignments + report submission
// ---------------------------------------------------------------------------

function AssignmentsPanel({
  session,
  registrationId,
}: {
  session: TopicSession;
  registrationId: number;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [submittingFor, setSubmittingFor] = useState<number | null>(null);
  const [reportText, setReportText] = useState("");

  const { data: existingReports } = useQuery({
    queryKey: ["training", "assignment-reports", registrationId],
    queryFn: () => listAssignmentReports(registrationId),
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      submitAssignmentReport(registrationId, {
        assignment: submittingFor!,
        report_text: reportText,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["training", "assignment-reports", registrationId],
      });
      toast.success("Report submitted. The trainer will review it.");
      setSubmittingFor(null);
      setReportText("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-sm">Assignments</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {session.assignments.map((a) => {
          const existingReport = existingReports?.find((r) => r.assignment === a.id);
          return (
            <div key={a.id} className="rounded-md border border-slate-100 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-slate-900">{a.title}</div>
                  {a.description && <p className="mt-1 text-xs text-slate-500">{a.description}</p>}
                  {a.resource_url && (
                    <a
                      href={a.resource_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block text-xs text-primary-600 hover:underline"
                    >
                      Open resource ↗
                    </a>
                  )}
                </div>
                <div>
                  {existingReport ? (
                    <Badge variant={existingReport.status === "reviewed" ? "success" : "warning"}>
                      {existingReport.status}
                      {existingReport.trainer_score != null &&
                        ` (${existingReport.trainer_score}/100)`}
                    </Badge>
                  ) : a.report_submission_enabled ? (
                    <Button size="sm" variant="outline" onClick={() => setSubmittingFor(a.id)}>
                      Submit report
                    </Button>
                  ) : (
                    <Badge variant="outline">no submission</Badge>
                  )}
                </div>
              </div>

              {/* Report submission form */}
              {submittingFor === a.id && (
                <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                  <Label htmlFor={`report-${a.id}`} required>
                    Your report
                  </Label>
                  <textarea
                    id={`report-${a.id}`}
                    rows={4}
                    className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                    value={reportText}
                    onChange={(e) => setReportText(e.target.value)}
                    placeholder="Write your report..."
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => submitMutation.mutate()}
                      loading={submitMutation.isPending}
                      disabled={!reportText}
                    >
                      Submit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setSubmittingFor(null);
                        setReportText("");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Show trainer feedback if reviewed */}
              {existingReport?.status === "reviewed" && existingReport.trainer_feedback && (
                <div className="mt-2 rounded-md bg-emerald-50 p-2 text-xs text-emerald-800">
                  <strong>Trainer feedback:</strong> {existingReport.trainer_feedback}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Assessments Panel — launch assessments at session/topic/lesson level
// ---------------------------------------------------------------------------

function AssessmentsPanel({ course, sessionId }: { course: TrainingCourse; sessionId: number }) {
  const sessionAssessments = course.assessments.filter((a) => a.session === sessionId);

  if (sessionAssessments.length === 0) return null;

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-sm">Assessments</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {sessionAssessments.map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between rounded-md border border-slate-100 p-3"
          >
            <div>
              <div className="text-sm font-medium text-slate-900">{a.title}</div>
              <div className="text-xs text-slate-500">
                {a.level.replace(/_/g, " ")}
                {a.is_scored && " · scored"}
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => window.open(`/assessment/${a.assessment}/session/new`, "_blank")}
            >
              Take assessment
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
