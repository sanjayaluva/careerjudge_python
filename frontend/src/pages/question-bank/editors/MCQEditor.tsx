/**
 * MCQ Editor — for question types 1a-1h
 * Handles: text/image options, single vs multiple correct, passage/image config, media,
 *          flash items for 1e (word flash) and 1f (image flash)
 */
import { Input, Label, MediaManager, RichText, WysiwygEditorLite } from "@/components/ui";
import { SCORING_TYPES } from "@/api/questionBank";
import { AddOptionButton, createEmptyOption, type FlashItemData, type OptionData } from "./shared";
import { FlashItemsEditor } from "./FlashItemsEditor";

interface MCQEditorProps {
  questionType: string;
  data: {
    question_text_1: string;
    question_text_2: string;
    scoring_type: string;
    passage_title: string;
    passage_body: string;
    display_duration_seconds: string;
    display_mode: "timed" | "unlimited";
    replay_mode: "permitted" | "not_permitted";
    option_layout: "1" | "2" | "3";
    imageUrl: string;
    audioUrl: string;
    videoUrl: string;
    options: OptionData[];
    isMultipleAnswer: boolean;
    flashItems: FlashItemData[];
    flashIntervalMs: string;
    flashDisplayCount: string;
    flashOrder: string;
    /** Number of sub-questions pooled under one media (SRS feedback C-CFG-1).
     *  1 = single question (default). >1 = multiple sub-questions sharing
     *  the same audio/video/passage/image. */
    sub_question_count?: number;
    /** Currently active sub-question tab (0-indexed). */
    active_sub_question?: number;
    /** Per-sub-question text — shown before options for each sub-question.
     * Separate from question_text_2 (main question's secondary text). */
    sub_question_texts?: string[];
  };
  onChange: (data: MCQEditorProps["data"]) => void;
}

export function MCQEditor({ questionType, data, onChange }: MCQEditorProps) {
  const isPassageType = questionType === "MCQ_PASSAGE_DISPLAY_MULTI";
  const isAudioType = questionType === "MCQ_AUDIO_MULTI";
  const isVideoType = questionType === "MCQ_VIDEO_MULTI";
  const isImageOptionType = questionType === "MCQ_TEXT_IMAGE_IMG_OPTIONS";
  const isWordFlashType = questionType === "MCQ_WORD_FLASH_MULTI";
  const isImageFlashType = questionType === "MCQ_IMAGE_FLASH_MULTI";
  const isFlashType = isWordFlashType || isImageFlashType;
  const flashItemType: "TEXT" | "IMAGE" = isImageFlashType ? "IMAGE" : "TEXT";
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
    // Tag new options with the active sub-question index (SRS feedback C-CFG-1)
    const sqi = data.active_sub_question ?? 0;
    onChange({
      ...data,
      options: [...data.options, createEmptyOption(data.options.length, "TEXT", sqi)],
    });
  };

  const removeOption = (index: number) => {
    onChange({ ...data, options: data.options.filter((_, i) => i !== index) });
  };

  const setCorrect = (index: number, checked: boolean) => {
    if (data.isMultipleAnswer) {
      // Multiple answers: toggle this option's correct flag
      updateOption(index, { ...data.options[index], is_correct: checked });
    } else {
      // Single answer: only one can be correct (radio behavior) — but only
      // within the same sub-question (SRS feedback C-CFG-1)
      const sqi = data.active_sub_question ?? 0;
      const newOptions = data.options.map((opt, i) => ({
        ...opt,
        is_correct:
          i === index
            ? checked
            : opt.sub_question_index === sqi
              ? false // clear other correct in same sub-question
              : opt.is_correct, // preserve other sub-questions' correct flags
      }));
      onChange({ ...data, options: newOptions });
    }
  };

  // Filter options to only those belonging to the active sub-question
  const activeSubQ = data.active_sub_question ?? 0;
  const visibleOptions = data.options.filter((o) => (o.sub_question_index ?? 0) === activeSubQ);

  // Per-sub-question text helpers — this is the text shown before options
  // for each sub-question. Separate from question_text_2 (main question's
  // secondary text shown after media).
  const subTexts = data.sub_question_texts ?? [];
  const getSubQuestionText = (sqi: number): string => subTexts[sqi] ?? "";
  const setSubQuestionText = (sqi: number, value: string) => {
    const newList = [...subTexts];
    while (newList.length <= sqi) newList.push("");
    newList[sqi] = value;
    onChange({ ...data, sub_question_texts: newList });
  };

  return (
    <div className="space-y-4">
      {/* Question text 1 — main instruction, shown above media.
          Shared across all sub-questions (not per-sub-question). */}
      <div>
        <Label htmlFor="qtext1" required>
          Question text (Text 1)
        </Label>
        <WysiwygEditorLite
          value={data.question_text_1}
          onChange={(html) => onChange({ ...data, question_text_1: html })}
          minHeight={80}
          placeholder="Enter the main question or instructions (shown above the media)…"
        />
      </div>

      {/* Question text 2 — main question's secondary text, shown BELOW media.
          Shared across all sub-questions (not per-sub-question).
          Per the review document: Text 1 → Media → Text 2 → Options. */}
      <div>
        <Label htmlFor="qtext2">Additional text (Text 2, optional)</Label>
        <WysiwygEditorLite
          value={data.question_text_2}
          onChange={(html) => onChange({ ...data, question_text_2: html })}
          minHeight={60}
          placeholder="Secondary text shown below the media (e.g. the actual question based on the audio/video/passage)…"
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
            <WysiwygEditorLite
              value={data.passage_body}
              onChange={(html) => onChange({ ...data, passage_body: html })}
              minHeight={160}
              placeholder="Enter the passage text. Use subtitle / list / bold formatting for lengthy passages…"
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
              disabled={data.display_mode === "unlimited"}
            />
          </div>
          <div>
            <Label htmlFor="display_mode">Display Mode</Label>
            <select
              id="display_mode"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              value={data.display_mode}
              onChange={(e) =>
                onChange({
                  ...data,
                  display_mode: e.target.value as "timed" | "unlimited",
                })
              }
            >
              <option value="timed">Timed — passage expires after duration, no replay</option>
              <option value="unlimited">
                Unlimited — passage stays visible until test taker moves on
              </option>
            </select>
          </div>
        </div>
      )}

      {/* Flash items (types 1e, 1f) */}
      {isFlashType && (
        <FlashItemsEditor
          items={data.flashItems}
          flashIntervalMs={data.flashIntervalMs}
          flashDisplayCount={data.flashDisplayCount}
          flashOrder={data.flashOrder}
          itemType={flashItemType}
          onChange={(flashData) =>
            onChange({
              ...data,
              flashItems: flashData.items,
              flashIntervalMs: flashData.flashIntervalMs,
              flashDisplayCount: flashData.flashDisplayCount,
              flashOrder: flashData.flashOrder,
            })
          }
        />
      )}

      {/* Audio/Video replay mode (SRS feedback Recommendation 2) */}
      {(isAudioType || isVideoType || isImageFlashType || isWordFlashType) && (
        <div>
          <Label htmlFor="replay_mode">Replay Mode</Label>
          <select
            id="replay_mode"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={data.replay_mode}
            onChange={(e) =>
              onChange({
                ...data,
                replay_mode: e.target.value as "permitted" | "not_permitted",
              })
            }
          >
            <option value="not_permitted">
              Not Permitted — one-time playback only (assessment mode)
            </option>
            <option value="permitted">Permitted — test taker can replay (training mode)</option>
          </select>
        </div>
      )}

      {/* Option layout (SRS feedback Common Issue 7) */}
      <div>
        <Label htmlFor="option_layout">Option Layout</Label>
        <select
          id="option_layout"
          className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
          value={data.option_layout}
          onChange={(e) =>
            onChange({
              ...data,
              option_layout: e.target.value as "1" | "2" | "3",
            })
          }
        >
          <option value="1">Single column</option>
          <option value="2">Two columns</option>
          <option value="3">Three columns</option>
        </select>
        <p className="mt-1 text-xs text-slate-500">
          Use multi-column layout when there are many options to avoid scrolling.
        </p>
      </div>

      {/* Multi-sub-question pooling (SRS feedback C-CFG-1).
          For audio/video/passage/image-display types, the author can pool
          multiple sub-questions under the same media. Each sub-question has
          its own Text 2 + options; the media is shared. */}
      {isMultiSubQuestion && (
        <div className="rounded-md border border-blue-200 bg-blue-50/50 p-3">
          <Label htmlFor="subq_count">Number of Sub-Questions (pooled under one media)</Label>
          <div className="mt-2 flex items-center gap-2">
            <input
              id="subq_count"
              type="number"
              min={1}
              max={10}
              value={data.sub_question_count ?? 1}
              onChange={(e) => {
                const n = Math.max(1, Math.min(10, Number(e.target.value) || 1));
                onChange({ ...data, sub_question_count: n });
              }}
              className="h-10 w-24 rounded-md border border-slate-200 bg-white px-3 text-sm"
            />
            <span className="text-xs text-slate-500">
              {data.sub_question_count && data.sub_question_count > 1
                ? `${data.sub_question_count} sub-questions share the same media above. Use the tabs below to edit each.`
                : "1 = single question (default). Increase to pool multiple questions under the same media."}
            </span>
          </div>
          {data.sub_question_count && data.sub_question_count > 1 && (
            <div className="mt-3">
              <Label className="text-xs">Active Sub-Question</Label>
              <div className="mt-1 flex flex-wrap gap-1">
                {Array.from({ length: data.sub_question_count }).map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => onChange({ ...data, active_sub_question: i })}
                    className={`h-8 w-8 rounded-md text-xs font-bold ${
                      (data.active_sub_question ?? 0) === i
                        ? "bg-primary-600 text-white"
                        : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                The Text 2 and options below belong to sub-question{" "}
                {(data.active_sub_question ?? 0) + 1}. Switch tabs to edit other sub-questions.
              </p>
            </div>
          )}
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

      {/* Per-sub-question text — shown before options for each sub-question.
          Only visible when sub_question_count > 1.
          Per the Multiple Questions Display Style spec: each sub-question has
          its own question text + option fields. This is SEPARATE from Text 2. */}
      {isMultiSubQuestion && (data.sub_question_count ?? 1) > 1 && (
        <div className="rounded-md border border-blue-200 bg-blue-50/30 p-3">
          <Label htmlFor="subq_text">
            Sub-Question {(data.active_sub_question ?? 0) + 1} Text
            <span className="ml-2 text-xs font-normal text-slate-500">
              (shown before the options for this sub-question)
            </span>
          </Label>
          <WysiwygEditorLite
            value={getSubQuestionText(data.active_sub_question ?? 0)}
            onChange={(html) => setSubQuestionText(data.active_sub_question ?? 0, html)}
            minHeight={60}
            placeholder="Enter the text for this sub-question (e.g. 'Which element in an atom is relatively more unstable?')…"
          />
        </div>
      )}

      {/* Response Options */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>Response Options</Label>
          <span className="text-xs text-slate-500">
            {visibleOptions.length} option{visibleOptions.length !== 1 ? "s" : ""}
            {isMultiSubQuestion && (data.sub_question_count ?? 1) > 1 && (
              <span className="ml-1 text-primary-600">
                (for sub-question {(data.active_sub_question ?? 0) + 1})
              </span>
            )}
          </span>
        </div>
        {visibleOptions.map((opt, vi) => {
          // Find the index in the full data.options array (for update/remove)
          const i = data.options.indexOf(opt);
          return (
            <div key={i} className="flex items-start gap-3 rounded-md border border-slate-200 p-3">
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-500">Option {vi + 1}</span>
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
          );
        })}
        <AddOptionButton onClick={addOption} label="Add option" />
      </div>

      {/* Preview — shows the delivery-time layout:
          Text 1 → Media → Text 2 → SubQ Text → Options */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
          {isMultiSubQuestion && (data.sub_question_count ?? 1) > 1 && (
            <span className="ml-2 font-normal text-slate-500">
              (Sub-question {(data.active_sub_question ?? 0) + 1} of {data.sub_question_count})
            </span>
          )}
        </p>
        <div className="space-y-2">
          {/* 1. Question Text 1 — shown above media */}
          {data.question_text_1 && (
            <RichText html={data.question_text_1} className="text-sm font-medium text-slate-900" />
          )}

          {/* 2. Media — passage, flash, image, audio, video */}
          {isFlashType && data.flashItems.length > 0 && (
            <div className="rounded border border-amber-300 bg-amber-50 p-2">
              <p className="mb-1 text-xs font-medium text-amber-700">
                Flash items ({data.flashIntervalMs || "?"}ms each · {data.flashDisplayCount || "?"}{" "}
                shown)
              </p>
              <div className="flex flex-wrap gap-1.5">
                {data.flashItems.map((item, i) => (
                  <div
                    key={i}
                    className="flex h-12 w-12 items-center justify-center rounded border border-slate-300 bg-white p-0.5"
                  >
                    {item.item_type === "IMAGE" && item.image_file ? (
                      <img
                        src={item.image_file}
                        alt={`Flash ${i + 1}`}
                        className="max-h-full max-w-full object-contain"
                      />
                    ) : (
                      <span className="text-center text-[10px] font-medium text-slate-700">
                        {item.text_value || `(${i + 1})`}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {isPassageType && (data.passage_title || data.passage_body) && (
            <div className="rounded border border-blue-300 bg-blue-50 p-2">
              <p className="mb-1 text-xs font-medium text-blue-700">
                Passage
                {data.display_duration_seconds && ` · ${data.display_duration_seconds}s display`}
              </p>
              {data.passage_title && (
                <p className="text-sm font-semibold text-slate-900">{data.passage_title}</p>
              )}
              {data.passage_body && (
                <RichText html={data.passage_body} className="mt-0.5 text-xs text-slate-700" />
              )}
            </div>
          )}

          {data.imageUrl && <img src={data.imageUrl} alt="Question" className="max-h-32 rounded" />}
          {data.audioUrl && <audio controls src={data.audioUrl} className="w-full" />}
          {data.videoUrl && (
            <video controls src={data.videoUrl} className="max-h-32 w-full rounded" />
          )}

          {/* 3. Question Text 2 — shown below media */}
          {data.question_text_2 && (
            <RichText html={data.question_text_2} className="text-sm text-slate-600" />
          )}

          {/* 4. Sub-question text — shown before options (multi-sub-question only) */}
          {isMultiSubQuestion &&
            (data.sub_question_count ?? 1) > 1 &&
            getSubQuestionText(data.active_sub_question ?? 0) && (
              <RichText
                html={getSubQuestionText(data.active_sub_question ?? 0)}
                className="text-sm font-medium text-slate-900"
              />
            )}

          {/* 5. Options */}
          {visibleOptions.length > 0 && (
            <div className="space-y-1.5">
              {visibleOptions.map((opt, i) => (
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
