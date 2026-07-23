/**
 * Timeliner — trainer authoring UI for interactive video questions (SRS §2.3.1).
 *
 * Shows the video player with a timeline. Trainer can:
 * - Play/seek the video
 * - "Add question at current time" — captures the current timestamp
 * - Fill in question text + MCQ options + mark correct option
 * - Set jump-to timestamps for correct/incorrect answers
 * - See existing questions as markers on the timeline
 * - Delete existing questions
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Badge, Button, Input, Label, Modal, useToast } from "@/components/ui";
import {
  createInteractiveQuestion,
  listInteractiveQuestions,
  type InteractiveQuestionOption,
} from "@/api/training";
import { extractApiError } from "@/api/client";

export function TimelinerEditor({
  contentId,
  contentUrl,
  title,
  onClose,
}: {
  contentId: number;
  contentUrl: string;
  title: string;
  onClose: () => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showAddForm, setShowAddForm] = useState(false);

  // Load existing questions
  const { data: questions, isLoading } = useQuery({
    queryKey: ["training", "interactive-questions", contentId],
    queryFn: () => listInteractiveQuestions(contentId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: {
      question_text: string;
      trigger_timestamp: number;
      options: InteractiveQuestionOption[];
      correct_jump_to: number;
      incorrect_jump_to: number;
    }) => createInteractiveQuestion(contentId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["training", "interactive-questions", contentId],
      });
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success("Interactive question added.");
      setShowAddForm(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const sortedQuestions = [...(questions ?? [])].sort(
    (a, b) => a.trigger_timestamp - b.trigger_timestamp,
  );

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  function seekTo(time: number) {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Timeliner — ${title}`} size="xl">
      <div className="space-y-4">
        {/* Video player */}
        <div className="relative">
          <video
            ref={videoRef}
            src={contentUrl}
            controls
            className="w-full rounded-md border border-slate-200"
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
            onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          />
          {/* Question markers on the timeline */}
          {duration > 0 && sortedQuestions.length > 0 && (
            <div className="relative mt-1 h-6 w-full rounded bg-slate-100">
              {sortedQuestions.map((q, i) => (
                <button
                  key={q.id}
                  onClick={() => seekTo(q.trigger_timestamp)}
                  className="absolute top-0 flex h-6 w-6 -translate-x-1/2 items-center justify-center rounded-full border-2 border-amber-500 bg-amber-100 text-xs font-bold text-amber-700 hover:bg-amber-200"
                  style={{ left: `${(q.trigger_timestamp / duration) * 100}%` }}
                  title={`Q${i + 1} at ${formatTime(q.trigger_timestamp)}: ${q.question_text}`}
                >
                  {i + 1}
                </button>
              ))}
              {/* Current position indicator */}
              <div
                className="absolute top-0 h-6 w-0.5 bg-primary-500"
                style={{ left: `${(currentTime / duration) * 100}%` }}
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-500">
            Current position: <strong>{formatTime(currentTime)}</strong>
            {duration > 0 && <> / {formatTime(duration)}</>}
          </div>
          <Button size="sm" onClick={() => setShowAddForm(true)}>
            + Add question at {formatTime(currentTime)}
          </Button>
        </div>

        {/* Existing questions list */}
        {!isLoading && sortedQuestions.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-semibold text-slate-700">
              Interactive Questions ({sortedQuestions.length})
            </div>
            {sortedQuestions.map((q, i) => (
              <div key={q.id} className="rounded-md border border-slate-100 p-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="warning">Q{i + 1}</Badge>
                      <span className="text-xs text-slate-500">
                        Trigger: {formatTime(q.trigger_timestamp)}
                      </span>
                      <span className="text-xs text-emerald-600">
                        ✓ → {formatTime(q.correct_jump_to)}
                      </span>
                      <span className="text-xs text-orange-600">
                        ✗ → {formatTime(q.incorrect_jump_to)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-900">{q.question_text}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {q.options.map((opt) => (
                        <Badge key={opt.id} variant={opt.is_correct ? "success" : "outline"}>
                          {opt.is_correct ? "✓ " : ""}
                          {opt.text}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => seekTo(q.trigger_timestamp)}>
                    Jump to
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add question form */}
        {showAddForm && (
          <QuestionForm
            triggerTimestamp={currentTime}
            duration={duration}
            onSubmit={(payload) => createMutation.mutate(payload)}
            loading={createMutation.isPending}
            onCancel={() => setShowAddForm(false)}
          />
        )}
      </div>
    </Modal>
  );
}

function QuestionForm({
  triggerTimestamp,
  duration,
  onSubmit,
  loading,
  onCancel,
}: {
  triggerTimestamp: number;
  duration: number;
  onSubmit: (payload: {
    question_text: string;
    trigger_timestamp: number;
    options: InteractiveQuestionOption[];
    correct_jump_to: number;
    incorrect_jump_to: number;
  }) => void;
  loading: boolean;
  onCancel: () => void;
}) {
  const [questionText, setQuestionText] = useState("");
  const [options, setOptions] = useState<{ id: number; text: string; is_correct: boolean }[]>([
    { id: 1, text: "", is_correct: true },
    { id: 2, text: "", is_correct: false },
  ]);
  const [correctJump, setCorrectJump] = useState(
    String(Math.min(triggerTimestamp + 30, duration || triggerTimestamp + 30)),
  );
  const [incorrectJump, setIncorrectJump] = useState(String(triggerTimestamp));

  function fmt(s: string): string {
    const sec = parseFloat(s);
    const m = Math.floor(sec / 60);
    const ss = Math.floor(sec % 60);
    return `${m}:${ss.toString().padStart(2, "0")}`;
  }

  return (
    <div className="space-y-3 rounded-md border border-slate-200 p-4">
      <div className="text-sm font-semibold text-slate-900">
        New Question at {fmt(String(triggerTimestamp))}
      </div>

      <div>
        <Label htmlFor="q-text" required>
          Question text
        </Label>
        <textarea
          id="q-text"
          rows={2}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
          value={questionText}
          onChange={(e) => setQuestionText(e.target.value)}
          placeholder="e.g., What did the speaker just mention?"
          required
        />
      </div>

      <div>
        <Label>Answer options</Label>
        <div className="space-y-2">
          {options.map((opt, i) => (
            <div key={opt.id} className="flex items-center gap-2">
              <input
                type="radio"
                name="correct-option"
                checked={opt.is_correct}
                onChange={() =>
                  setOptions(options.map((o) => ({ ...o, is_correct: o.id === opt.id })))
                }
                className="h-4 w-4"
                title="Mark as correct"
              />
              <Input
                value={opt.text}
                onChange={(e) => {
                  const next = [...options];
                  next[i] = { ...opt, text: e.target.value };
                  setOptions(next);
                }}
                placeholder={`Option ${i + 1}`}
                className="flex-1"
              />
              {options.length > 2 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setOptions(options.filter((o) => o.id !== opt.id))}
                >
                  ✕
                </Button>
              )}
            </div>
          ))}
        </div>
        {options.length < 5 && (
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              setOptions([...options, { id: options.length + 1, text: "", is_correct: false }])
            }
          >
            + Add option
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="correct-jump" required>
            If correct → jump to (seconds)
          </Label>
          <Input
            id="correct-jump"
            type="number"
            step="0.1"
            min="0"
            value={correctJump}
            onChange={(e) => setCorrectJump(e.target.value)}
          />
          <span className="text-xs text-emerald-600">{fmt(correctJump)}</span>
        </div>
        <div>
          <Label htmlFor="incorrect-jump" required>
            If incorrect → jump to (seconds)
          </Label>
          <Input
            id="incorrect-jump"
            type="number"
            step="0.1"
            min="0"
            value={incorrectJump}
            onChange={(e) => setIncorrectJump(e.target.value)}
          />
          <span className="text-xs text-orange-600">{fmt(incorrectJump)}</span>
        </div>
      </div>

      <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          loading={loading}
          disabled={!questionText || options.some((o) => !o.text)}
          onClick={() =>
            onSubmit({
              question_text: questionText,
              trigger_timestamp: triggerTimestamp,
              options,
              correct_jump_to: parseFloat(correctJump),
              incorrect_jump_to: parseFloat(incorrectJump),
            })
          }
        >
          Add question
        </Button>
      </div>
    </div>
  );
}
