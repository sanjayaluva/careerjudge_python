/**
 * Shared components for question type editors.
 * Used by MCQ, FITB, Match, Grid, Rank, Rating, Forced-Choice editors.
 */
import { Button, Input, Label } from "@/components/ui";

// ---------------------------------------------------------------------------
// Option Row — editable response option
// ---------------------------------------------------------------------------

export interface OptionData {
  id?: number;
  sub_question_index: number;
  option_type: string;
  label: string;
  text_value: string;
  is_correct: boolean;
  match_pair_id: number | null;
  predefined_score: number;
  order: number;
  correct_answers: { id?: number; answer_text: string; order: number }[];
}

interface OptionRowProps {
  option: OptionData;
  index: number;
  onChange: (index: number, option: OptionData) => void;
  onRemove: (index: number) => void;
  showCorrect?: boolean;
  showImageOption?: boolean;
  correctAnswerMode?: boolean;
  label?: string;
}

export function OptionRow({
  option,
  index,
  onChange,
  onRemove,
  showCorrect = true,
  correctAnswerMode = false,
  label = "Option",
}: OptionRowProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-slate-200 p-3">
      <div className="flex-1 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">
            {label} {index + 1}
          </span>
          {showCorrect && (
            <label className="flex items-center gap-1 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={option.is_correct}
                onChange={(e) => onChange(index, { ...option, is_correct: e.target.checked })}
                className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
              />
              Correct
            </label>
          )}
        </div>
        <Input
          value={option.text_value}
          onChange={(e) => onChange(index, { ...option, text_value: e.target.value })}
          placeholder="Enter option text..."
          className="text-sm"
        />
        {correctAnswerMode && (
          <div className="space-y-1">
            <Label className="text-xs text-slate-500">
              Correct answers (one per line, up to 5)
            </Label>
            <textarea
              rows={3}
              value={option.correct_answers.map((ca) => ca.answer_text).join("\n")}
              onChange={(e) => {
                const lines = e.target.value.split("\n").slice(0, 5);
                onChange(index, {
                  ...option,
                  correct_answers: lines.map((text, i) => ({
                    answer_text: text,
                    order: i,
                  })),
                });
              }}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary-600"
              placeholder="answer1&#10;answer2&#10;answer3"
            />
          </div>
        )}
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="text-danger hover:bg-danger-50"
        onClick={() => onRemove(index)}
      >
        Remove
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Match Pair Row — Group A + Group B linked items
// ---------------------------------------------------------------------------

export interface MatchPairData {
  pairId: number;
  groupA: OptionData;
  groupB: OptionData;
}

interface MatchPairRowProps {
  pair: MatchPairData;
  index: number;
  onChange: (index: number, pair: MatchPairData) => void;
  onRemove: (index: number) => void;
}

export function MatchPairRow({ pair, index, onChange, onRemove }: MatchPairRowProps) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500">Pair {index + 1}</span>
        <Button
          variant="ghost"
          size="sm"
          className="text-danger hover:bg-danger-50"
          onClick={() => onRemove(index)}
        >
          Remove
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs text-slate-500">Group A</Label>
          <Input
            value={pair.groupA.text_value}
            onChange={(e) =>
              onChange(index, {
                ...pair,
                groupA: { ...pair.groupA, text_value: e.target.value },
              })
            }
            placeholder="Group A item..."
            className="text-sm"
          />
        </div>
        <div>
          <Label className="text-xs text-slate-500">Group B (correct match)</Label>
          <Input
            value={pair.groupB.text_value}
            onChange={(e) =>
              onChange(index, {
                ...pair,
                groupB: { ...pair.groupB, text_value: e.target.value },
              })
            }
            placeholder="Group B item..."
            className="text-sm"
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rank Option Row — for ranking questions
// ---------------------------------------------------------------------------

interface RankOptionRowProps {
  option: OptionData;
  index: number;
  onChange: (index: number, option: OptionData) => void;
  onRemove: (index: number) => void;
}

export function RankOptionRow({ option, index, onChange, onRemove }: RankOptionRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-slate-200 p-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-medium text-slate-600">
        {index + 1}
      </span>
      <Input
        value={option.text_value}
        onChange={(e) => onChange(index, { ...option, text_value: e.target.value })}
        placeholder="Enter item to rank..."
        className="flex-1 text-sm"
      />
      <Button
        variant="ghost"
        size="sm"
        className="text-danger hover:bg-danger-50"
        onClick={() => onRemove(index)}
      >
        Remove
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rating Scale Row — for rating/forced-choice questions
// ---------------------------------------------------------------------------

interface RatingRowProps {
  option: OptionData;
  index: number;
  onChange: (index: number, option: OptionData) => void;
  onRemove: (index: number) => void;
  showScore?: boolean;
  scoreLabel?: string;
}

export function RatingRow({
  option,
  index,
  onChange,
  onRemove,
  showScore = false,
  scoreLabel = "Predefined score",
}: RatingRowProps) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <Input
            value={option.text_value}
            onChange={(e) => onChange(index, { ...option, text_value: e.target.value })}
            placeholder="Enter statement..."
            className="text-sm"
          />
        </div>
        {showScore && (
          <div className="w-28">
            <Label className="text-xs text-slate-500">{scoreLabel}</Label>
            <Input
              type="number"
              value={option.predefined_score}
              onChange={(e) =>
                onChange(index, {
                  ...option,
                  predefined_score: Number(e.target.value),
                })
              }
              className="text-sm"
              step="0.5"
            />
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="text-danger hover:bg-danger-50"
          onClick={() => onRemove(index)}
        >
          Remove
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add Option Button
// ---------------------------------------------------------------------------

export function AddOptionButton({
  onClick,
  label = "Add option",
}: {
  onClick: () => void;
  label?: string;
}) {
  return (
    <Button type="button" variant="outline" size="sm" onClick={onClick}>
      + {label}
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function createEmptyOption(order: number, type = "TEXT"): OptionData {
  return {
    sub_question_index: 0,
    option_type: type,
    label: "",
    text_value: "",
    is_correct: false,
    match_pair_id: null,
    predefined_score: 1.0,
    order,
    correct_answers: [],
  };
}

export function createEmptyMatchPair(pairId: number, order: number): MatchPairData {
  return {
    pairId,
    groupA: { ...createEmptyOption(order, "MATCH_A"), match_pair_id: pairId },
    groupB: { ...createEmptyOption(order, "MATCH_B"), match_pair_id: pairId },
  };
}
