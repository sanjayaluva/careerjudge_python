/**
 * FITB Editor — for question types 2a-2d
 * Handles: single/multiple fields, correct answers (up to 5 per field),
 * fuzzy match config, flash config for 2c/2d
 */
import { Input, Label } from "@/components/ui";
import { SCORING_TYPES } from "@/api/questionBank";
import { AddOptionButton, OptionRow, createEmptyOption, type OptionData } from "./shared";

interface FITBEditorProps {
  questionType: string;
  data: {
    question_text_1: string;
    scoring_type: string;
    case_sensitive: boolean;
    pct_match_threshold: string;
    flash_interval_ms: string;
    flash_display_count: string;
    options: OptionData[];
  };
  onChange: (data: FITBEditorProps["data"]) => void;
}

export function FITBEditor({ questionType, data, onChange }: FITBEditorProps) {
  const isMultiField = questionType === "FITB_MULTI_FIELD";
  const isFlashType =
    questionType === "FITB_WORD_FLASH_MULTI" || questionType === "FITB_IMAGE_FLASH_MULTI";
  const isFuzzy = data.scoring_type === "BINARY_FUZZY";

  const updateOption = (index: number, option: OptionData) => {
    const newOptions = [...data.options];
    newOptions[index] = option;
    onChange({ ...data, options: newOptions });
  };

  const addOption = () => {
    onChange({
      ...data,
      options: [...data.options, createEmptyOption(data.options.length)],
    });
  };

  const removeOption = (index: number) => {
    onChange({
      ...data,
      options: data.options.filter((_, i) => i !== index),
    });
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
          placeholder="Enter the question. Use ____ for blank(s)..."
        />
      </div>

      {/* Flash config (types 2c, 2d) */}
      {isFlashType && (
        <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3">
          <p className="text-sm font-medium text-slate-700">Flash Configuration</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="flashint">Flash interval (ms)</Label>
              <Input
                id="flashint"
                type="number"
                value={data.flash_interval_ms}
                onChange={(e) => onChange({ ...data, flash_interval_ms: e.target.value })}
                placeholder="e.g. 500"
              />
            </div>
            <div>
              <Label htmlFor="flashcount">Flash display count</Label>
              <Input
                id="flashcount"
                type="number"
                value={data.flash_display_count}
                onChange={(e) => onChange({ ...data, flash_display_count: e.target.value })}
                placeholder="e.g. 10"
              />
            </div>
          </div>
        </div>
      )}

      {/* Scoring config */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="sm:col-span-3">
          <Label htmlFor="stype">Scoring type</Label>
          <select
            id="stype"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={data.scoring_type}
            onChange={(e) => onChange({ ...data, scoring_type: e.target.value })}
          >
            <option value="BINARY">Binary (exact match)</option>
            <option value="BINARY_FUZZY">Binary with Fuzzy Match</option>
            <option value="PARTIAL">Partial Credit (multi-field)</option>
          </select>
          {(() => {
            const selected = SCORING_TYPES.find((s) => s.value === data.scoring_type);
            return selected?.description ? (
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                <span className="font-medium text-slate-700">How it works: </span>
                {selected.description}
              </p>
            ) : null;
          })()}
        </div>
        <div>
          <Label htmlFor="casesens">Case sensitive</Label>
          <select
            id="casesens"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={data.case_sensitive ? "true" : "false"}
            onChange={(e) => onChange({ ...data, case_sensitive: e.target.value === "true" })}
          >
            <option value="false">No (case insensitive)</option>
            <option value="true">Yes (case sensitive)</option>
          </select>
        </div>
        {isFuzzy && (
          <div>
            <Label htmlFor="pctmatch">Match threshold (%)</Label>
            <Input
              id="pctmatch"
              type="number"
              value={data.pct_match_threshold}
              onChange={(e) => onChange({ ...data, pct_match_threshold: e.target.value })}
              placeholder="e.g. 80"
            />
          </div>
        )}
      </div>

      {/* Answer fields */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>{isMultiField ? "Answer Fields (one per blank)" : "Correct Answer(s)"}</Label>
          <span className="text-xs text-slate-500">Up to 5 correct answers per field</span>
        </div>
        {data.options.map((opt, i) => (
          <OptionRow
            key={i}
            option={opt}
            index={i}
            onChange={updateOption}
            onRemove={removeOption}
            showCorrect={false}
            correctAnswerMode
            label={isMultiField ? `Field ${i + 1}` : "Answer"}
          />
        ))}
        {isMultiField && <AddOptionButton onClick={addOption} label="Add field" />}
        {!isMultiField && data.options.length === 0 && (
          <AddOptionButton onClick={addOption} label="Add answer" />
        )}
      </div>

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="text-sm font-medium text-slate-900">
          {data.question_text_1 || "(no question text)"}
        </p>
        <div className="mt-2 space-y-1">
          {data.options.map((opt, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
              <span className="font-medium">{isMultiField ? `Field ${i + 1}:` : "Accepted:"}</span>
              <span>
                {opt.correct_answers.map((ca) => ca.answer_text).join(", ") || "(no answers set)"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
