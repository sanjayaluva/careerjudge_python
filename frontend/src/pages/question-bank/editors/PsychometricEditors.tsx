/**
 * Rating Scale Editor (7) — single row of rating scale points with labels.
 *
 * The rating question is ONE statement with N scale points (columns).
 * Each column has a label (e.g. "Very True", "Not at all True") and a value.
 * The candidate selects one point on the scale.
 *
 * NOT multiple rows of statements — that's a different pattern.
 * This is a single-row rating field.
 */
import { Input, Label } from "@/components/ui";
import { createEmptyOption, type OptionData } from "./shared";

interface RatingScaleEditorProps {
  data: {
    question_text_1: string;
    rating_scale_points: string;
    rating_direction: string;
    scaleLabels: string[];
  };
  onChange: (data: RatingScaleEditorProps["data"]) => void;
}

export function RatingEditor({ data, onChange }: RatingScaleEditorProps) {
  const scalePoints = parseInt(data.rating_scale_points) || 5;

  const updateScaleLabels = () => {
    const n = parseInt(data.rating_scale_points) || 5;
    const newLabels = Array(n)
      .fill("")
      .map((_, i) => data.scaleLabels[i] || defaultLabels(i, n));
    onChange({ ...data, scaleLabels: newLabels });
  };

  const defaultLabels = (index: number, total: number): string => {
    const labels = [
      "Not at all True",
      "Slightly True",
      "Moderately True",
      "Quite True",
      "Very True",
      "Extremely True",
      "Absolutely True",
      "Completely True",
      "Mostly True",
      "Somewhat True",
    ];
    if (data.rating_direction === "REVERSE") {
      return labels[total - 1 - index] || `Point ${index + 1}`;
    }
    return labels[index] || `Point ${index + 1}`;
  };

  const updateLabel = (i: number, val: string) => {
    const newLabels = [...data.scaleLabels];
    newLabels[i] = val;
    onChange({ ...data, scaleLabels: newLabels });
  };

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Statement / Question
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder="Enter the statement to rate..."
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
            onBlur={updateScaleLabels}
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

      {/* Scale labels */}
      <div className="space-y-2">
        <Label>Scale Point Labels (left to right)</Label>
        <p className="text-xs text-slate-500">
          Each column in the rating scale. Candidate selects one point.
          {data.rating_direction === "REVERSE"
            ? " Reverse: rightmost point = highest score."
            : " Forward: leftmost point = highest score."}
        </p>
        <div
          className="grid gap-2"
          style={{ gridTemplateColumns: `repeat(${Math.min(scalePoints, 5)}, 1fr)` }}
        >
          {Array.from({ length: scalePoints }).map((_, i) => (
            <div key={i} className="space-y-1">
              <span className="text-xs text-slate-400">
                Point {i + 1} = {data.rating_direction === "REVERSE" ? i + 1 : scalePoints - i} pts
              </span>
              <Input
                value={data.scaleLabels[i] || ""}
                onChange={(e) => updateLabel(i, e.target.value)}
                placeholder={`Label ${i + 1}`}
                className="text-xs"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-3 text-sm font-medium text-slate-900">
          {data.question_text_1 || "(no statement)"}
        </p>
        <div className="flex items-center gap-2">
          {Array.from({ length: scalePoints }).map((_, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <button
                type="button"
                className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-300 text-xs font-medium text-slate-500 hover:border-primary-600 hover:text-primary-600"
              >
                {i + 1}
              </button>
              <span className="max-w-20 text-center text-xs text-slate-500">
                {data.scaleLabels[i] || `Point ${i + 1}`}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {data.rating_direction === "REVERSE"
            ? `Scoring: Point 1 = 1, Point ${scalePoints} = ${scalePoints}`
            : `Scoring: Point 1 = ${scalePoints}, Point ${scalePoints} = 1`}
        </p>
      </div>
    </div>
  );
}

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
        <Label>Items to Rank</Label>
        {data.options.map((opt, i) => (
          <div key={i} className="flex items-center gap-3 rounded-md border border-slate-200 p-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-medium text-slate-600">
              {i + 1}
            </span>
            <Input
              value={opt.text_value}
              onChange={(e) => updateOption(i, { ...opt, text_value: e.target.value })}
              placeholder="Enter item to rank..."
              className="flex-1 text-sm"
            />
            <button
              type="button"
              className="rounded px-2 py-1 text-xs text-danger hover:bg-danger-50"
              onClick={() => removeOption(i)}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addOption}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          + Add item
        </button>
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
      </div>
      <div className="space-y-2">
        <Label>Items (candidate ranks 1-N, then rates each on {scalePoints}-point scale)</Label>
        {data.options.map((opt, i) => (
          <div key={i} className="flex items-center gap-3 rounded-md border border-slate-200 p-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-medium text-slate-600">
              {i + 1}
            </span>
            <Input
              value={opt.text_value}
              onChange={(e) => updateOption(i, { ...opt, text_value: e.target.value })}
              placeholder="Enter item..."
              className="flex-1 text-sm"
            />
            <button
              type="button"
              className="rounded px-2 py-1 text-xs text-danger hover:bg-danger-50"
              onClick={() => removeOption(i)}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addOption}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          + Add item
        </button>
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
          Score per item = (total - rank + 1) × rating. Max = {data.options.length} × {scalePoints}{" "}
          = {data.options.length * scalePoints}
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
          <div key={i} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <Input
                  value={opt.text_value}
                  onChange={(e) => updateOption(i, { ...opt, text_value: e.target.value })}
                  placeholder="Enter option text..."
                  className="text-sm"
                />
              </div>
              <div className="w-28">
                <Label className="text-xs text-slate-500">Predefined score</Label>
                <Input
                  type="number"
                  value={opt.predefined_score}
                  onChange={(e) =>
                    updateOption(i, { ...opt, predefined_score: Number(e.target.value) })
                  }
                  className="text-sm"
                  step="0.5"
                />
              </div>
              <button
                type="button"
                className="rounded px-2 py-1 text-xs text-danger hover:bg-danger-50"
                onClick={() => removeOption(i)}
              >
                Remove
              </button>
            </div>
          </div>
        ))}
        {data.options.length < 2 && (
          <button
            type="button"
            onClick={addPair}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            + Add option pair
          </button>
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
            = predefined × rating.
          </p>
        )}
      </div>
    </div>
  );
}
