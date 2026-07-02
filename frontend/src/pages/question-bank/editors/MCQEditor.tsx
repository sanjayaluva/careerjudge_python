/**
 * MCQ Editor — for question types 1a-1h
 * Handles: text/image options, single vs multiple correct, passage/image config, media
 */
import { Input, Label, MediaManager } from "@/components/ui";
import { SCORING_TYPES } from "@/api/questionBank";
import { AddOptionButton, createEmptyOption, type OptionData } from "./shared";

interface MCQEditorProps {
  questionType: string;
  data: {
    question_text_1: string;
    question_text_2: string;
    scoring_type: string;
    passage_title: string;
    passage_body: string;
    display_duration_seconds: string;
    imageUrl: string;
    audioUrl: string;
    videoUrl: string;
    options: OptionData[];
    isMultipleAnswer: boolean;
  };
  onChange: (data: MCQEditorProps["data"]) => void;
}

export function MCQEditor({ questionType, data, onChange }: MCQEditorProps) {
  const isPassageType = questionType === "MCQ_PASSAGE_DISPLAY_MULTI";
  const isAudioType = questionType === "MCQ_AUDIO_MULTI";
  const isVideoType = questionType === "MCQ_VIDEO_MULTI";
  const isImageOptionType = questionType === "MCQ_TEXT_IMAGE_IMG_OPTIONS";
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
    onChange({ ...data, options: [...data.options, createEmptyOption(data.options.length)] });
  };

  const removeOption = (index: number) => {
    onChange({ ...data, options: data.options.filter((_, i) => i !== index) });
  };

  const setCorrect = (index: number, checked: boolean) => {
    if (data.isMultipleAnswer) {
      // Multiple answers: toggle this option's correct flag
      updateOption(index, { ...data.options[index], is_correct: checked });
    } else {
      // Single answer: only one can be correct (radio behavior)
      const newOptions = data.options.map((opt, i) => ({
        ...opt,
        is_correct: i === index,
      }));
      onChange({ ...data, options: newOptions });
    }
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

      {/* Additional text */}
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

      {/* Question image (for types with image stimulus) */}
      {(questionType === "MCQ_TEXT_IMAGE" ||
        questionType === "MCQ_TEXT_IMAGE_IMG_OPTIONS" ||
        questionType === "MCQ_IMAGE_DISPLAY_MULTI") && (
        <MediaManager
          label="Question image (optional)"
          accept="image/*"
          modes={["upload", "url", "gallery"]}
          value={data.imageUrl}
          onChange={(url) => onChange({ ...data, imageUrl: url })}
          previewType="image"
          helpText="Image shown alongside the question text."
        />
      )}

      {/* Audio (for type 1c) */}
      {isAudioType && (
        <MediaManager
          label="Audio file"
          accept="audio/*"
          modes={["upload", "url", "gallery"]}
          value={data.audioUrl}
          onChange={(url) => onChange({ ...data, audioUrl: url })}
          previewType="audio"
          helpText="Audio plays once (no replay). Sub-questions appear after audio."
        />
      )}

      {/* Video (for type 1d) */}
      {isVideoType && (
        <MediaManager
          label="Video file"
          accept="video/*"
          modes={["upload", "url", "gallery"]}
          value={data.videoUrl}
          onChange={(url) => onChange({ ...data, videoUrl: url })}
          previewType="video"
          helpText="Video plays once (no replay). Sub-questions appear after video."
        />
      )}

      {/* Passage config (type 1g) */}
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
              placeholder="Enter the passage text..."
            />
          </div>
          <div>
            <Label htmlFor="dduration">Display duration (seconds)</Label>
            <Input
              id="dduration"
              type="number"
              value={data.display_duration_seconds}
              onChange={(e) => onChange({ ...data, display_duration_seconds: e.target.value })}
              placeholder="How long the passage displays"
            />
          </div>
        </div>
      )}

      {/* Answer type toggle */}
      <div className="flex items-center gap-4">
        <Label>Answer type:</Label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="radio"
            name="answer-type"
            checked={!data.isMultipleAnswer}
            onChange={() => {
              // Switching to single answer: clear all but first correct
              const newOptions = data.options.map((opt, i) => ({
                ...opt,
                is_correct: i === 0 ? opt.is_correct : false,
              }));
              onChange({ ...data, isMultipleAnswer: false, options: newOptions });
            }}
            className="h-4 w-4 border-slate-300 text-primary-600"
          />
          Single answer
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="radio"
            name="answer-type"
            checked={data.isMultipleAnswer}
            onChange={() => onChange({ ...data, isMultipleAnswer: true })}
            className="h-4 w-4 border-slate-300 text-primary-600"
          />
          Multiple answers
        </label>
      </div>

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
          <div key={i} className="flex items-start gap-3 rounded-md border border-slate-200 p-3">
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500">Option {i + 1}</span>
                {data.isMultipleAnswer ? (
                  <label className="flex items-center gap-1 text-xs text-slate-600">
                    <input
                      type="checkbox"
                      checked={opt.is_correct}
                      onChange={(e) => setCorrect(i, e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-primary-600"
                    />
                    Correct
                  </label>
                ) : (
                  <label className="flex items-center gap-1 text-xs text-slate-600">
                    <input
                      type="radio"
                      name="mcq-correct"
                      checked={opt.is_correct}
                      onChange={() => setCorrect(i, true)}
                      className="h-4 w-4 border-slate-300 text-primary-600"
                    />
                    Correct answer
                  </label>
                )}
              </div>
              <Input
                value={opt.text_value}
                onChange={(e) => updateOption(i, { ...opt, text_value: e.target.value })}
                placeholder="Enter option text..."
                className="text-sm"
              />
              {/* Image option for type 1b */}
              {isImageOptionType && (
                <MediaManager
                  label={`Option ${i + 1} image`}
                  accept="image/*"
                  modes={["upload", "url", "gallery"]}
                  value={opt.image_file || ""}
                  onChange={(url) => updateOption(i, { ...opt, image_file: url })}
                  previewType="image"
                />
              )}
            </div>
            <button
              type="button"
              className="rounded px-2 py-1 text-xs text-danger hover:bg-danger-50"
              onClick={() => removeOption(i)}
            >
              Remove
            </button>
          </div>
        ))}
        <AddOptionButton onClick={addOption} label="Add option" />
      </div>

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <div className="space-y-2">
          {data.imageUrl && <img src={data.imageUrl} alt="Question" className="max-h-32 rounded" />}
          {data.question_text_1 && (
            <p className="text-sm font-medium text-slate-900">{data.question_text_1}</p>
          )}
          {data.audioUrl && <audio controls src={data.audioUrl} className="w-full" />}
          {data.videoUrl && (
            <video controls src={data.videoUrl} className="max-h-32 w-full rounded" />
          )}
          {data.options.length > 0 && (
            <div className="space-y-1.5">
              {data.options.map((opt, i) => (
                <label
                  key={i}
                  className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                >
                  <input
                    type={data.isMultipleAnswer ? "checkbox" : "radio"}
                    name="mcq-preview"
                    defaultChecked={opt.is_correct}
                    className="h-4 w-4 border-slate-300 text-primary-600"
                    readOnly
                  />
                  {opt.image_file && (
                    <img src={opt.image_file} alt="" className="h-8 w-8 rounded" />
                  )}
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
