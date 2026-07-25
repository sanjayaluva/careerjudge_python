/**
 * Session Player — fullscreen assessment delivery interface.
 *
 * Shows questions one at a time with navigation (prev/next),
 * bookmark, skip, and submit. Supports MCQ, FITB, Rating, Rank,
 * Forced-Choice question types. Flash/passage types show stimulus first.
 *
 * Route: /assessments/sessions/:sessionId
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Alert, AlertDescription, Button, Label, Modal, Spinner, useToast } from "@/components/ui";
import {
  type SessionQuestion,
  getSessionQuestions,
  retrieveSession,
  submitAnswer,
  submitSessionResult,
  suspendSession,
} from "@/api/assessment";
import { extractApiError } from "@/api/client";

export default function SessionPlayerPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const sid = Number(sessionId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Record<string, unknown>>>({});
  const [bookmarked, setBookmarked] = useState<Set<string>>(new Set());
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [questionTimeLeft, setQuestionTimeLeft] = useState<number | null>(null);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  // Tracks question IDs the candidate has already viewed (visited + navigated
  // away from). Used to lock flash/passage/image replay on revisit
  // (SRS feedback Common Issue 5).
  const [viewedQuestions, setViewedQuestions] = useState<Set<number>>(new Set());
  // Tracks question IDs where the timed presentation (flash/passage/image)
  // has finished. Used to gate Question Text 2 + answer options until the
  // presentation is over (SRS feedback Common Issue 4).
  const [presentationDone, setPresentationDone] = useState<Set<number>>(new Set());

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ["assessment-session", sid],
    queryFn: () => retrieveSession(sid),
    enabled: !Number.isNaN(sid),
  });

  // Initialize the timer once we know the assessment duration.
  // total_duration_seconds is exposed on the session serializer for the player.
  useEffect(() => {
    if (!session || session.status !== "active") return;
    if (timeLeft !== null) return; // already initialised
    if (session.total_duration_seconds && session.total_duration_seconds > 0) {
      // For an in-progress session we approximate remaining time from started_at.
      // (Server-side enforcement is the source of truth; this is purely UX.)
      const elapsed = Math.floor((Date.now() - new Date(session.started_at).getTime()) / 1000);
      const remaining = Math.max(0, session.total_duration_seconds - elapsed);
      setTimeLeft(remaining);
    }
  }, [session, timeLeft]);

  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft((t) => {
        if (t === null || t <= 1) {
          // Auto-submit on timeout
          clearInterval(timer);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft]);

  // Auto-submit when timer hits 0
  useEffect(() => {
    if (timeLeft === 0 && session?.status === "active") {
      submitMutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  const { data: rawQuestions, isLoading: questionsLoading } = useQuery({
    queryKey: ["assessment-session-questions", sid],
    queryFn: () => getSessionQuestions(sid),
    enabled: !Number.isNaN(sid),
  });

  // Apply random display order if the assessment requests it.
  // The shuffle is stable per session (seeded by session ID) so the candidate
  // sees the same order on refresh, but different from the authoring order.
  const questions = (() => {
    if (!rawQuestions) return undefined;
    if (session?.display_order === "RANDOM" && rawQuestions.length > 0) {
      // Simple shuffle — seeded by session ID for consistency across refreshes
      // (not cryptographically secure, but sufficient for display ordering)
      const shuffled = [...rawQuestions];
      let seed = sid;
      for (let i = shuffled.length - 1; i > 0; i--) {
        seed = (seed * 9301 + 49297) % 233280;
        const j = Math.floor((seed / 233280) * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      return shuffled;
    }
    return rawQuestions;
  })();

  const answerMutation = useMutation({
    mutationFn: (payload: {
      question_id: number;
      raw_answer?: Record<string, unknown>;
      bookmark?: boolean;
      sub_question_index?: number;
    }) => submitAnswer(sid, payload),
    onError: (err) => toast.error(extractApiError(err)),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitSessionResult(sid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessment-session", sid] });
      navigate(`/assessments/sessions/${sid}/results`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const suspendMutation = useMutation({
    mutationFn: () => suspendSession(sid),
    onSuccess: () => navigate("/assessments"),
    onError: (err) => toast.error(extractApiError(err)),
  });

  // Question-level timer: when timer_level='question', each question can
  // have its own duration_seconds. Reset the per-question timer when the
  // current question changes. Must be before early returns (hooks rule).
  const timerLevel = session?.timer_level ?? "assessment";
  useEffect(() => {
    if (timerLevel !== "question" || !questions || !questions[currentIndex]) {
      setQuestionTimeLeft(null);
      return;
    }
    setQuestionTimeLeft(null);
  }, [currentIndex, timerLevel, questions]);

  // Question-level timer countdown
  useEffect(() => {
    if (questionTimeLeft === null || questionTimeLeft <= 0) return;
    const qTimer = setInterval(() => {
      setQuestionTimeLeft((t) => {
        if (t === null || t <= 1) {
          clearInterval(qTimer);
          if (!isLast) {
            setCurrentIndex((i) => i + 1);
          } else {
            submitMutation.mutate();
          }
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(qTimer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionTimeLeft]);

  if (sessionLoading || questionsLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!session || !questions || questions.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Alert variant="error" className="max-w-md">
          <AlertDescription>No questions found for this session.</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (session.status !== "active") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-medium text-slate-900">Session is {session.status}</p>
          <Button className="mt-4" onClick={() => navigate("/assessments")}>
            Back to Assessments
          </Button>
        </div>
      </div>
    );
  }

  const q = questions[currentIndex];
  const qd = q.question_detail;
  const answerKey = `${q.question}_${q.sub_question_index}`;
  const isLast = currentIndex === questions.length - 1;
  const answeredCount = Object.keys(answers).length;
  const bookmarkedCount = bookmarked.size;

  // Determine whether this question has a timed presentation that should
  // gate Question Text 2 + answer options (SRS feedback Common Issue 4).
  // Gate is active when:
  //   - Question has flash items (flash types 1e, 1f, 2c, 2d)
  //   - Question has a passage with display_mode='timed' (1g)
  //   - Question is Image Display (1h) with display_duration_seconds set
  // AND the presentation has not yet finished for this question.
  const hasTimedPresentation =
    qd.flash_items.length > 0 ||
    (qd.passage_title != null && (qd.display_mode ?? "timed") === "timed") ||
    (qd.question_type === "MCQ_IMAGE_DISPLAY_MULTI" && qd.display_duration_seconds != null);
  const presentationActive =
    hasTimedPresentation && !presentationDone.has(qd.id) && !viewedQuestions.has(qd.id);

  // Navigation rule enforcement — per SRS 03_assessment_configuration.json:
  // FREE: free navigation (default, no restrictions)
  // PREV_SECTION: can only go back to previous section
  // NO_BACKWARD_SECTION: cannot go back to previous section
  // NO_BACKWARD_QUESTION: cannot go back to previous question
  const navRule = session.navigation_rule ?? "FREE";
  const canGoBack = () => {
    if (navRule === "NO_BACKWARD_QUESTION") return false;
    // For section-level rules, check if the previous question is in a
    // different section
    if (navRule === "NO_BACKWARD_SECTION" && currentIndex > 0) {
      const prevSection = questions[currentIndex - 1].section;
      const currentSection = q.section;
      if (prevSection !== currentSection) return false;
    }
    return true;
  };

  const handleNext = () => {
    // Save current answer before navigating
    const currentAnswer = answers[answerKey];
    if (currentAnswer) {
      answerMutation.mutate({
        question_id: q.question,
        raw_answer: currentAnswer,
        sub_question_index: q.sub_question_index,
      });
    }
    // Mark current question as viewed (locks replay on revisit)
    if (q?.question) {
      setViewedQuestions((prev) => new Set(prev).add(q.question));
    }
    if (!isLast) setCurrentIndex((i) => i + 1);
  };

  const handlePrev = () => {
    // Save current answer before navigating backwards
    const currentAnswer = answers[answerKey];
    if (currentAnswer) {
      answerMutation.mutate({
        question_id: q.question,
        raw_answer: currentAnswer,
        sub_question_index: q.sub_question_index,
      });
    }
    // Mark current question as viewed (locks replay on revisit)
    if (q?.question) {
      setViewedQuestions((prev) => new Set(prev).add(q.question));
    }
    if (currentIndex > 0) setCurrentIndex((i) => i - 1);
  };

  const handleBookmark = () => {
    const newBookmarked = new Set(bookmarked);
    if (newBookmarked.has(answerKey)) {
      newBookmarked.delete(answerKey);
    } else {
      newBookmarked.add(answerKey);
    }
    setBookmarked(newBookmarked);
    answerMutation.mutate({
      question_id: q.question,
      bookmark: true,
      sub_question_index: q.sub_question_index,
    });
  };

  const handleSubmit = () => {
    setShowSubmitConfirm(true);
  };

  const performSubmit = async () => {
    setShowSubmitConfirm(false);

    // Save ALL answers before submitting. The local `answers` state may have
    // unsaved changes — especially for the last question (the user answers
    // it then clicks Submit without clicking Next first). We save every
    // answer that has data, not just the current one, to catch any previous
    // save failures.
    const savePromises: Promise<unknown>[] = [];
    for (const [key, ans] of Object.entries(answers)) {
      const [qId, subIdx] = key.split("_");
      savePromises.push(
        submitAnswer(sid, {
          question_id: Number(qId),
          sub_question_index: Number(subIdx),
          raw_answer: ans,
        }).catch(() => {}),
      );
    }
    await Promise.all(savePromises);

    submitMutation.mutate();
  };

  // Group questions by section for the sidebar navigation tree.
  // Within each section, sub-questions from the same parent question are
  // grouped together (for multi-question types 1c-1h, 2c-2d).
  const sections = new Map<number | null, { questionIndex: number }[]>();
  questions.forEach((q, i) => {
    const sid = q.section;
    if (!sections.has(sid)) sections.set(sid, []);
    sections.get(sid)!.push({ questionIndex: i });
  });
  const sectionEntries = Array.from(sections.entries());

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* ─── Top bar ─── */}
      <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div>
          <h1 className="text-sm font-bold text-slate-900">{session.assessment_title}</h1>
          <p className="text-xs text-slate-500">
            Question {currentIndex + 1} of {questions.length} · Answered: {answeredCount} ·
            Bookmarked: {bookmarkedCount}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Assessment-level timer — bigger box per SRS feedback Common Issue 10 */}
          {timeLeft !== null && timeLeft > 0 && (
            <div
              className={`flex items-center gap-1 rounded-lg px-3 py-1.5 font-mono text-lg font-bold ${
                timeLeft < 60
                  ? "bg-danger-100 text-danger-700"
                  : timeLeft < 300
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-700"
              }`}
              title="Assessment time remaining"
            >
              <span className="text-xs">⏱</span>
              {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, "0")}
            </div>
          )}
          {/* Question-level timer (when timer_level='question') */}
          {questionTimeLeft !== null && questionTimeLeft > 0 && (
            <div
              className={`flex items-center gap-1 rounded-lg px-3 py-1.5 font-mono text-base font-bold ${
                questionTimeLeft < 10
                  ? "bg-danger-100 text-danger-700"
                  : "bg-amber-100 text-amber-700"
              }`}
              title="Question time remaining"
            >
              Q: {questionTimeLeft}s
            </div>
          )}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => suspendMutation.mutate()}>
              Suspend
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={submitMutation.isPending}
              onClick={handleSubmit}
            >
              Submit Assessment
            </Button>
          </div>
        </div>
      </div>

      {/* ─── Main area: sidebar + content ─── */}
      <div className="flex min-h-0 flex-1">
        {/* Left sidebar — section/question navigation tree + test summary */}
        <aside className="w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white">
          {/* Test Summary */}
          <div className="border-b border-slate-100 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Test Summary
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-md bg-slate-50 p-2">
                <span className="text-slate-500">Total</span>
                <p className="text-lg font-bold text-slate-900">{questions.length}</p>
              </div>
              <div className="rounded-md bg-green-50 p-2">
                <span className="text-green-600">Answered</span>
                <p className="text-lg font-bold text-green-700">{answeredCount}</p>
              </div>
              <div className="rounded-md bg-amber-50 p-2">
                <span className="text-amber-600">Bookmarked</span>
                <p className="text-lg font-bold text-amber-700">{bookmarkedCount}</p>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <span className="text-slate-500">Remaining</span>
                <p className="text-lg font-bold text-slate-700">
                  {questions.length - answeredCount}
                </p>
              </div>
            </div>
          </div>

          {/* Section / Question navigation tree */}
          <div className="p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Test Progress
            </p>
            {sectionEntries.map(([sid, items], secIdx) => (
              <div key={sid ?? "no-section"} className="mb-3">
                <p className="mb-1 text-xs font-medium text-slate-700">
                  {sid !== null ? `Section ${secIdx + 1}` : "Questions"}
                </p>
                <div className="flex flex-wrap gap-1">
                  {items.map(({ questionIndex: i }) => {
                    const aKey = `${questions[i].question}_${questions[i].sub_question_index}`;
                    const isAnswered = Boolean(answers[aKey]);
                    const isBookmarked = bookmarked.has(aKey);
                    const isCurrent = i === currentIndex;
                    return (
                      <button
                        key={i}
                        onClick={() => {
                          // Save current answer before jumping to a different question
                          const currentAnswer = answers[answerKey];
                          if (currentAnswer && i !== currentIndex) {
                            answerMutation.mutate({
                              question_id: q.question,
                              raw_answer: currentAnswer,
                            });
                          }
                          setCurrentIndex(i);
                        }}
                        title={`Question ${i + 1}`}
                        className={`h-7 w-7 rounded-md text-xs font-medium transition-colors ${
                          isCurrent
                            ? "bg-primary-600 text-white"
                            : isAnswered
                              ? "bg-green-100 text-green-700 hover:bg-green-200"
                              : isBookmarked
                                ? "bg-amber-100 text-amber-700 hover:bg-amber-200"
                                : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                        }`}
                      >
                        {i + 1}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Center content — question card */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-6 py-8">
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              {/* Bookmark button only — hide backend details (question type,
                  difficulty level, cognitive level) from the test taker
                  per SRS feedback Common Issue 9 */}
              <div className="mb-4 flex items-center justify-end">
                <button
                  onClick={handleBookmark}
                  className={`text-sm ${bookmarked.has(answerKey) ? "text-primary-600" : "text-slate-400 hover:text-slate-600"}`}
                >
                  {bookmarked.has(answerKey) ? "★ Bookmarked" : "☆ Bookmark"}
                </button>
              </div>

              {/* Question Text1 — ABOVE media (serves as instructions per
                  SRS feedback Common Issue 2).
                  Rendered as HTML to support rich-text formatting
                  (bold/italic/lists/subtitle) per SRS feedback Common Issue 2. */}
              {qd.question_text_1 && (
                <div
                  className="prose prose-sm mb-4 max-w-none text-base font-medium text-slate-900"
                  dangerouslySetInnerHTML={{ __html: qd.question_text_1 }}
                />
              )}

              {/* Flash items — interactive simulation.
                  key={qd.id} forces re-mount when the question changes,
                  fixing the flash-content-not-changing-between-questions bug
                  (SRS feedback Common Issue 8). */}
              {qd.flash_items.length > 0 && (
                <FlashSimulation
                  key={qd.id}
                  items={qd.flash_items}
                  intervalMs={qd.flash_interval_ms ?? 1000}
                  displayCount={qd.flash_display_count ?? qd.flash_items.length}
                  order={qd.flash_order}
                  replayMode={qd.replay_mode ?? "not_permitted"}
                  hasBeenViewed={viewedQuestions.has(qd.id)}
                  onPresentationEnd={() => setPresentationDone((prev) => new Set(prev).add(qd.id))}
                />
              )}

              {/* Passage — collapsible panel */}
              {qd.passage_title && (
                <PassageDisplay
                  key={`passage-${qd.id}`}
                  title={qd.passage_title}
                  body={qd.passage_body}
                  displayDurationSeconds={qd.display_duration_seconds ?? null}
                  displayMode={qd.display_mode ?? "timed"}
                  replayMode={qd.replay_mode ?? "not_permitted"}
                  hasBeenViewed={viewedQuestions.has(qd.id)}
                  onPresentationEnd={() => setPresentationDone((prev) => new Set(prev).add(qd.id))}
                />
              )}

              {/* Question image — larger per SRS feedback Common Issue 6.
                  For Image Display (1h) questions with a display_duration,
                  render the timed play button variant (SRS feedback §8 Issue 1+3). */}
              {qd.image &&
              qd.question_type === "MCQ_IMAGE_DISPLAY_MULTI" &&
              qd.display_duration_seconds ? (
                <ImageDisplayTimed
                  key={`img-${qd.id}`}
                  imageUrl={qd.image}
                  durationSeconds={qd.display_duration_seconds}
                  replayMode={qd.replay_mode ?? "not_permitted"}
                  hasBeenViewed={viewedQuestions.has(qd.id)}
                  onPresentationEnd={() => setPresentationDone((prev) => new Set(prev).add(qd.id))}
                />
              ) : qd.image ? (
                <img
                  src={qd.image}
                  alt="Question"
                  className="mb-4 max-h-[500px] w-full rounded-md border border-slate-200 object-contain"
                />
              ) : null}

              {/* Audio player (for MCQ_AUDIO_MULTI 1c).
                  Respects replay_mode: if 'not_permitted', audio can only be
                  played once. On revisit (Previous button), audio is locked.
                  SRS feedback §3 Issue 2 + Recommendation 2. */}
              {qd.media_files
                .filter((m) => m.media_type === "audio")
                .map((media) => (
                  <AudioPlayerControlled
                    key={`audio-${media.id}`}
                    fileUrl={media.file_url}
                    replayMode={qd.replay_mode ?? "not_permitted"}
                    hasBeenViewed={viewedQuestions.has(qd.id)}
                    onPresentationEnd={() =>
                      setPresentationDone((prev) => new Set(prev).add(qd.id))
                    }
                  />
                ))}

              {/* Video player (for MCQ_VIDEO_MULTI 1d).
                  Same replay controls as audio. */}
              {qd.media_files
                .filter((m) => m.media_type === "video")
                .map((media) => (
                  <VideoPlayerControlled
                    key={`video-${media.id}`}
                    fileUrl={media.file_url}
                    replayMode={qd.replay_mode ?? "not_permitted"}
                    hasBeenViewed={viewedQuestions.has(qd.id)}
                    onPresentationEnd={() =>
                      setPresentationDone((prev) => new Set(prev).add(qd.id))
                    }
                  />
                ))}

              {/* Question Text2 — BELOW media (the actual question based on
                  the audio/video/passage/image per SRS feedback Common Issue 2).
                  Rendered as HTML to support rich-text formatting.
                  GATED: hidden until the timed presentation is over
                  (SRS feedback Common Issue 4). */}
              {qd.question_text_2 && !presentationActive && (
                <div
                  className="prose prose-sm mb-4 mt-4 max-w-none text-sm text-slate-600"
                  dangerouslySetInnerHTML={{ __html: qd.question_text_2 }}
                />
              )}
              {qd.question_text_2 && presentationActive && (
                <div className="mb-4 mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-center">
                  <p className="text-sm text-amber-700">
                    The question and answer options will appear after the presentation is over.
                  </p>
                </div>
              )}

              {/* Answer input area — by question type.
                  GATED: hidden until the timed presentation is over
                  (SRS feedback Common Issue 4). */}
              {presentationActive ? (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-6 text-center">
                  <p className="text-sm text-slate-500">
                    Answer options will be available after the presentation ends.
                  </p>
                </div>
              ) : (
                <AnswerInput
                  question={q}
                  currentAnswer={answers[answerKey]}
                  onChange={(ans) => setAnswers({ ...answers, [answerKey]: ans })}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Footer — navigation buttons ─── */}
      <div className="flex shrink-0 items-center justify-between border-t border-slate-200 bg-white px-6 py-3">
        <Button
          variant="outline"
          onClick={handlePrev}
          disabled={currentIndex === 0 || !canGoBack()}
          title={
            !canGoBack() ? "Backward navigation is not allowed for this assessment" : undefined
          }
        >
          ← Previous
        </Button>
        <p className="text-xs text-slate-400">
          {currentIndex + 1} / {questions.length}
        </p>
        {isLast ? (
          <Button onClick={handleSubmit} loading={submitMutation.isPending}>
            Submit Assessment
          </Button>
        ) : (
          <Button onClick={handleNext}>Next →</Button>
        )}
      </div>

      {/* Submit confirmation modal — replaces the blocking confirm() dialog */}
      <Modal
        open={showSubmitConfirm}
        onClose={() => setShowSubmitConfirm(false)}
        title="Submit Assessment?"
        size="sm"
      >
        <p className="text-sm text-slate-700">
          You have answered <strong>{answeredCount}</strong> of <strong>{questions.length}</strong>{" "}
          questions.
          {answeredCount < questions.length && (
            <span className="mt-2 block text-amber-600">
              ⚠ {questions.length - answeredCount} question(s) are unanswered and will score 0. Are
              you sure you want to submit?
            </span>
          )}
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setShowSubmitConfirm(false)}>
            Cancel
          </Button>
          <Button variant="danger" loading={submitMutation.isPending} onClick={performSubmit}>
            Submit Assessment
          </Button>
        </div>
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Answer Input — renders the correct input based on question type
// ---------------------------------------------------------------------------

function AnswerInput({
  question,
  currentAnswer,
  onChange,
}: {
  question: SessionQuestion;
  currentAnswer: Record<string, unknown> | undefined;
  onChange: (answer: Record<string, unknown>) => void;
}) {
  const qd = question.question_detail;
  const qType = qd.question_type;
  const [selectedA, setSelectedA] = useState<number | null>(null);

  // MCQ types — radio or checkbox
  if (qType.startsWith("MCQ_")) {
    // Filter options to only those belonging to the current sub-question
    // (SRS feedback C-CFG-1 — multi-sub-question pooling).
    const subQIdx = question.sub_question_index;
    const subOptions = qd.options.filter((o) => (o.sub_question_index ?? 0) === subQIdx);
    const isMulti = subOptions.filter((o) => o.is_correct).length > 1;
    const selectedIds: number[] = (currentAnswer?.selected_option_ids as number[]) || [];

    const handleSelect = (optId: number) => {
      if (isMulti) {
        const newIds = selectedIds.includes(optId)
          ? selectedIds.filter((id) => id !== optId)
          : [...selectedIds, optId];
        onChange({ selected_option_ids: newIds });
      } else {
        onChange({ selected_option_ids: [optId] });
      }
    };

    // Multi-column layout per SRS feedback Common Issue 7
    const layoutCols =
      qd.option_layout === "2"
        ? "grid-cols-2"
        : qd.option_layout === "3"
          ? "grid-cols-3"
          : "grid-cols-1";

    return (
      <div className={`grid ${layoutCols} gap-2`}>
        {subOptions
          .filter((o) => o.option_type === "TEXT" || o.option_type === "IMAGE")
          .map((opt) => (
            <label
              key={opt.id}
              className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors ${
                selectedIds.includes(opt.id)
                  ? "border-primary-500 bg-primary-50"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <input
                type={isMulti ? "checkbox" : "radio"}
                name={`q-${question.id}`}
                checked={selectedIds.includes(opt.id)}
                onChange={() => handleSelect(opt.id)}
                className="h-4 w-4 shrink-0"
              />
              {opt.image_file && (
                <img src={opt.image_file} alt="" className="h-12 w-12 rounded object-cover" />
              )}
              {/* Hide '(image)' text for image-only options per SRS feedback Issue 2 (1b) */}
              {opt.text_value && <span>{opt.text_value}</span>}
            </label>
          ))}
      </div>
    );
  }

  // FITB types — text inputs
  // Per SRS feedback Issue 6: do NOT show "Field N" labels (unnecessary detail).
  // Per SRS feedback Issue 11: For FITB Flash Image/Word, allow candidate to add
  // up to N answer fields where N = number of flash items.
  if (qType.startsWith("FITB_")) {
    const answers: string[] = (currentAnswer?.answers as string[]) || [];
    const isFlashFitb = qType === "FITB_IMAGE_FLASH_MULTI" || qType === "FITB_WORD_FLASH_MULTI";
    const fields = qd.options.filter((o) => o.option_type === "TEXT");
    const maxFields = isFlashFitb
      ? Math.max(fields.length, qd.flash_items?.length || 0)
      : fields.length;
    const visibleFields = isFlashFitb ? Math.max(answers.length, fields.length, 1) : fields.length;

    return (
      <div className="space-y-2">
        {Array.from({ length: isFlashFitb ? visibleFields : fields.length }).map((_, i) => (
          <input
            key={i}
            type="text"
            value={answers[i] || ""}
            onChange={(e) => {
              const newAnswers = [...answers];
              newAnswers[i] = e.target.value;
              onChange({ answers: newAnswers });
            }}
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            placeholder="Type your answer..."
          />
        ))}
        {isFlashFitb && visibleFields < maxFields && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onChange({ answers: [...answers, ""] })}
          >
            + Add answer field ({visibleFields} / {maxFields})
          </Button>
        )}
        {isFlashFitb && (
          <p className="text-xs text-slate-500">
            Enter each item you remember from the flash presentation. Each correct answer gets +1
            point (any order).
          </p>
        )}
      </div>
    );
  }

  // Rating — scale circles
  if (qType === "STANDARD_RATING_SCALE") {
    const rating: number = (currentAnswer?.rating as number) || 0;
    const points = qd.rating_scale_points || 5;

    return (
      <div className="flex items-center gap-3">
        {[...Array(points)].map((_, p) => (
          <button
            key={p}
            type="button"
            onClick={() => onChange({ rating: p + 1 })}
            className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-medium ${
              rating === p + 1
                ? "border-primary-600 bg-primary-100 text-primary-700"
                : "border-slate-300 text-slate-500 hover:border-primary-300"
            }`}
          >
            {p + 1}
          </button>
        ))}
      </div>
    );
  }

  // Rank — draggable list (simplified: select order)
  if (qType === "RANK_SIMPLE") {
    const ranking: number[] = (currentAnswer?.ranking as number[]) || [];
    const rankOptions = qd.options.filter((o) => o.option_type === "RANK");

    const toggleRank = (optId: number) => {
      if (ranking.includes(optId)) {
        onChange({ ranking: ranking.filter((id) => id !== optId) });
      } else {
        onChange({ ranking: [...ranking, optId] });
      }
    };

    return (
      <div className="space-y-2">
        <p className="text-xs text-slate-500">
          Click items in order of preference (1 = most preferred):
        </p>
        {rankOptions.map((opt) => {
          const rank = ranking.indexOf(opt.id) + 1;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => toggleRank(opt.id)}
              className={`flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                rank > 0 ? "border-primary-500 bg-primary-50" : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-xs font-medium">
                {rank > 0 ? rank : "?"}
              </span>
              <span>{opt.text_value}</span>
            </button>
          );
        })}
        {ranking.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => onChange({ ranking: [] })}
          >
            Clear ranking
          </Button>
        )}
      </div>
    );
  }

  // Rank-then-Rate (6b) — rank items first, then rate each
  if (qType === "RANK_THEN_RATE") {
    const ranking: number[] = (currentAnswer?.ranking as number[]) || [];
    const ratings: Record<string, number> =
      (currentAnswer?.ratings as Record<string, number>) || {};
    const rankOptions = qd.options.filter((o) => o.option_type === "RANK");
    const points = qd.rating_scale_points || 5;

    const toggleRank = (optId: number) => {
      if (ranking.includes(optId)) {
        const newRanking = ranking.filter((id) => id !== optId);
        const newRatings = { ...ratings };
        delete newRatings[String(optId)];
        onChange({ ranking: newRanking, ratings: newRatings });
      } else {
        onChange({ ranking: [...ranking, optId], ratings });
      }
    };

    const setRating = (optId: number, rating: number) => {
      onChange({ ranking, ratings: { ...ratings, [String(optId)]: rating } });
    };

    const allRanked = ranking.length === rankOptions.length;

    return (
      <div className="space-y-4">
        {/* Step 1: Rank items */}
        <div>
          <p className="mb-2 text-xs font-medium text-slate-500">
            Step 1: Click items in order of preference (1 = most preferred):
          </p>
          <div className="space-y-2">
            {rankOptions.map((opt) => {
              const rank = ranking.indexOf(opt.id) + 1;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => toggleRank(opt.id)}
                  className={`flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                    rank > 0
                      ? "border-primary-500 bg-primary-50"
                      : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-xs font-medium">
                    {rank > 0 ? rank : "?"}
                  </span>
                  <span>{opt.text_value}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Step 2: Rate each ranked item */}
        {allRanked && (
          <div className="border-t border-slate-200 pt-4">
            <p className="mb-3 text-xs font-medium text-slate-500">
              Step 2: Rate each item (1 = lowest, {points} = highest):
            </p>
            <div className="space-y-3">
              {ranking.map((optId, rankIdx) => {
                const opt = rankOptions.find((o) => o.id === optId);
                if (!opt) return null;
                const rating = ratings[String(optId)] || 0;
                return (
                  <div key={optId} className="rounded-md border border-slate-200 p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-600 text-xs font-medium text-white">
                        {rankIdx + 1}
                      </span>
                      <span className="text-sm font-medium text-slate-900">{opt.text_value}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {[...Array(points)].map((_, p) => (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setRating(optId, p + 1)}
                          className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium ${
                            rating === p + 1
                              ? "border-primary-600 bg-primary-100 text-primary-700"
                              : "border-slate-300 text-slate-500 hover:border-primary-300"
                          }`}
                        >
                          {p + 1}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {!allRanked && ranking.length > 0 && (
          <p className="text-xs text-amber-600">
            ⚠ Rank all {rankOptions.length} items to proceed to rating. ({ranking.length}/
            {rankOptions.length} ranked)
          </p>
        )}
      </div>
    );
  }

  // Forced Choice — select one of two
  if (qType.startsWith("FORCED_CHOICE_")) {
    const selectedId: number | undefined = currentAnswer?.selected_option_id as number;
    const fcOptions = qd.options.filter((o) => o.option_type === "FORCED_CHOICE");
    const needsRating = qType === "FORCED_CHOICE_TWO_LEVEL";
    const rating: number = (currentAnswer?.rating as number) || 0;
    const points = qd.rating_scale_points || 5;

    return (
      <div className="space-y-4">
        <div className="space-y-2">
          {fcOptions.map((opt) => (
            <label
              key={opt.id}
              className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                selectedId === opt.id
                  ? "border-primary-500 bg-primary-50"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <input
                type="radio"
                name={`fc-${question.id}`}
                checked={selectedId === opt.id}
                onChange={() =>
                  onChange({ selected_option_id: opt.id, ...(needsRating ? { rating } : {}) })
                }
                className="h-4 w-4"
              />
              <span>{opt.text_value}</span>
            </label>
          ))}
        </div>
        {needsRating && selectedId && (
          <div>
            <Label className="text-xs text-slate-500">Rate your choice:</Label>
            <div className="mt-2 flex items-center gap-2">
              {[...Array(points)].map((_, p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => onChange({ selected_option_id: selectedId, rating: p + 1 })}
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium ${
                    rating === p + 1
                      ? "border-primary-600 bg-primary-100 text-primary-700"
                      : "border-slate-300 text-slate-500"
                  }`}
                >
                  {p + 1}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Hotspot — click on image to select answer
  if (qType.startsWith("HOTSPOT_")) {
    const clicks: { x: number; y: number }[] =
      (currentAnswer?.clicks as { x: number; y: number }[]) || [];
    const isMulti = qType === "HOTSPOT_MULTI";

    const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
      const img = e.currentTarget;
      const rect = img.getBoundingClientRect();
      const x = Math.round(e.clientX - rect.left);
      const y = Math.round(e.clientY - rect.top);
      // Scale to natural dimensions (shapes are stored in natural coords)
      const scaleX = img.naturalWidth / rect.width;
      const scaleY = img.naturalHeight / rect.height;
      const natX = Math.round(x * scaleX);
      const natY = Math.round(y * scaleY);

      if (isMulti) {
        onChange({ clicks: [...clicks, { x: natX, y: natY }] });
      } else {
        // Single answer: only keep latest click
        onChange({ clicks: [{ x: natX, y: natY }] });
      }
    };

    return (
      <div>
        {qd.image ? (
          <div>
            <div className="relative inline-block" style={{ maxWidth: 500 }}>
              <img
                src={qd.image}
                alt="Hotspot"
                onClick={handleImageClick}
                className="w-full cursor-crosshair rounded-md border border-slate-300"
                style={{ userSelect: "none", pointerEvents: "auto" }}
              />
              {/* Show click markers + (if hotspot_visibility='visible') the
                  hotspot area outlines (SRS feedback §15 Recommendation). */}
              <svg
                className="pointer-events-none absolute left-0 top-0"
                width="100%"
                height="100%"
                viewBox={`0 0 ${qd.image_width || 400} ${qd.image_height || 300}`}
                preserveAspectRatio="none"
              >
                {/* Hotspot area outlines — only shown when visibility='visible' */}
                {qd.hotspot_visibility === "visible" &&
                  qd.hotspot_areas.map((area) => {
                    const stroke = area.is_correct ? "#22c55e" : "#ef4444";
                    if (area.shape_type === "RECTANGLE") {
                      return (
                        <rect
                          key={`area-${area.id}`}
                          x={area.x}
                          y={area.y}
                          width={area.width_px}
                          height={area.height_px}
                          fill={area.is_correct ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"}
                          stroke={stroke}
                          strokeWidth="2"
                          strokeDasharray="4 2"
                        />
                      );
                    }
                    if (area.shape_type === "CIRCLE" && area.radius) {
                      return (
                        <circle
                          key={`area-${area.id}`}
                          cx={area.x}
                          cy={area.y}
                          r={area.radius}
                          fill={area.is_correct ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"}
                          stroke={stroke}
                          strokeWidth="2"
                          strokeDasharray="4 2"
                        />
                      );
                    }
                    if (area.shape_type === "POLYGON" && area.points && area.points.length > 1) {
                      const pts = area.points.map((p) => `${p.x},${p.y}`).join(" ");
                      return (
                        <polygon
                          key={`area-${area.id}`}
                          points={pts}
                          fill={area.is_correct ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"}
                          stroke={stroke}
                          strokeWidth="2"
                          strokeDasharray="4 2"
                        />
                      );
                    }
                    return null;
                  })}
                {clicks.map((c, i) => (
                  <g key={i}>
                    <circle
                      cx={c.x}
                      cy={c.y}
                      r={8}
                      fill="rgba(59,130,246,0.5)"
                      stroke="#3b82f6"
                      strokeWidth="2"
                    />
                    <text x={c.x + 4} y={c.y - 12} fill="#3b82f6" fontSize="14" fontWeight="bold">
                      {i + 1}
                    </text>
                  </g>
                ))}
              </svg>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {isMulti
                ? "Click on the image to mark your answers. Multiple clicks allowed."
                : "Click on the image to select your answer. Only your latest click counts."}
            </p>
            {clicks.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => onChange({ clicks: [] })}
              >
                Clear clicks
              </Button>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No image available for this question.</p>
        )}
      </div>
    );
  }

  // Match — two columns, select pairs
  if (qType === "MATCH_FOLLOWING") {
    const pairs: { a_id: number; b_id: number }[] =
      (currentAnswer?.pairs as { a_id: number; b_id: number }[]) || [];
    const groupA = qd.options.filter((o) => o.option_type === "MATCH_A");
    const groupB = qd.options.filter((o) => o.option_type === "MATCH_B");
    const dummyB = qd.options.filter((o) => o.option_type === "MATCH_DUMMY");

    // Combine real Group B + dummy options, then shuffle deterministically
    // per question (so refreshes don't reshuffle). Use question id as seed.
    const allGroupB = [...groupB, ...dummyB];
    const seed = qd.id || 0;
    const shuffledGroupB = [...allGroupB].sort((a, b) => {
      // Simple deterministic pseudo-random based on option id + question seed
      const ha = ((a.id * 9301 + seed * 49297) % 233280) / 233280;
      const hb = ((b.id * 9301 + seed * 49297) % 233280) / 233280;
      return ha - hb;
    });

    const handleMatch = (bId: number) => {
      if (selectedA === null) return;
      // Remove any existing pair with this a_id or b_id
      const filtered = pairs.filter((p) => p.a_id !== selectedA && p.b_id !== bId);
      onChange({ pairs: [...filtered, { a_id: selectedA, b_id: bId }] });
      setSelectedA(null);
    };

    const getMatchedB = (aId: number) => pairs.find((p) => p.a_id === aId)?.b_id;

    return (
      <div>
        <p className="mb-3 text-xs text-slate-500">
          Click an item from Group A, then click the matching item from Group B.
          {dummyB.length > 0 && (
            <span className="ml-1 italic text-amber-600">
              (Some Group B items are dummy — they don't match any Group A item.)
            </span>
          )}
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Group A</p>
            {groupA.map((opt) => {
              const matchedB = getMatchedB(opt.id);
              const matchedBOpt = shuffledGroupB.find((b) => b.id === matchedB);
              const isSelected = selectedA === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setSelectedA(isSelected ? null : opt.id)}
                  className={`mb-1 w-full rounded-md border px-3 py-2 text-left text-sm ${
                    isSelected
                      ? "border-primary-500 bg-primary-50"
                      : matchedBOpt
                        ? "border-green-300 bg-green-50"
                        : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {opt.text_value}
                  {matchedBOpt && (
                    <span className="ml-2 text-xs text-green-600">→ {matchedBOpt.text_value}</span>
                  )}
                </button>
              );
            })}
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-slate-500">
              Group B (shuffled)
            </p>
            {shuffledGroupB.map((opt) => {
              const isMatched = pairs.some((p) => p.b_id === opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => handleMatch(opt.id)}
                  disabled={selectedA === null}
                  className={`mb-1 w-full rounded-md border px-3 py-2 text-left text-sm ${
                    isMatched
                      ? "border-green-300 bg-green-50"
                      : selectedA !== null
                        ? "cursor-pointer border-slate-200 hover:bg-slate-50"
                        : "cursor-not-allowed border-slate-200 opacity-50"
                  }`}
                >
                  {opt.text_value}
                </button>
              );
            })}
          </div>
        </div>
        {pairs.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => onChange({ pairs: [] })}
          >
            Clear all pairs
          </Button>
        )}
      </div>
    );
  }

  // Grid — checkbox grid with numbered buttons (SRS feedback Issue 14)
  // Hides row/column names (they're backend metadata, not for the candidate).
  // Uses numbered-button grid style per SRS recommendation.
  if (qType === "GRID_LIST_SELECTION") {
    const selectedCells: { r: number; c: number }[] =
      (currentAnswer?.selected_cells as { r: number; c: number }[]) || [];
    const rows = qd.grid_rows || 3;
    const cols = qd.grid_cols || 3;

    const toggleCell = (r: number, c: number) => {
      const exists = selectedCells.some((cell) => cell.r === r && cell.c === c);
      if (exists) {
        onChange({
          selected_cells: selectedCells.filter((cell) => !(cell.r === r && cell.c === c)),
        });
      } else {
        onChange({ selected_cells: [...selectedCells, { r, c }] });
      }
    };

    // Get cell content from DRAG_POOL options
    const dragPoolOptions = qd.options.filter((o) => o.option_type === "DRAG_POOL");

    return (
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Click on a numbered button to view its content. Tick the checkbox to mark it as correct.
            Each correct cell = +1, each incorrect = −1, minimum 0.
          </p>
          <ViewAllGridItemsButton dragPoolOptions={dragPoolOptions} />
        </div>
        <table className="w-full text-sm">
          <tbody>
            {Array.from({ length: rows }).map((_, r) => (
              <tr key={r}>
                {Array.from({ length: cols }).map((_, c) => {
                  const cellIndex = r * cols + c;
                  const cellOpt = dragPoolOptions[cellIndex];
                  const selected = selectedCells.some((cell) => cell.r === r && cell.c === c);
                  return (
                    <GridCell
                      key={c}
                      cellIndex={cellIndex}
                      cellOpt={cellOpt}
                      selected={selected}
                      onToggle={() => toggleCell(r, c)}
                    />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <p className="text-sm text-slate-500">
      Answer input for this question type ({qd.question_type_label}) is not yet implemented.
    </p>
  );
}

// ---------------------------------------------------------------------------
// FlashSimulation — plays flash items one at a time at the configured interval.
// Respects flash_order (SEQUENCE = saved order, RANDOM = shuffled).
// Candidate can replay the sequence on demand.
// ---------------------------------------------------------------------------

interface FlashItemLike {
  id: number;
  item_type: string;
  text_value: string;
  image_file: string | null;
  order: number;
  is_in_display_pool: boolean;
}

function FlashSimulation({
  items,
  intervalMs,
  displayCount,
  order,
  replayMode = "not_permitted",
  hasBeenViewed = false,
  onPresentationEnd,
}: {
  items: FlashItemLike[];
  intervalMs: number;
  displayCount: number;
  order: string;
  replayMode?: "permitted" | "not_permitted";
  hasBeenViewed?: boolean;
  onPresentationEnd?: () => void;
}) {
  // Use only items flagged for the display pool (default to all if none flagged)
  const pool = items.filter((i) => i.is_in_display_pool);
  const sourceItems = pool.length > 0 ? pool : items;

  const [playing, setPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);
  const [playedOnce, setPlayedOnce] = useState(false);

  // Build the sequence once on mount (or when question changes)
  const [sequence] = useState<FlashItemLike[]>(() => {
    const sorted = [...sourceItems].sort((a, b) => a.order - b.order);
    const trimmed = sorted.slice(0, displayCount);
    if (order === "RANDOM") {
      // Fisher-Yates shuffle
      for (let i = trimmed.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [trimmed[i], trimmed[j]] = [trimmed[j], trimmed[i]];
      }
    }
    return trimmed;
  });

  // If the question has already been viewed (Previous button) and replay
  // is not permitted, lock the player. (SRS feedback C-FE-5 + 1e-3)
  const replayLocked = hasBeenViewed && replayMode === "not_permitted" && !playing;

  const play = () => {
    if (sequence.length === 0 || replayLocked) return;
    setPlaying(true);
    setCurrentIndex(0);

    sequence.forEach((_, i) => {
      setTimeout(
        () => {
          if (i + 1 < sequence.length) {
            setCurrentIndex(i + 1);
          } else {
            // End of sequence
            setTimeout(() => {
              setPlaying(false);
              setCurrentIndex(null);
              setPlayedOnce(true);
              // Notify parent that the presentation has ended
              // (used to un-gate Question Text 2 + answer options per
              // SRS feedback Common Issue 4).
              if (onPresentationEnd) onPresentationEnd();
            }, intervalMs);
          }
        },
        intervalMs * (i + 1),
      );
    });
  };

  // Hide flash specifications from candidate (SRS feedback §11 Issue 2)
  // Show only status messages, not technical details like '1000ms each'.

  return (
    <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3">
      {/* Big centred Play button — only visible before play starts or after
          replay is permitted (SRS feedback §11 Issue 3) */}
      {!playing && currentIndex === null && !replayLocked && (
        <div className="flex h-40 items-center justify-center rounded-md border border-amber-200 bg-white">
          <button
            type="button"
            onClick={play}
            disabled={playedOnce && replayMode === "not_permitted"}
            className={`flex h-16 w-16 items-center justify-center rounded-full text-2xl font-bold shadow-md transition-colors ${
              playedOnce && replayMode === "not_permitted"
                ? "cursor-not-allowed bg-slate-200 text-slate-400"
                : "bg-amber-500 text-white hover:bg-amber-600"
            }`}
            aria-label="Play flash sequence"
          >
            ▶
          </button>
        </div>
      )}

      {/* Flashing area */}
      {playing && currentIndex !== null && sequence[currentIndex] && (
        <div className="flex h-48 items-center justify-center rounded-md border border-amber-200 bg-white">
          <div className="text-center">
            {sequence[currentIndex].item_type === "IMAGE" && sequence[currentIndex].image_file ? (
              <img
                src={sequence[currentIndex].image_file!}
                alt=""
                className="mx-auto max-h-44 max-w-full object-contain"
              />
            ) : (
              <span className="text-3xl font-bold text-slate-900">
                {sequence[currentIndex].text_value}
              </span>
            )}
            <p className="mt-1 text-xs text-slate-400">
              {currentIndex + 1} / {sequence.length}
            </p>
          </div>
        </div>
      )}

      {/* Replay-permitted case: small replay button after play ends */}
      {!playing && currentIndex === null && playedOnce && !replayLocked && (
        <div className="mt-2 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={play}
            disabled={replayMode === "not_permitted"}
            className="h-8 px-3 text-xs"
          >
            ↻ Replay
          </Button>
        </div>
      )}

      {/* Replay-locked case (Previous button + not_permitted) */}
      {replayLocked && (
        <div className="flex h-40 items-center justify-center rounded-md border border-amber-200 bg-white">
          <p className="text-sm text-slate-500">
            Flash presentation already viewed. Replay is not permitted for this question.
          </p>
        </div>
      )}

      {/* Pre-play hint */}
      {!playing && currentIndex === null && !playedOnce && !replayLocked && (
        <p className="mt-2 text-center text-xs text-slate-500">
          Click the play button to begin the flash sequence.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PassageDisplay — collapsible passage panel for passage-based questions.
// Shows the passage title and body, with an optional display_duration_seconds
// countdown (after which the passage is hidden to simulate exam conditions).
// ---------------------------------------------------------------------------

function PassageDisplay({
  title,
  body,
  displayDurationSeconds,
  displayMode = "timed",
  replayMode = "not_permitted",
  hasBeenViewed = false,
  onPresentationEnd,
}: {
  title: string;
  body: string;
  displayDurationSeconds: number | null;
  displayMode?: "timed" | "unlimited";
  replayMode?: "permitted" | "not_permitted";
  hasBeenViewed?: boolean;
  onPresentationEnd?: () => void;
}) {
  // For 'timed' mode: passage starts hidden until user clicks 'Start Passage Presentation'
  // For 'unlimited' mode: passage is always visible
  // For 'not_permitted' replay mode: once viewed + time elapsed, cannot be viewed again
  const [presentationStarted, setPresentationStarted] = useState(
    displayMode === "unlimited" || (replayMode === "permitted" && hasBeenViewed),
  );
  const [visible, setVisible] = useState(displayMode === "unlimited");
  const [secondsLeft, setSecondsLeft] = useState<number | null>(
    displayMode === "timed" ? displayDurationSeconds : null,
  );

  // Countdown for timed passages
  useEffect(() => {
    if (secondsLeft === null || secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((s) => {
        if (s === null || s <= 1) {
          clearInterval(timer);
          setVisible(false);
          // Notify parent that the timed presentation has ended — used to
          // un-gate Question Text 2 + answer options per SRS feedback
          // Common Issue 4.
          if (onPresentationEnd) onPresentationEnd();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [secondsLeft]); // eslint-disable-line react-hooks/exhaustive-deps

  const startPresentation = () => {
    setPresentationStarted(true);
    setVisible(true);
    if (displayMode === "timed" && displayDurationSeconds) {
      setSecondsLeft(displayDurationSeconds);
    }
  };

  // Unlimited mode: always visible
  if (displayMode === "unlimited") {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3">
        <div className="mb-1 flex items-center justify-between">
          <p className="font-semibold text-slate-900">{title}</p>
        </div>
        {body && (
          <div
            className="prose prose-sm mt-1 max-w-none leading-relaxed text-slate-700"
            dangerouslySetInnerHTML={{ __html: body }}
          />
        )}
      </div>
    );
  }

  // Timed mode — passage not yet started
  if (!presentationStarted && replayMode === "not_permitted" && !hasBeenViewed) {
    return (
      <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-center">
        <p className="text-sm font-medium text-slate-700">Passage ready to view</p>
        <p className="mt-1 text-xs text-slate-600">
          When you click the button below, the passage will be displayed
          {displayDurationSeconds ? ` for ${displayDurationSeconds} seconds` : ""}. After the time
          elapses, the passage cannot be viewed again.
        </p>
        <Button size="sm" className="mt-3" onClick={startPresentation}>
          Start Passage Presentation
        </Button>
      </div>
    );
  }

  // Timed mode — passage was viewed but cannot be replayed
  if (!visible && replayMode === "not_permitted") {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-center">
        <p className="text-sm text-slate-600">
          Passage display time has elapsed. The passage is no longer visible.
        </p>
      </div>
    );
  }

  // Timed mode — replay permitted
  if (!visible && replayMode === "permitted") {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-center">
        <p className="text-sm text-slate-600">
          Passage display time has elapsed. You can replay it again.
        </p>
        <Button variant="outline" size="sm" className="mt-2" onClick={startPresentation}>
          Replay Passage
        </Button>
      </div>
    );
  }

  return (
    <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3">
      <div className="mb-1 flex items-center justify-between">
        <p className="font-semibold text-slate-900">{title}</p>
        {secondsLeft !== null && secondsLeft > 0 && (
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
            {secondsLeft}s left
          </span>
        )}
      </div>
      {body && (
        <div
          className="prose prose-sm mt-1 max-w-none leading-relaxed text-slate-700"
          dangerouslySetInnerHTML={{ __html: body }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GridCell — numbered-button cell for Grid Selection questions.
// Click the number to view the cell's content in a popup (SRS feedback Issue 14).
// Tick the checkbox to mark the cell as correct/incorrect.
// ---------------------------------------------------------------------------

interface GridCellOption {
  text_value?: string;
  image_file?: string | null;
}

function GridCell({
  cellIndex,
  cellOpt,
  selected,
  onToggle,
}: {
  cellIndex: number;
  cellOpt: GridCellOption | undefined;
  selected: boolean;
  onToggle: () => void;
}) {
  const [popupOpen, setPopupOpen] = useState(false);

  return (
    <td className="border border-slate-200 p-1 text-center align-top">
      <div
        className={`flex flex-col items-center gap-1 rounded-md p-1 ${
          selected ? "bg-green-50 ring-1 ring-green-300" : "bg-white"
        }`}
      >
        <button
          type="button"
          onClick={() => setPopupOpen(true)}
          className={`flex h-8 w-8 items-center justify-center rounded-md text-xs font-bold ${
            selected ? "bg-green-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
          aria-label={`View cell ${cellIndex + 1}`}
        >
          {cellIndex + 1}
        </button>
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="h-4 w-4"
          aria-label={`Select cell ${cellIndex + 1}`}
        />
      </div>
      {popupOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setPopupOpen(false)}
        >
          <div
            className="max-w-md rounded-md bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-semibold">Cell {cellIndex + 1}</p>
              <button
                type="button"
                onClick={() => setPopupOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>
            {cellOpt?.image_file ? (
              <img src={cellOpt.image_file} alt="" className="mx-auto mb-2 max-h-60" />
            ) : null}
            {cellOpt?.text_value ? (
              <p className="text-sm text-slate-700">{cellOpt.text_value}</p>
            ) : null}
            <div className="mt-3 flex justify-end gap-2">
              <Button
                size="sm"
                variant={selected ? "outline" : "primary"}
                onClick={() => {
                  onToggle();
                  setPopupOpen(false);
                }}
              >
                {selected ? "Unmark" : "Mark Correct"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </td>
  );
}

// ---------------------------------------------------------------------------
// ImageDisplayTimed — for Image Display (1h) questions with a display duration.
// Shows a Play button; clicking starts the timed display. After the duration
// elapses, the image disappears and cannot be replayed (if replay_mode is
// 'not_permitted'). On revisit (Previous button), the image is not shown.
// SRS feedback §8 Issue 1, 3, 4.
// ---------------------------------------------------------------------------

function ImageDisplayTimed({
  imageUrl,
  durationSeconds,
  replayMode = "not_permitted",
  hasBeenViewed = false,
  onPresentationEnd,
}: {
  imageUrl: string;
  durationSeconds: number;
  replayMode?: "permitted" | "not_permitted";
  hasBeenViewed?: boolean;
  onPresentationEnd?: () => void;
}) {
  const [visible, setVisible] = useState(false);
  const [started, setStarted] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  const replayLocked = hasBeenViewed && replayMode === "not_permitted";

  useEffect(() => {
    if (secondsLeft === null || secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((s) => {
        if (s === null || s <= 1) {
          clearInterval(timer);
          setVisible(false);
          if (onPresentationEnd) onPresentationEnd();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [secondsLeft]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = () => {
    setStarted(true);
    setVisible(true);
    setSecondsLeft(durationSeconds);
  };

  if (replayLocked && !visible) {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-6 text-center">
        <p className="text-sm text-slate-600">
          Image was already displayed. It cannot be viewed again.
        </p>
      </div>
    );
  }

  if (!started && !visible) {
    return (
      <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-center">
        <p className="text-sm font-medium text-slate-700">Image ready to view</p>
        <p className="mt-1 text-xs text-slate-600">
          When you click the button below, the image will be displayed for {durationSeconds}{" "}
          seconds. After the time elapses, the image cannot be viewed again.
        </p>
        <Button size="sm" className="mt-3" onClick={start}>
          Start Image Display
        </Button>
      </div>
    );
  }

  if (!visible && replayMode === "not_permitted") {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-center">
        <p className="text-sm text-slate-600">
          Image display time has elapsed. The image is no longer visible.
        </p>
      </div>
    );
  }

  if (!visible && replayMode === "permitted") {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-center">
        <p className="text-sm text-slate-600">
          Image display time has elapsed. You can view it again.
        </p>
        <Button variant="outline" size="sm" className="mt-2" onClick={start}>
          View Image Again
        </Button>
      </div>
    );
  }

  return (
    <div className="mb-4">
      <img
        src={imageUrl}
        alt="Question"
        className="max-h-[500px] w-full rounded-md border border-slate-200 object-contain"
      />
      {secondsLeft !== null && secondsLeft > 0 && (
        <p className="mt-1 text-center text-xs text-amber-700">{secondsLeft}s remaining</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AudioPlayerControlled — audio player that respects replay_mode.
// If replay_mode='not_permitted', audio plays once and cannot be replayed.
// On revisit (Previous button), the audio player is locked.
// SRS feedback §3 Issue 2 + Recommendation 2.
// ---------------------------------------------------------------------------

function AudioPlayerControlled({
  fileUrl,
  replayMode,
  hasBeenViewed,
  onPresentationEnd,
}: {
  fileUrl: string;
  replayMode: "permitted" | "not_permitted";
  hasBeenViewed: boolean;
  onPresentationEnd?: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [hasPlayed, setHasPlayed] = useState(false);

  const replayLocked = hasBeenViewed && replayMode === "not_permitted";

  const handleEnded = () => {
    setHasPlayed(true);
    if (onPresentationEnd) onPresentationEnd();
  };

  if (replayLocked) {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-center">
        <p className="text-sm text-slate-600">
          Audio was already played. Replay is not permitted for this question.
        </p>
      </div>
    );
  }

  return (
    <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="mb-2 text-xs font-medium text-slate-500">
        Audio {replayMode === "not_permitted" ? "(plays once — no replay)" : "(replay permitted)"}:
      </p>
      <audio
        ref={audioRef}
        controls
        src={fileUrl}
        onEnded={handleEnded}
        className="w-full"
        // Hide the seek bar when replay is not permitted — candidate can play
        // once from start to end, no scrubbing.
        style={
          replayMode === "not_permitted" && hasPlayed ? { pointerEvents: "none", opacity: 0.5 } : {}
        }
      >
        Your browser does not support audio playback.
      </audio>
      {replayMode === "not_permitted" && hasPlayed && (
        <p className="mt-1 text-xs text-amber-700">Audio has been played. Replay is disabled.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// VideoPlayerControlled — video player that respects replay_mode.
// Same logic as AudioPlayerControlled.
// ---------------------------------------------------------------------------

function VideoPlayerControlled({
  fileUrl,
  replayMode,
  hasBeenViewed,
  onPresentationEnd,
}: {
  fileUrl: string;
  replayMode: "permitted" | "not_permitted";
  hasBeenViewed: boolean;
  onPresentationEnd?: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [hasPlayed, setHasPlayed] = useState(false);

  const replayLocked = hasBeenViewed && replayMode === "not_permitted";

  const handleEnded = () => {
    setHasPlayed(true);
    if (onPresentationEnd) onPresentationEnd();
  };

  if (replayLocked) {
    return (
      <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-center">
        <p className="text-sm text-slate-600">
          Video was already played. Replay is not permitted for this question.
        </p>
      </div>
    );
  }

  return (
    <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="mb-2 text-xs font-medium text-slate-500">
        Video {replayMode === "not_permitted" ? "(plays once — no replay)" : "(replay permitted)"}:
      </p>
      <video
        ref={videoRef}
        controls
        src={fileUrl}
        onEnded={handleEnded}
        className="max-h-80 w-full rounded"
        style={
          replayMode === "not_permitted" && hasPlayed ? { pointerEvents: "none", opacity: 0.5 } : {}
        }
      >
        Your browser does not support video playback.
      </video>
      {replayMode === "not_permitted" && hasPlayed && (
        <p className="mt-1 text-xs text-amber-700">Video has been played. Replay is disabled.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ViewAllGridItemsButton — opens a popup listing all grid cell contents.
// SRS feedback §14 Recommendation — 'View Complete Grid Items' button.
// ---------------------------------------------------------------------------

function ViewAllGridItemsButton({ dragPoolOptions }: { dragPoolOptions: GridCellOption[] }) {
  const [open, setOpen] = useState(false);

  if (dragPoolOptions.length === 0) return null;

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        View Complete Grid Items ({dragPoolOptions.length})
      </Button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setOpen(false)}
        >
          <div
            className="max-h-[80vh] max-w-2xl overflow-y-auto rounded-md bg-white p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-semibold">All Grid Items ({dragPoolOptions.length})</p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {dragPoolOptions.map((opt, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 rounded-md border border-slate-200 p-3"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">
                    {i + 1}
                  </span>
                  <div className="flex-1">
                    {opt.image_file && (
                      <img
                        src={opt.image_file}
                        alt=""
                        className="mb-1 max-h-32 rounded border border-slate-200"
                      />
                    )}
                    {opt.text_value && <p className="text-sm text-slate-700">{opt.text_value}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
