/**
 * PassagePresentation — simulates the delivery-time passage question experience.
 *
 * Used in the QuestionDetailPage Preview tab for passage type (1g) questions.
 * At delivery time, the passage displays first (for display_duration_seconds),
 * then the passage is hidden and the question + options appear.
 *
 * Controls:
 *   - "Start passage presentation" button
 *   - "Skip" button to jump to question phase
 *   - "Replay" button after completion
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";

interface PassagePresentationProps {
  passageTitle: string;
  passageBody: string;
  displayDurationSeconds: number | null;
  /** The question content to show after passage display completes */
  children: React.ReactNode;
}

type Phase = "idle" | "passage" | "question";

export function PassagePresentation({
  passageTitle,
  passageBody,
  displayDurationSeconds,
  children,
}: PassagePresentationProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [timeLeft, setTimeLeft] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const duration =
    displayDurationSeconds && displayDurationSeconds > 0 ? displayDurationSeconds : 10;

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    stop();
    setTimeLeft(duration);
    setPhase("passage");
  }, [stop, duration]);

  const skip = useCallback(() => {
    stop();
    setPhase("question");
  }, [stop]);

  // Countdown timer during passage phase
  useEffect(() => {
    if (phase !== "passage") return;

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          stop();
          setPhase("question");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [phase, stop]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div>
      {/* Controls */}
      <div className="mb-4 flex items-center gap-2">
        {phase === "idle" && (
          <Button type="button" size="sm" onClick={start}>
            ▶ Start passage presentation
          </Button>
        )}
        {phase === "passage" && (
          <>
            <span className="text-xs text-slate-500">
              Passage displays · {timeLeft}s remaining…
            </span>
            <Button type="button" variant="outline" size="sm" onClick={skip}>
              ⏭ Skip to question
            </Button>
          </>
        )}
        {phase === "question" && (
          <Button type="button" variant="outline" size="sm" onClick={start}>
            ↻ Replay passage
          </Button>
        )}
      </div>

      {/* Phase 1: Passage display */}
      {phase === "passage" && (
        <div className="mb-4 rounded-lg border-2 border-blue-300 bg-blue-50 p-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
            Passage (displayed for {duration} seconds)
          </p>
          {passageTitle && <h3 className="text-lg font-bold text-slate-900">{passageTitle}</h3>}
          {passageBody && (
            <p className="mt-2 text-sm leading-relaxed text-slate-700">{passageBody}</p>
          )}
          {/* Countdown progress bar */}
          <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-blue-200">
            <div
              className="h-full bg-blue-600 transition-all duration-1000 ease-linear"
              style={{ width: `${(timeLeft / duration) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Phase 2: Question + options (shown after passage display completes) */}
      {phase === "question" && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Question (shown after passage)
          </p>
          {children}
        </div>
      )}

      {/* Idle state — show a hint */}
      {phase === "idle" && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">
            Click "Start passage presentation" to simulate the candidate experience. The passage
            will display for {duration} seconds, then the question will appear.
          </p>
        </div>
      )}
    </div>
  );
}
