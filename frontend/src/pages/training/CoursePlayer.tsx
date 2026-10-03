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
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

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
  completionStatusLabel,
  completionStatusVariant,
  getProgressSummary,
  listAssignmentReports,
  listMyCourses,
  listProgress,
  startCourse,
  submitAssignmentReport,
  submitAssignmentReportFile,
  updateProgress,
  type InteractiveQuestion,
  type ProgressSummary,
  type SessionContent,
  type TopicSession,
  type TrainingCourse,
} from "@/api/training";
import { extractApiError } from "@/api/client";
import { startSession } from "@/api/assessment";
import { InteractiveVideoPlayer } from "./InteractiveVideoPlayer";
import { isHtml } from "./TextContentEditor";
import { RichText } from "@/components/ui/RichText";

// Flatten all content into a sequential list for navigation
interface FlatContent {
  lessonId: number;
  topicId: number;
  lessonTitle: string;
  topicTitle: string;
  sessionTitle: string;
  content: SessionContent;
  session: TopicSession;
}

export function CoursePlayer({
  course,
  onRegister,
}: {
  course: TrainingCourse;
  /** Opens the registration form (so "Learn" isn't a dead end). */
  onRegister?: () => void;
}) {
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
              lessonId: lesson.id,
              topicId: topic.id,
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
  // Report 8 #23: once the last content is completed, show the final
  // results instead of leaving "Mark as completed & Continue" on screen.
  const [finished, setFinished] = useState(false);
  // D7: resume from the last-accessed content once, when the progress
  // summary and course content are both loaded — the backend already
  // computes `last_content` (progress_summary's resume point); the player
  // just needs to jump there instead of always starting at index 0.
  const [hasResumed, setHasResumed] = useState(false);
  const [resumedFrom, setResumedFrom] = useState(false);
  useEffect(() => {
    // Decide once, on the first summary load. Waiting for a `last_content`
    // meant a fresh start resumed right after the first "Mark as completed",
    // yanking the student back to the item they had just finished.
    if (hasResumed || !progressSummary || flatContent.length === 0) return;
    const last = progressSummary.last_content;
    if (last?.content_type === "session_content") {
      const idx = flatContent.findIndex((item) => item.content.id === last.content_id);
      if (idx >= 0) {
        setCurrentIdx(idx);
        setResumedFrom(true);
      }
    }
    setHasResumed(true);
  }, [hasResumed, progressSummary, flatContent]);
  const current = flatContent[currentIdx];

  // Report 3 §5.1: content sequencing. When content_sequencing_enabled is on, the
  // candidate must complete each content in order before advancing.
  const contentSequencingEnabled = course.content_sequencing_enabled;
  const { data: progressRecords } = useQuery({
    queryKey: ["training", "progress-records", registration?.id],
    queryFn: () => listProgress(registration!.id),
    enabled: !!registration && contentSequencingEnabled,
  });
  // Set of completed session_content IDs (only relevant when enforcing).
  const completedContentIds = new Set(
    (progressRecords ?? [])
      .filter((p) => p.content_type === "session_content" && p.is_completed)
      .map((p) => p.content_id),
  );
  const currentCompleted = current ? completedContentIds.has(current.content.id) : false;

  // Report 8.1 #62: opening the course (paid, or free) is what starts it —
  // record the start date and move "not started" to "in progress" once.
  // Paying no longer does this, so the trainer's "Started" column and the
  // status reflect the learner, not the payment.
  const queryClient = useQueryClient();
  const startRequested = useRef(false);
  const canPlay =
    !!registration &&
    (parseFloat(course.price) === 0 || registration.payment_status === "paid") &&
    flatContent.length > 0;
  useEffect(() => {
    if (!registration || !canPlay || startRequested.current) return;
    if (registration.completion_status !== "not_started" && registration.started_at) return;
    startRequested.current = true;
    startCourse(registration.id)
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: ["training", "my-courses"] });
        void queryClient.invalidateQueries({
          queryKey: ["training", "progress-summary", registration.id],
        });
      })
      .catch(() => {});
  }, [registration, canPlay, queryClient]);
  // A content item is unlocked if sequencing is off, or it's the first
  // incomplete content, or it's already completed.
  const isUnlocked = (idx: number) => {
    if (!contentSequencingEnabled) return true;
    if (idx === 0) return true;
    // Unlocked if the previous content is completed
    const prev = flatContent[idx - 1];
    return completedContentIds.has(prev.content.id);
  };

  if (!registration) {
    return (
      <Alert variant="warning">
        <AlertDescription>
          {onRegister
            ? "You need to register for this course before you can start learning."
            : "Only learners registered for this course can open its content."}
          {onRegister && (
            <Button size="sm" className="ml-3" onClick={onRegister}>
              Register now
            </Button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  // For free courses (price=0), don't block on payment_status — the
  // backend auto-marks them as 'paid', but existing registrations from
  // before the fix may still have 'pending'. For paid courses, block
  // until payment is confirmed.
  const isFreeCourse = parseFloat(course.price) === 0;
  if (!isFreeCourse && registration.payment_status !== "paid") {
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

      {/* D7: resume-from-last-accessed banner */}
      {resumedFrom && current && (
        <Alert>
          <AlertDescription>
            Resuming from where you left off: <strong>{current.content.title}</strong>
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content Player */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Content area (2/3) */}
        <div className="lg:col-span-2">
          {finished ? (
            <CourseFinishedPanel
              course={course}
              summary={progressSummary}
              onReview={() => {
                setFinished(false);
                setCurrentIdx(0);
              }}
            />
          ) : (
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
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
                      setFinished(true);
                    }
                  }}
                />

                {/* Navigation */}
                <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}
                    disabled={currentIdx === 0}
                  >
                    ← Previous
                  </Button>
                  <span className="text-sm tabular-nums text-slate-500">
                    Content {currentIdx + 1} of {flatContent.length}
                  </span>
                  <Button
                    onClick={() => setCurrentIdx(Math.min(flatContent.length - 1, currentIdx + 1))}
                    disabled={
                      currentIdx === flatContent.length - 1 ||
                      (contentSequencingEnabled && !currentCompleted)
                    }
                    title={
                      contentSequencingEnabled && !currentCompleted
                        ? "Complete this content to unlock the next (sequential mode)"
                        : undefined
                    }
                  >
                    Next →
                  </Button>
                </div>
                {contentSequencingEnabled && !currentCompleted && (
                  <p className="mt-2 text-xs text-warning-600">
                    Sequential mode: mark this content as completed to unlock the next.
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Assignments for current session */}
          {current.session.assignments.length > 0 && (
            <AssignmentsPanel session={current.session} registrationId={registration.id} />
          )}

          {/* Report 8 #24: live sessions placed after this content */}
          {!finished && (
            <LiveSessionsAt
              sessions={course.live_sessions.filter(
                (ls) => ls.after_content === current.content.id,
              )}
              registrationId={registration.id}
            />
          )}

          {/* Assessments due at this point in the sequence (Doc 7 §2.4) */}
          {!finished && (
            <AssessmentsPanel
              assessments={assessmentsDueAt(course, flatContent, currentIdx)}
              summary={progressSummary}
            />
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
                {flatContent.map((item, idx) => {
                  const locked = contentSequencingEnabled && !isUnlocked(idx);
                  const completed = completedContentIds.has(item.content.id);
                  return (
                    <button
                      key={item.content.id}
                      onClick={() => !locked && setCurrentIdx(idx)}
                      disabled={locked}
                      className={`block w-full rounded-md px-3 py-2 text-left text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${
                        idx === currentIdx
                          ? "bg-primary-50 text-primary-900"
                          : locked
                            ? "cursor-not-allowed text-slate-300"
                            : "text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      <div className="flex items-center justify-between font-medium">
                        <span>{item.content.title}</span>
                        {completed && <span className="text-success-500">✓</span>}
                        {locked && <span title="Locked">🔒</span>}
                      </div>
                      <div className="text-slate-400">
                        {item.lessonTitle} → {item.sessionTitle}
                      </div>
                    </button>
                  );
                })}
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
                    <div key={s.id} className="rounded-lg border border-slate-200 p-2">
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
      void queryClient.invalidateQueries({
        queryKey: ["training", "progress-records", registrationId],
      });
    },
  });

  // Mark as completed + move to next
  const markComplete = () => {
    trackProgress.mutate(true);
    onComplete();
  };

  // D7: an uploaded media file takes priority over the URL/base64 field.
  const mediaSrc = content.media_file || content.content_url;

  if (content.content_format === "video" && mediaSrc) {
    return (
      <div className="space-y-3">
        <InteractiveVideoPlayer
          contentUrl={mediaSrc}
          questions={content.interactive_questions as InteractiveQuestion[]}
        />
        <Button onClick={markComplete} loading={trackProgress.isPending}>
          ✓ Mark as completed
        </Button>
      </div>
    );
  }

  if (content.content_format === "audio" && mediaSrc) {
    return (
      <div className="space-y-3">
        <InteractiveVideoPlayer
          kind="audio"
          contentUrl={mediaSrc}
          questions={content.interactive_questions as InteractiveQuestion[]}
          onEnded={markComplete}
        />
        <Button onClick={markComplete} loading={trackProgress.isPending}>
          ✓ Mark as completed
        </Button>
      </div>
    );
  }

  if (content.content_format === "text") {
    return (
      <div className="space-y-3">
        {/* Report 8 #16: keep the trainer's paragraphs and line breaks — a
            3000-word essay rendered as one unbroken paragraph. */}
        {isHtml(content.text_content) ? (
          // Formatted text from the editor (sanitised server-side).
          <RichText
            html={content.text_content}
            className="rounded-md border border-slate-100 bg-slate-50 p-4 leading-relaxed"
          />
        ) : (
          <div className="prose max-w-none whitespace-pre-line rounded-md border border-slate-100 bg-slate-50 p-4 text-sm leading-relaxed">
            {content.text_content || content.content_url || "No text content available."}
          </div>
        )}
        {/* D7: minimal media embedding — an uploaded media file attached to
            text content is shown inline alongside the text. */}
        {content.media_file && (
          <img
            src={content.media_file}
            alt={content.title}
            className="max-w-full rounded-md border border-slate-100"
          />
        )}
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
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Completion
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-slate-900">
              {pct}%
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-primary-600 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-400">
              {summary.completed_count}/{summary.total_count} items
            </div>
          </div>

          {/* Time spent */}
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Time Spent
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-slate-900">
              {hoursSpent}h {minsSpent}m
            </div>
          </div>

          {/* Time left (scheduled courses only) */}
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Time Left
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-slate-900">
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
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Status
            </div>
            <div className="mt-1">
              <Badge variant={completionStatusVariant(summary.completion_status)}>
                {completionStatusLabel(summary.completion_status)}
              </Badge>
            </div>
          </div>
        </div>

        {/* D7: score report — assessment + assignment-report scores rolled
            into the progress summary (SRS §6 "Score report"). */}
        {(summary.assessment_scores.length > 0 || summary.assignment_report_scores.length > 0) && (
          <div className="mt-4 border-t border-slate-200 pt-4">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Score Report
              </div>
              {summary.average_assessment_percentage != null && (
                <Badge variant="primary">
                  Avg. assessment score: {summary.average_assessment_percentage}%
                </Badge>
              )}
            </div>
            <div className="mt-2 space-y-1">
              {summary.assessment_scores.map((s) => (
                <div
                  key={`assessment-${s.course_assessment_id}`}
                  className="flex items-center justify-between text-xs text-slate-600"
                >
                  <span>{s.title}</span>
                  <span>
                    {s.status === "completed" ? (
                      <Badge variant="success">{s.percentage}%</Badge>
                    ) : (
                      <Badge variant="outline">not attempted</Badge>
                    )}
                  </span>
                </div>
              ))}
              {summary.assignment_report_scores.map((s) => (
                <div key={`report-${s.assignment_id}`} className="text-xs text-slate-600">
                  <div className="flex items-center justify-between gap-3">
                    <span>{s.assignment_title} (report)</span>
                    <span>
                      {s.trainer_score != null ? (
                        <Badge variant="success">{s.trainer_score}/10</Badge>
                      ) : (
                        <Badge variant="outline">{s.status}</Badge>
                      )}
                    </span>
                  </div>
                  {/* Report 8 #28: show the trainer's feedback to the trainee. */}
                  {s.trainer_feedback && (
                    <p className="mt-1 whitespace-pre-line rounded bg-slate-50 px-2 py-1 text-slate-700">
                      <span className="font-medium">Trainer feedback:</span> {s.trainer_feedback}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        {summary.requirements && summary.requirements.length > 0 && (
          <details className="mt-4 border-t border-slate-200 pt-3">
            <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
              Completion requirements ({summary.requirements.filter((r) => r.completed).length}/
              {summary.requirements.length})
            </summary>
            <p className="mt-1 text-xs text-slate-500">
              {summary.requirements_are_mandatory_params
                ? "Your trainer has marked these items as mandatory to complete the course."
                : "Complete every content item to complete the course."}
            </p>
            <ul className="mt-2 space-y-1">
              {summary.requirements.map((r) => (
                <li
                  key={`${r.content_type}-${r.content_id}`}
                  className="flex items-center gap-2 text-xs text-slate-700"
                >
                  <span className={r.completed ? "text-success-600" : "text-slate-400"}>
                    {r.completed ? "✓" : "○"}
                  </span>
                  {r.title}
                  <span className="text-slate-400">({r.content_type.replace(/_/g, " ")})</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Assignments Panel — shows assignments + report submission
// ---------------------------------------------------------------------------

export function AssignmentsPanel({
  session,
  registrationId,
  title = "Assignments",
}: {
  session: TopicSession;
  registrationId: number;
  /** Report 9 #80: the Assignments tab heads each panel with its session. */
  title?: string;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [submittingFor, setSubmittingFor] = useState<number | null>(null);
  const [reportText, setReportText] = useState("");
  const [reportFiles, setReportFiles] = useState<File[]>([]);

  const { data: existingReports } = useQuery({
    queryKey: ["training", "assignment-reports", registrationId],
    queryFn: () => listAssignmentReports(registrationId),
  });

  const submitMutation = useMutation({
    mutationFn: () => {
      // Report 3 §3.6 + E-X7: if files are attached, submit via multipart
      // upload (one or many files of mixed formats).
      if (reportFiles.length > 0) {
        return submitAssignmentReportFile(registrationId, {
          assignment: submittingFor!,
          report_text: reportText,
          file: reportFiles[0],
          files: reportFiles.slice(1),
        });
      }
      return submitAssignmentReport(registrationId, {
        assignment: submittingFor!,
        report_text: reportText,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["training", "assignment-reports", registrationId],
      });
      toast.success("Report submitted. The trainer will review it.");
      setSubmittingFor(null);
      setReportText("");
      setReportFiles([]);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {session.assignments.map((a) => {
          const existingReport = existingReports?.find((r) => r.assignment === a.id);
          return (
            <div key={a.id} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
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
                    <div className="text-right">
                      <Badge variant={existingReport.status === "reviewed" ? "success" : "warning"}>
                        {existingReport.status}
                        {existingReport.trainer_score != null &&
                          ` (${existingReport.trainer_score}/10)`}
                      </Badge>
                      {existingReport.trainer_feedback && (
                        <p className="mt-1 max-w-xs whitespace-pre-line text-left text-xs text-slate-600">
                          <span className="font-medium">Trainer feedback:</span>{" "}
                          {existingReport.trainer_feedback}
                        </p>
                      )}
                    </div>
                  ) : a.report_submission_enabled ? (
                    <Button size="sm" variant="outline" onClick={() => setSubmittingFor(a.id)}>
                      Submit report
                    </Button>
                  ) : (
                    <Badge variant="outline">no submission</Badge>
                  )}
                </div>
              </div>

              {/* Report 3 §3.3: deadline + mandatory indicators */}
              {a.report_submission_enabled && (
                <div className="mt-1 flex flex-wrap gap-2 text-xs">
                  {a.is_mandatory && <Badge variant="warning">Report mandatory</Badge>}
                  {a.submission_deadline && (
                    <span className="text-slate-500">
                      Deadline: {new Date(a.submission_deadline).toLocaleString()}
                      {new Date(a.submission_deadline) < new Date() &&
                        !existingReport?.late_submission_approved && (
                          <span className="ml-1 font-medium text-danger">
                            (passed — ask trainer to approve late submission)
                          </span>
                        )}
                    </span>
                  )}
                </div>
              )}

              {/* Report submission form */}
              {submittingFor === a.id && (
                <div className="mt-3 space-y-2 border-t border-slate-200 pt-3">
                  <Label htmlFor={`report-${a.id}`}>Your report (text)</Label>
                  <textarea
                    id={`report-${a.id}`}
                    rows={4}
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                    value={reportText}
                    onChange={(e) => setReportText(e.target.value)}
                    placeholder="Write your report..."
                  />
                  <Label htmlFor={`file-${a.id}`}>
                    Or upload files (PDF / PPT / Word — you can attach several)
                  </Label>
                  <input
                    id={`file-${a.id}`}
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.ppt,.pptx"
                    onChange={(e) => setReportFiles(Array.from(e.target.files ?? []))}
                    className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-700 hover:file:bg-primary-100"
                  />
                  {reportFiles.length > 0 && (
                    <p className="text-xs text-slate-500">
                      {reportFiles.length} file{reportFiles.length !== 1 ? "s" : ""} selected:{" "}
                      {reportFiles.map((f) => f.name).join(", ")}
                    </p>
                  )}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => submitMutation.mutate()}
                      loading={submitMutation.isPending}
                      disabled={!reportText && reportFiles.length === 0}
                    >
                      Submit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setSubmittingFor(null);
                        setReportText("");
                        setReportFiles([]);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Show trainer feedback if reviewed */}
              {existingReport?.status === "reviewed" && existingReport.trainer_feedback && (
                <div className="mt-2 rounded-md bg-success-50 p-2 text-xs text-success-800">
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

/**
 * Course assessments whose sequence point is the current content (Doc 7 §2.4
 * levels; Report 8 #18/#19). Session-level ones show with their session; end
 * of topic / lesson / course ones on the last content of that topic / lesson /
 * course. Before, only session-linked assessments were ever offered, so an
 * "end of topic" assessment could never be taken.
 */
function assessmentsDueAt(
  course: TrainingCourse,
  flat: FlatContent[],
  idx: number,
): TrainingCourse["assessments"] {
  const cur = flat[idx];
  if (!cur) return [];
  const next = flat[idx + 1];
  const lastOfTopic = !next || next.topicId !== cur.topicId;
  const lastOfLesson = !next || next.lessonId !== cur.lessonId;
  const lastOfCourse = !next;
  return course.assessments.filter((a) => {
    if (a.session != null) return a.session === cur.session.id;
    if (a.level === "end_of_topic" || (a.topic != null && a.lesson == null)) {
      return a.topic === cur.topicId && lastOfTopic;
    }
    if (a.level === "end_of_lesson" || a.lesson != null) {
      return a.lesson === cur.lessonId && lastOfLesson;
    }
    return lastOfCourse; // end of course / unplaced
  });
}

function AssessmentsPanel({
  assessments,
  summary,
}: {
  assessments: TrainingCourse["assessments"];
  summary?: ProgressSummary;
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const [starting, setStarting] = useState<number | null>(null);

  if (assessments.length === 0) return null;

  // Start or resume the candidate's session and open the real player. The old
  // button opened /assessment/<id>/session/new, a route that doesn't exist.
  const take = async (assessmentId: number) => {
    setStarting(assessmentId);
    try {
      const session = await startSession(assessmentId);
      navigate(`/assessments/sessions/${session.id}`);
    } catch (err) {
      toast.error(extractApiError(err));
    } finally {
      setStarting(null);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-sm">Assessments</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {assessments.map((a) => {
          const result = summary?.assessment_scores.find((s) => s.course_assessment_id === a.id);
          return (
            <div
              key={a.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 p-3"
            >
              <div>
                <div className="text-sm font-medium text-slate-900">{a.title}</div>
                <div className="text-xs text-slate-500">
                  {a.level.replace(/_/g, " ")}
                  {a.is_scored && " · scored"}
                </div>
              </div>
              {result?.status === "completed" && result.session_id ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate(`/assessments/sessions/${result.session_id}/results`)}
                >
                  View result{result.percentage != null ? ` (${result.percentage}%)` : ""}
                </Button>
              ) : (
                <Button
                  size="sm"
                  loading={starting === a.assessment}
                  onClick={() => void take(a.assessment)}
                >
                  Take assessment
                </Button>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

/** Report 8 #23: final results once every content item is completed. */
function CourseFinishedPanel({
  course,
  summary,
  onReview,
}: {
  course: TrainingCourse;
  summary?: ProgressSummary;
  onReview: () => void;
}) {
  const pending = course.assessments.filter((a) => {
    const r = summary?.assessment_scores.find((s) => s.course_assessment_id === a.id);
    return r?.status !== "completed";
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">🎉 Course completed</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          You have completed all the content of <strong>{course.title}</strong>.
        </p>
        {summary && (
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-slate-500">Completion</dt>
              <dd className="font-semibold">{summary.completion_percentage}%</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Items completed</dt>
              <dd className="font-semibold">
                {summary.completed_count} / {summary.total_count}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Time spent</dt>
              <dd className="font-semibold">
                {Math.floor(summary.total_time_spent_seconds / 3600)}h{" "}
                {Math.floor((summary.total_time_spent_seconds % 3600) / 60)}m
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Avg. assessment score</dt>
              <dd className="font-semibold">
                {summary.average_assessment_percentage != null
                  ? `${summary.average_assessment_percentage}%`
                  : "—"}
              </dd>
            </div>
          </dl>
        )}
        {summary && summary.assignment_report_scores.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Assignments
            </p>
            <ul className="space-y-1 text-sm">
              {summary.assignment_report_scores.map((r) => (
                <li key={r.assignment_id} className="flex justify-between">
                  <span>{r.assignment_title}</span>
                  <span className="text-slate-500">
                    {r.trainer_score != null ? `${r.trainer_score}/10` : r.status}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <AssessmentsPanel assessments={pending} summary={summary} />
        <Button variant="outline" onClick={onReview}>
          Review course content
        </Button>
      </CardContent>
    </Card>
  );
}

/** Report 8 #24: live sessions linked to a sequence point; joining records
 * attendance (Report 8 #10 — counts toward completion when mandatory). */
function LiveSessionsAt({
  sessions,
  registrationId,
}: {
  sessions: TrainingCourse["live_sessions"];
  registrationId: number;
}) {
  if (sessions.length === 0) return null;
  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-sm">Live session</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {sessions.map((ls) => (
          <div
            key={ls.id}
            className="flex items-center justify-between rounded-lg border border-slate-200 p-3"
          >
            <div>
              <div className="text-sm font-medium text-slate-900">{ls.title}</div>
              <div className="text-xs text-slate-500">
                {new Date(ls.scheduled_at).toLocaleString()} · {ls.duration_minutes} min ·{" "}
                {ls.mode === "online" ? "online" : ls.venue || "classroom"}
              </div>
            </div>
            {ls.mode === "online" && ls.meeting_url && !ls.join_locked ? (
              <a
                href={ls.meeting_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() =>
                  void updateProgress(registrationId, {
                    content_type: "live_session",
                    content_id: ls.id,
                    is_completed: true,
                  }).catch(() => {})
                }
              >
                <Button size="sm">Join ↗</Button>
              </a>
            ) : (
              <Badge variant="outline">{ls.status}</Badge>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
