/**
 * MCQ Editor — for question types 1a-1h
 * Handles: text/image options, correct answer selection, passage/image config
 */
import { Input, Label } from "@/components/ui";
import { SCORING_TYPES } from "@/api/questionBank";
import { AddOptionButton, OptionRow, createEmptyOption, type OptionData } from "./shared";

interface MCQEditorProps {
  questionType: string;
  data: {
    question_text_1: string;
    question_text_2: string;
    scoring_type: string;
    passage_title: string;
    passage_body: string;
    display_duration_seconds: string;
    options: OptionData[];
  };
  onChange: (data: MCQEditorProps["data"]) => void;
}

export function MCQEditor({ questionType, data, onChange }: MCQEditorProps) {
  const isPassageType = questionType === "MCQ_PASSAGE_DISPLAY_MULTI";
  const isMultiSubQuestion = [
    "MCQ_AUDIO_MULTI",
    "MCQ_VIDEO_MULTI",
    "MCQ_WORD_FLASH_MULTI",
    "MCQ_IMAGE_FLASH_MULTI",
    "MCQ_PASSAGE_DISPLAY_MULTI",
    "MCQ_IMAGE_DISPLAY_MULTI",
  ].includes(questionType);

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
      {/* Question text */}
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
          placeholder="Enter the main question..."
        />
      </div>

      {/* Additional text (optional) */}
      <div>
        <Label htmlFor="qtext2">Additional text (optional)</Label>
        <textarea
          id="qtext2"
          rows={2}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_2}
          onChange={(e) => onChange({ ...data, question_text_2: e.target.value })}
        />
      </div>

      {/* Passage config (type 1g only) */}
      {isPassageType && (
        <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3">
          <p className="text-sm font-medium text-slate-700">Passage Configuration</p>
          <div>
            <Label htmlFor="ptitle">Passage title</Label>
            <Input
              id="ptitle"
              value={data.passage_title}
              onChange={(e) => onChange({ ...data, passage_title: e.target.value })}
              placeholder="Passage heading..."
            />
          </div>
          <div>
            <Label htmlFor="pbody">Passage body</Label>
            <textarea
              id="pbody"
              rows={5}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={data.passage_body}
              onChange={(e) => onChange({ ...data, passage_body: e.target.value })}
              placeholder="Enter the passage text that candidates will read..."
            />
          </div>
          <div>
            <Label htmlFor="dduration">Display duration (seconds)</Label>
            <Input
              id="dduration"
              type="number"
              value={data.display_duration_seconds}
              onChange={(e) => onChange({ ...data, display_duration_seconds: e.target.value })}
              placeholder="How long the passage displays before questions appear"
            />
          </div>
        </div>
      )}

      {/* Scoring type */}
      <div>
        <Label htmlFor="stype">Scoring type</Label>
        <select
          id="stype"
          className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.scoring_type}
          onChange={(e) => onChange({ ...data, scoring_type: e.target.value })}
        >
          {SCORING_TYPES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Response Options */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>Response Options</Label>
          <span className="text-xs text-slate-500">
            {data.options.length} option{data.options.length !== 1 ? "s" : ""}
            {isMultiSubQuestion && " (shared across sub-questions)"}
          </span>
        </div>
        {data.options.map((opt, i) => (
          <OptionRow
            key={i}
            option={opt}
            index={i}
            onChange={updateOption}
            onRemove={removeOption}
            showCorrect
          />
        ))}
        <AddOptionButton onClick={addOption} label="Add option" />
      </div>

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <div className="space-y-2">
          {data.question_text_1 && (
            <p className="text-sm font-medium text-slate-900">{data.question_text_1}</p>
          )}
          {data.options.length > 0 && (
            <div className="space-y-1.5">
              {data.options.map((opt, i) => (
                <label
                  key={i}
                  className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                >
                  <input
                    type="radio"
                    name="mcq-preview"
                    defaultChecked={opt.is_correct}
                    className="h-4 w-4 border-slate-300 text-primary-600"
                    readOnly
                  />
                  <span
                    className={opt.is_correct ? "font-medium text-slate-900" : "text-slate-700"}
                  >
                    {opt.text_value || `(empty option ${i + 1})`}
                  </span>
                  {opt.is_correct && (
                    <span className="ml-auto text-xs text-success-600">✓ correct</span>
                  )}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
