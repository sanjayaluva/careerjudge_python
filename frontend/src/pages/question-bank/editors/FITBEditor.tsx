/**
 * FITB Editor — for question types 2a-2d
 * Handles: single/multiple fields, correct answers (up to 5 per field),
 * fuzzy match config, flash items + flash config for 2c/2d
 */
import { Input, Label } from "@/components/ui";
import { SCORING_TYPES } from "@/api/questionBank";
import {
  AddOptionButton,
  OptionRow,
  createEmptyOption,
  type FlashItemData,
  type OptionData,
} from "./shared";
import { FlashItemsEditor } from "./FlashItemsEditor";

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
    flashItems: FlashItemData[];
  };
  onChange: (data: FITBEditorProps["data"]) => void;
}

export function FITBEditor({ questionType, data, onChange }: FITBEditorProps) {
  const isMultiField = questionType === "FITB_MULTI_FIELD";
  const isWordFlashType = questionType === "FITB_WORD_FLASH_MULTI";
  const isImageFlashType = questionType === "FITB_IMAGE_FLASH_MULTI";
  const isFlashType = isWordFlashType || isImageFlashType;
  const flashItemType: "TEXT" | "IMAGE" = isImageFlashType ? "IMAGE" : "TEXT";
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
      {/* Flash items preview — shown above question text for flash types (2c, 2d).
          At delivery time, flash items display FIRST, then the question appears. */}
      {isFlashType && data.flashItems.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50/50 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Flash Items (displayed first, then question)
          </p>
          <div className="flex flex-wrap gap-2">
            {data.flashItems.map((item, i) => (
              <div
                key={i}
                className="flex h-16 w-16 items-center justify-center rounded border border-slate-300 bg-white p-1"
              >
                {item.item_type === "IMAGE" && item.image_file ? (
                  <img
                    src={item.image_file}
                    alt={`Flash ${i + 1}`}
                    className="max-h-full max-w-full object-contain"
                  />
                ) : (
                  <span className="text-center text-xs font-medium text-slate-700">
                    {item.text_value || `(empty ${i + 1})`}
                  </span>
                )}
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {data.flashItems.length} items · {data.flash_interval_ms || "?"} ms each ·{" "}
            {data.flash_display_count || "?"} shown
          </p>
        </div>
      )}

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

      {/* Flash items + config (types 2c, 2d) */}
      {isFlashType && (
        <FlashItemsEditor
          items={data.flashItems}
          flashIntervalMs={data.flash_interval_ms}
          flashDisplayCount={data.flash_display_count}
          itemType={flashItemType}
          onChange={(flashData) =>
            onChange({
              ...data,
              flashItems: flashData.items,
              flash_interval_ms: flashData.flashIntervalMs,
              flash_display_count: flashData.flashDisplayCount,
            })
          }
        />
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
