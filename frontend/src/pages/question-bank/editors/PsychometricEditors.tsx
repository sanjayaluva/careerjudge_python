/**
 * Psychometric Editors — for types 6a (Rank), 6b (Rank-then-Rate),
 * 7 (Rating Scale), 8a (Forced-Choice Single), 8b (Forced-Choice Two-Level)
 */
import { Input, Label, Button } from "@/components/ui";
import {
  AddOptionButton,
  RankOptionRow,
  RatingRow,
  createEmptyOption,
  type OptionData,
} from "./shared";

// ---------------------------------------------------------------------------
// Rank Editor (6a)
// ---------------------------------------------------------------------------

interface RankEditorProps {
  data: {
    question_text_1: string;
    options: OptionData[];
  };
  onChange: (data: RankEditorProps["data"]) => void;
}

export function RankEditor({ data, onChange }: RankEditorProps) {
  const updateOption = (index: number, option: OptionData) => {
    const newOptions = [...data.options];
    newOptions[index] = option;
    onChange({ ...data, options: newOptions });
  };

  const addOption = () => {
    onChange({
      ...data,
      options: [...data.options, createEmptyOption(data.options.length, "RANK")],
    });
  };

  const removeOption = (index: number) => {
    onChange({ ...data, options: data.options.filter((_, i) => i !== index) });
  };

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Question text
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder="Rank the following items from highest (1) to lowest..."
        />
      </div>

      <div className="space-y-2">
        <Label>Items to Rank (candidate assigns rank 1 = highest)</Label>
        {data.options.map((opt, i) => (
          <RankOptionRow
            key={i}
            option={opt}
            index={i}
            onChange={updateOption}
            onRemove={removeOption}
          />
        ))}
        <AddOptionButton onClick={addOption} label="Add item" />
      </div>

      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-2 text-sm text-slate-900">{data.question_text_1}</p>
        <div className="space-y-1">
          {data.options.map((opt, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-slate-700">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs">
                {i + 1}
              </span>
              {opt.text_value || `(item ${i + 1})`}
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Score: Rank 1 = {data.options.length} pts, Rank 2 = {data.options.length - 1} pts, etc.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rank-then-Rate Editor (6b)
// ---------------------------------------------------------------------------

interface RankRateEditorProps {
  data: {
    question_text_1: string;
    rating_scale_points: string;
    options: OptionData[];
  };
  onChange: (data: RankRateEditorProps["data"]) => void;
}

export function RankRateEditor({ data, onChange }: RankRateEditorProps) {
  const updateOption = (index: number, option: OptionData) => {
    const newOptions = [...data.options];
    newOptions[index] = option;
    onChange({ ...data, options: newOptions });
  };
  const addOption = () => {
    onChange({
      ...data,
      options: [...data.options, createEmptyOption(data.options.length, "RANK")],
    });
  };
  const removeOption = (index: number) => {
    onChange({ ...data, options: data.options.filter((_, i) => i !== index) });
  };
  const scalePoints = parseInt(data.rating_scale_points) || 7;

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Question text
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder="Rank and rate the following items..."
        />
      </div>
      <div>
        <Label htmlFor="rsp">Rating scale points</Label>
        <Input
          id="rsp"
          type="number"
          min="2"
          max="10"
          value={data.rating_scale_points}
          onChange={(e) => onChange({ ...data, rating_scale_points: e.target.value })}
        />
        <p className="mt-1 text-xs text-slate-500">
          e.g. 7 = 7-point rating scale (1=lowest, 7=highest)
        </p>
      </div>
      <div className="space-y-2">
        <Label>Items (candidate ranks 1-N, then rates each on {scalePoints}-point scale)</Label>
        {data.options.map((opt, i) => (
          <RankOptionRow
            key={i}
            option={opt}
            index={i}
            onChange={updateOption}
            onRemove={removeOption}
          />
        ))}
        <AddOptionButton onClick={addOption} label="Add item" />
      </div>
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-2 text-sm text-slate-900">{data.question_text_1}</p>
        <div className="space-y-1">
          {data.options.map((opt, i) => (
            <div key={i} className="flex items-center gap-3 text-sm text-slate-700">
              <select className="h-7 rounded border border-slate-200 text-xs" disabled>
                <option>Rank {i + 1}</option>
              </select>
              <span>{opt.text_value || `(item ${i + 1})`}</span>
              <select className="ml-auto h-7 rounded border border-slate-200 text-xs" disabled>
                {Array.from({ length: scalePoints }).map((_, p) => (
                  <option key={p}>{p + 1}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Score per item = (total_items - rank + 1) × rating. Max = {data.options.length} ×{" "}
          {scalePoints} = {data.options.length * scalePoints}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rating Scale Editor (7)
// ---------------------------------------------------------------------------

interface RatingEditorProps {
  data: {
    question_text_1: string;
    rating_scale_points: string;
    rating_direction: string;
    options: OptionData[];
  };
  onChange: (data: RatingEditorProps["data"]) => void;
}

export function RatingEditor({ data, onChange }: RatingEditorProps) {
  const updateOption = (index: number, option: OptionData) => {
    const newOptions = [...data.options];
    newOptions[index] = option;
    onChange({ ...data, options: newOptions });
  };
  const addOption = () => {
    onChange({ ...data, options: [...data.options, createEmptyOption(data.options.length)] });
  };
  const removeOption = (index: number) => {
    onChange({ ...data, options: data.options.filter((_, i) => i !== index) });
  };
  const scalePoints = parseInt(data.rating_scale_points) || 5;

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Instructions
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder="Rate each statement on the scale..."
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="rsp">Scale points</Label>
          <Input
            id="rsp"
            type="number"
            min="2"
            max="10"
            value={data.rating_scale_points}
            onChange={(e) => onChange({ ...data, rating_scale_points: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="rdir">Scoring direction</Label>
          <select
            id="rdir"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={data.rating_direction}
            onChange={(e) => onChange({ ...data, rating_direction: e.target.value })}
          >
            <option value="FORWARD">Forward (leftmost = highest score)</option>
            <option value="REVERSE">Reverse (rightmost = highest score)</option>
          </select>
        </div>
      </div>
      <div className="space-y-2">
        <Label>Statements to Rate</Label>
        {data.options.map((opt, i) => (
          <RatingRow
            key={i}
            option={opt}
            index={i}
            onChange={updateOption}
            onRemove={removeOption}
          />
        ))}
        <AddOptionButton onClick={addOption} label="Add statement" />
      </div>
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-2 text-sm text-slate-900">{data.question_text_1}</p>
        <div className="space-y-1">
          {data.options.map((opt, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className="flex-1 text-slate-700">
                {opt.text_value || `(statement ${i + 1})`}
              </span>
              <div className="flex gap-1">
                {Array.from({ length: scalePoints }).map((_, p) => (
                  <span
                    key={p}
                    className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-300 text-xs text-slate-400"
                  >
                    {p + 1}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {data.rating_direction === "REVERSE"
            ? "Reverse: rightmost = highest"
            : "Forward: leftmost = highest"}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Forced-Choice Editor (8a, 8b)
// ---------------------------------------------------------------------------

interface ForcedChoiceEditorProps {
  questionType: string;
  data: {
    question_text_1: string;
    rating_scale_points: string;
    options: OptionData[];
  };
  onChange: (data: ForcedChoiceEditorProps["data"]) => void;
}

export function ForcedChoiceEditor({ questionType, data, onChange }: ForcedChoiceEditorProps) {
  const isTwoLevel = questionType === "FORCED_CHOICE_TWO_LEVEL";
  const updateOption = (index: number, option: OptionData) => {
    const newOptions = [...data.options];
    newOptions[index] = option;
    onChange({ ...data, options: newOptions });
  };
  const addPair = () => {
    const nextOrder = data.options.length;
    onChange({
      ...data,
      options: [
        ...data.options,
        { ...createEmptyOption(nextOrder, "FORCED_CHOICE") },
        { ...createEmptyOption(nextOrder + 1, "FORCED_CHOICE") },
      ],
    });
  };
  const removeOption = (index: number) => {
    onChange({ ...data, options: data.options.filter((_, i) => i !== index) });
  };

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Question text
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder={isTwoLevel ? "Select one option and rate it..." : "Select one option..."}
        />
      </div>

      {isTwoLevel && (
        <div>
          <Label htmlFor="rsp">Rating scale points (Level 2)</Label>
          <Input
            id="rsp"
            type="number"
            min="2"
            max="10"
            value={data.rating_scale_points}
            onChange={(e) => onChange({ ...data, rating_scale_points: e.target.value })}
          />
        </div>
      )}

      <div className="space-y-3">
        <Label>Option Pairs (exactly 2 options per question)</Label>
        <p className="text-xs text-slate-500">
          Each forced-choice question has exactly 2 options. Set predefined scores for each.
          {isTwoLevel && " Candidate selects one, then rates it."}
        </p>
        {data.options.map((opt, i) => (
          <RatingRow
            key={i}
            option={opt}
            index={i}
            onChange={updateOption}
            onRemove={removeOption}
            showScore
            scoreLabel="Predefined score"
          />
        ))}
        {data.options.length < 2 && (
          <Button type="button" variant="outline" size="sm" onClick={addPair}>
            + Add option pair
          </Button>
        )}
      </div>

      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-2 text-sm text-slate-900">{data.question_text_1}</p>
        <div className="space-y-1">
          {data.options.map((opt, i) => (
            <label key={i} className="flex items-center gap-2 text-sm">
              <input type="radio" name="fc-preview" className="h-4 w-4" readOnly />
              <span className="text-slate-700">{opt.text_value || `(option ${i + 1})`}</span>
              <span className="ml-auto text-xs text-slate-400">score: {opt.predefined_score}</span>
            </label>
          ))}
        </div>
        {isTwoLevel && (
          <p className="mt-2 text-xs text-slate-500">
            After selecting, candidate rates on {data.rating_scale_points || "N"}-point scale. Final
            score = predefined × rating.
          </p>
        )}
      </div>
    </div>
  );
}
