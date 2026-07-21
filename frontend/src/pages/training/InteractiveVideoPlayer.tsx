/**
 * Interactive Video Player — plays a video with embedded questions (SRS §2.3.1).
 *
 * When the video reaches a question's trigger_timestamp, playback pauses
 * and the question modal appears. Based on the answer:
 *   - correct   → jump to correct_jump_to timestamp
 *   - incorrect → jump to incorrect_jump_to timestamp
 * Then playback resumes.
 */
import { useRef, useState } from "react";

import { Badge, Modal } from "@/components/ui";
import type { InteractiveQuestion } from "@/api/training";

export function InteractiveVideoPlayer({
  contentUrl,
  questions,
}: {
  contentUrl: string;
  questions: InteractiveQuestion[];
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [activeQuestion, setActiveQuestion] = useState<InteractiveQuestion | null>(null);
  const [answeredQuestions, setAnsweredQuestions] = useState<Set<number>>(new Set());
  const [feedback, setFeedback] = useState<{ correct: boolean; jumpTo: number } | null>(null);

  // Sort questions by trigger timestamp
  const sortedQuestions = [...questions].sort((a, b) => a.trigger_timestamp - b.trigger_timestamp);

  function handleTimeUpdate() {
    const video = videoRef.current;
    if (!video || activeQuestion) return;

    const currentTime = video.currentTime;
    // Find a question that should trigger at this time and hasn't been answered
    for (const q of sortedQuestions) {
      if (Math.abs(currentTime - q.trigger_timestamp) < 0.5 && !answeredQuestions.has(q.id)) {
        video.pause();
        setActiveQuestion(q);
        setFeedback(null);
        break;
      }
    }
  }

  function handleAnswer(optionId: number) {
    if (!activeQuestion || !videoRef.current) return;

    const correctOption = activeQuestion.options.find((o) => o.is_correct);
    const isCorrect = optionId === correctOption?.id;
    const jumpTo = isCorrect ? activeQuestion.correct_jump_to : activeQuestion.incorrect_jump_to;

    setFeedback({ correct: isCorrect, jumpTo });

    // Mark as answered
    setAnsweredQuestions((prev) => new Set(prev).add(activeQuestion.id));

    // After 2 seconds (showing feedback), jump and resume
    setTimeout(() => {
      if (videoRef.current) {
        videoRef.current.currentTime = jumpTo;
        videoRef.current.play();
      }
      setActiveQuestion(null);
      setFeedback(null);
    }, 2000);
  }

  if (!contentUrl) {
    return (
      <div className="rounded-md border border-slate-200 bg-slate-50 p-8 text-center">
        <p className="text-sm text-slate-500">No video content available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <video
          ref={videoRef}
          src={contentUrl}
          controls
          className="w-full rounded-md border border-slate-200"
          onTimeUpdate={handleTimeUpdate}
        />
        {sortedQuestions.length > 0 && (
          <div className="absolute bottom-12 left-2 flex gap-1">
            {sortedQuestions.map((q) => (
              <div
                key={q.id}
                className={`h-2 w-2 rounded-full ${
                  answeredQuestions.has(q.id) ? "bg-emerald-500" : "bg-amber-500"
                }`}
                title={`Question at ${q.trigger_timestamp.toFixed(0)}s`}
              />
            ))}
          </div>
        )}
      </div>

      {sortedQuestions.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Badge variant="outline">{sortedQuestions.length} interactive question(s)</Badge>
          <span>
            Yellow dots = upcoming, green dots = answered. Questions appear automatically during
            playback.
          </span>
        </div>
      )}

      {/* Question Modal */}
      {activeQuestion && (
        <Modal
          open
          onClose={() => {
            if (videoRef.current) videoRef.current.play();
            setActiveQuestion(null);
          }}
          title="Question"
          size="md"
        >
          <div className="space-y-4">
            <p className="text-base font-medium text-slate-900">{activeQuestion.question_text}</p>
            <div className="space-y-2">
              {activeQuestion.options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => handleAnswer(opt.id)}
                  disabled={!!feedback}
                  className="block w-full rounded-md border border-slate-200 px-4 py-2 text-left text-sm transition-colors hover:bg-slate-50 disabled:opacity-50"
                >
                  {opt.text}
                </button>
              ))}
            </div>
            {feedback && (
              <div
                className={`rounded-md p-3 text-sm ${
                  feedback.correct
                    ? "bg-emerald-50 text-emerald-800"
                    : "bg-orange-50 text-orange-800"
                }`}
              >
                {feedback.correct
                  ? "✓ Correct! Jumping to the next section..."
                  : "✗ Not quite. Let's review that part again..."}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
