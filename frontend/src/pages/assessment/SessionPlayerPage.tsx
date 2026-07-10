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
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Alert, AlertDescription, Button, Label, Spinner } from "@/components/ui";
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
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Record<string, unknown>>>({});
  const [bookmarked, setBookmarked] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ["assessment-session", sid],
    queryFn: () => retrieveSession(sid),
    enabled: !Number.isNaN(sid),
  });

  // Timer countdown
  useEffect(() => {
    if (!session || session.status !== "active") return;
    // Get duration from the assessment (stored on session.assessment)
    // For now, use a simple approach: check if total_duration_seconds is set
    // We'll need the assessment data — retrieve from session
    // The session API returns assessment_title but not duration directly.
    // For simplicity, we'll skip timer if duration is not available.
  }, [session]);

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

  const { data: questions, isLoading: questionsLoading } = useQuery({
    queryKey: ["assessment-session-questions", sid],
    queryFn: () => getSessionQuestions(sid),
    enabled: !Number.isNaN(sid),
  });

  const answerMutation = useMutation({
    mutationFn: (payload: {
      question_id: number;
      raw_answer?: Record<string, unknown>;
      bookmark?: boolean;
    }) => submitAnswer(sid, payload),
    onError: (err) => setError(extractApiError(err)),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitSessionResult(sid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessment-session", sid] });
      navigate(`/assessments/sessions/${sid}/results`);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const suspendMutation = useMutation({
    mutationFn: () => suspendSession(sid),
    onSuccess: () => navigate("/assessments"),
    onError: (err) => setError(extractApiError(err)),
  });

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

  const handleNext = () => {
    // Save current answer
    const currentAnswer = answers[answerKey];
    if (currentAnswer) {
      answerMutation.mutate({
        question_id: q.question,
        raw_answer: currentAnswer,
      });
    }
    if (!isLast) setCurrentIndex((i) => i + 1);
  };

  const handlePrev = () => {
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
    answerMutation.mutate({ question_id: q.question, bookmark: true });
  };

  const handleSubmit = () => {
    if (
      confirm(
        `Submit assessment? You have answered ${answeredCount} of ${questions.length} questions.`,
      )
    ) {
      submitMutation.mutate();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top bar */}
      <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-sm font-bold text-slate-900">{session.assessment_title}</h1>
            <p className="text-xs text-slate-500">
              Question {currentIndex + 1} of {questions.length} · Answered: {answeredCount} ·
              Bookmarked: {bookmarkedCount}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {timeLeft !== null && timeLeft > 0 && (
              <span
                className={`font-mono text-sm font-bold ${timeLeft < 60 ? "text-danger" : "text-slate-600"}`}
              >
                {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, "0")}
              </span>
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
      </div>

      {/* Question content */}
      <div className="mx-auto max-w-3xl px-6 py-8">
        {error && (
          <Alert variant="error" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="rounded-lg border border-slate-200 bg-white p-6">
          {/* Question type badge */}
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              {qd.question_type_label}
            </span>
            {qd.difficulty_level && (
              <span className="text-xs text-slate-400">· {qd.difficulty_level}</span>
            )}
            <button
              onClick={handleBookmark}
              className={`ml-auto text-sm ${bookmarked.has(answerKey) ? "text-primary-600" : "text-slate-400 hover:text-slate-600"}`}
            >
              {bookmarked.has(answerKey) ? "★ Bookmarked" : "☆ Bookmark"}
            </button>
          </div>

          {/* Flash items (for flash types) */}
          {qd.flash_items.length > 0 && (
            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3">
              <p className="mb-2 text-xs font-medium text-amber-700">
                Flash items ({qd.flash_interval_ms}ms each · {qd.flash_display_count} shown):
              </p>
              <div className="flex flex-wrap gap-2">
                {qd.flash_items.map((fi) => (
                  <div
                    key={fi.id}
                    className="flex h-12 w-12 items-center justify-center rounded border border-slate-300 bg-white p-1"
                  >
                    {fi.item_type === "IMAGE" && fi.image_file ? (
                      <img
                        src={fi.image_file}
                        alt=""
                        className="max-h-full max-w-full object-contain"
                      />
                    ) : (
                      <span className="text-xs font-medium">{fi.text_value}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Passage (for passage type) */}
          {qd.passage_title && (
            <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3">
              <p className="font-semibold text-slate-900">{qd.passage_title}</p>
              {qd.passage_body && <p className="mt-1 text-sm text-slate-700">{qd.passage_body}</p>}
            </div>
          )}

          {/* Question image */}
          {qd.image && (
            <img
              src={qd.image}
              alt="Question"
              className="mb-4 max-h-60 rounded-md border border-slate-200"
            />
          )}

          {/* Question text */}
          <p className="mb-4 text-base font-medium text-slate-900">{qd.question_text_1}</p>
          {qd.question_text_2 && (
            <p className="mb-4 text-sm text-slate-600">{qd.question_text_2}</p>
          )}

          {/* Answer input area — by question type */}
          <AnswerInput
            question={q}
            currentAnswer={answers[answerKey]}
            onChange={(ans) => setAnswers({ ...answers, [answerKey]: ans })}
          />
        </div>

        {/* Navigation */}
        <div className="mt-6 flex items-center justify-between">
          <Button variant="outline" onClick={handlePrev} disabled={currentIndex === 0}>
            ← Previous
          </Button>
          <div className="flex gap-1">
            {questions.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentIndex(i)}
                className={`h-8 w-8 rounded-md text-xs font-medium ${
                  i === currentIndex
                    ? "bg-primary-600 text-white"
                    : answers[`${questions[i].question}_${questions[i].sub_question_index}`]
                      ? "bg-green-100 text-green-700"
                      : bookmarked.has(
                            `${questions[i].question}_${questions[i].sub_question_index}`,
                          )
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-500"
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
          {isLast ? (
            <Button onClick={handleSubmit} loading={submitMutation.isPending}>
              Submit
            </Button>
          ) : (
            <Button onClick={handleNext}>Next →</Button>
          )}
        </div>
      </div>
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
    const isMulti = qd.options.filter((o) => o.is_correct).length > 1;
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

    return (
      <div className="space-y-2">
        {qd.options
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
                className="h-4 w-4"
              />
              {opt.image_file && <img src={opt.image_file} alt="" className="h-8 w-8 rounded" />}
              <span>{opt.text_value || "(image)"}</span>
            </label>
          ))}
      </div>
    );
  }

  // FITB types — text inputs
  if (qType.startsWith("FITB_")) {
    const answers: string[] = (currentAnswer?.answers as string[]) || [];
    const fields = qd.options.filter((o) => o.option_type === "TEXT");

    return (
      <div className="space-y-2">
        {fields.map((opt, i) => (
          <div key={opt.id}>
            <Label className="text-xs text-slate-500">Field {i + 1}</Label>
            <input
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
          </div>
        ))}
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
              {/* Show click markers */}
              <svg
                className="pointer-events-none absolute left-0 top-0"
                width="100%"
                height="100%"
                viewBox={`0 0 ${qd.image_width || 400} ${qd.image_height || 300}`}
                preserveAspectRatio="none"
              >
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
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Group A</p>
            {groupA.map((opt) => {
              const matchedB = getMatchedB(opt.id);
              const matchedBOpt = groupB.find((b) => b.id === matchedB);
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
            <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Group B</p>
            {groupB.map((opt) => {
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

  // Grid — checkbox grid
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

    const isCellSelected = (r: number, c: number) =>
      selectedCells.some((cell) => cell.r === r && cell.c === c);

    // Get cell content from DRAG_POOL options
    const dragPoolOptions = qd.options.filter((o) => o.option_type === "DRAG_POOL");

    return (
      <div>
        <p className="mb-3 text-xs text-slate-500">
          Select the correct cells by checking the boxes:
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="border border-slate-200 p-2"></th>
              {Array.from({ length: cols }).map((_, c) => (
                <th
                  key={c}
                  className="border border-slate-200 p-2 text-center text-xs text-slate-600"
                >
                  Col {c + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }).map((_, r) => (
              <tr key={r}>
                <td className="border border-slate-200 p-2 text-xs font-medium text-slate-600">
                  Row {r + 1}
                </td>
                {Array.from({ length: cols }).map((_, c) => {
                  const cellOpt = dragPoolOptions[r * cols + c];
                  return (
                    <td key={c} className="border border-slate-200 p-2 text-center">
                      {cellOpt?.image_file ? (
                        <img src={cellOpt.image_file} alt="" className="mx-auto mb-1 max-h-10" />
                      ) : cellOpt?.text_value ? (
                        <div className="mb-1 text-xs">{cellOpt.text_value}</div>
                      ) : null}
                      <input
                        type="checkbox"
                        checked={isCellSelected(r, c)}
                        onChange={() => toggleCell(r, c)}
                        className="h-4 w-4"
                      />
                    </td>
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
