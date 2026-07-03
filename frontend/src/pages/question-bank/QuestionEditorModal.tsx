/**
 * Question Editor Modal — dynamic question creation/editing with type-specific editors.
 * Renders the correct editor (MCQ, FITB, Match, Grid, Hotspot, Rank, Rating, Forced-Choice)
 * based on the selected question type.
 *
 * Supports both CREATE and EDIT modes:
 *   <QuestionEditorModal open={true} onClose={...} />                              // create
 *   <QuestionEditorModal open={true} onClose={...} questionId={123} />             // edit
 *
 * When `questionId` is provided, the modal fetches the full question detail (including
 * existing options, media, hotspots, flash items) and prefills the form. On submit, it
 * PATCHes the question instead of POSTing, then re-syncs child resources (options/media/
 * hotspots) via the same bulk endpoints used during create.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Alert, AlertDescription, Button, Label, Modal, Spinner } from "@/components/ui";
import {
  bulkSaveOptions,
  createHotspot,
  createMediaFile,
  createQuestion,
  deleteHotspot,
  deleteMediaFile,
  DIFFICULTY_LEVELS,
  QUESTION_TYPES,
  retrieveQuestion,
  updateQuestion,
  type QuestionDetail,
} from "@/api/questionBank";
import { extractApiError } from "@/api/client";
import type { OptionData, MatchPairData } from "./editors/shared";
import { MCQEditor } from "./editors/MCQEditor";
import { FITBEditor } from "./editors/FITBEditor";
import { MatchEditor } from "./editors/MatchEditor";
import { GridEditor } from "./editors/GridEditor";
import { HotspotEditor } from "./editors/HotspotEditor";
import {
  RankEditor,
  RankRateEditor,
  RatingEditor,
  ForcedChoiceEditor,
} from "./editors/PsychometricEditors";

const QB_KEY = ["question-bank", "questions"];

interface QuestionEditorModalProps {
  open: boolean;
  onClose: () => void;
  /** When provided, the modal operates in EDIT mode for this question. */
  questionId?: number | null;
}

export function QuestionEditorModal({ open, onClose, questionId }: QuestionEditorModalProps) {
  const queryClient = useQueryClient();
  const isEditMode = Boolean(questionId);
  const [questionType, setQuestionType] = useState("MCQ_TEXT_IMAGE");
  const [difficulty, setDifficulty] = useState("");
  const [cognitiveLevel, setCognitiveLevel] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Shared question data
  const [questionText1, setQuestionText1] = useState("");
  const [questionText2, setQuestionText2] = useState("");
  const [scoringType, setScoringType] = useState("BINARY");
  const [passageTitle, setPassageTitle] = useState("");
  const [passageBody, setPassageBody] = useState("");
  const [displayDuration, setDisplayDuration] = useState("");
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [pctThreshold, setPctThreshold] = useState("");
  const [flashInterval, setFlashInterval] = useState("");
  const [flashCount, setFlashCount] = useState("");
  const [gridRows, setGridRows] = useState("3");
  const [gridCols, setGridCols] = useState("3");
  const [ratingScalePoints, setRatingScalePoints] = useState("5");
  const [ratingDirection, setRatingDirection] = useState("FORWARD");
  const [imageUrl, setImageUrl] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [options, setOptions] = useState<OptionData[]>([]);
  const [pairs, setPairs] = useState<MatchPairData[]>([]);
  const [rowLabels, setRowLabels] = useState<string[]>([]);
  const [colLabels, setColLabels] = useState<string[]>([]);
  const [correctCells, setCorrectCells] = useState<boolean[][]>([]);
  const [isMultipleAnswer, setIsMultipleAnswer] = useState(false);
  const [scaleLabels, setScaleLabels] = useState<string[]>([]);
  const [hotspotAreas, setHotspotAreas] = useState<
    {
      x: number;
      y: number;
      width_px: number;
      height_px: number;
      area_size_code: string;
      sub_question_index?: number;
    }[]
  >([]);

  const resetForm = () => {
    setQuestionType("MCQ_TEXT_IMAGE");
    setDifficulty("");
    setCognitiveLevel("");
    setQuestionText1("");
    setQuestionText2("");
    setScoringType("BINARY");
    setPassageTitle("");
    setPassageBody("");
    setDisplayDuration("");
    setCaseSensitive(false);
    setPctThreshold("");
    setFlashInterval("");
    setFlashCount("");
    setGridRows("3");
    setGridCols("3");
    setRatingScalePoints("5");
    setRatingDirection("FORWARD");
    setImageUrl("");
    setAudioUrl("");
    setVideoUrl("");
    setOptions([]);
    setPairs([]);
    setRowLabels([]);
    setColLabels([]);
    setCorrectCells([]);
    setIsMultipleAnswer(false);
    setScaleLabels([]);
    setHotspotAreas([]);
    setError(null);
  };

  // Populate the form from an existing QuestionDetail (edit mode).
  // Maps every persisted field back into the local component state so the
  // user sees the exact data they previously saved.
  const populateForm = (q: QuestionDetail) => {
    setQuestionType(q.question_type);
    setDifficulty(q.difficulty_level ?? "");
    setCognitiveLevel(q.cognitive_level ?? "");
    setQuestionText1(q.question_text_1 ?? "");
    setQuestionText2(q.question_text_2 ?? "");
    setScoringType(q.scoring_type ?? "BINARY");
    setPassageTitle(q.passage_title ?? "");
    setPassageBody(q.passage_body ?? "");
    setDisplayDuration(
      q.display_duration_seconds != null ? String(q.display_duration_seconds) : "",
    );
    setCaseSensitive(Boolean(q.case_sensitive));
    setPctThreshold(q.pct_match_threshold != null ? String(q.pct_match_threshold) : "");
    setFlashInterval(q.flash_interval_ms != null ? String(q.flash_interval_ms) : "");
    setFlashCount(q.flash_display_count != null ? String(q.flash_display_count) : "");
    setGridRows(q.grid_rows != null ? String(q.grid_rows) : "3");
    setGridCols(q.grid_cols != null ? String(q.grid_cols) : "3");
    setRatingScalePoints(q.rating_scale_points != null ? String(q.rating_scale_points) : "5");
    setRatingDirection(q.rating_direction ?? "FORWARD");
    setImageUrl(q.image ?? "");
    // Audio/video are stored as MediaFile records (media_type AUDIO/VIDEO).
    setAudioUrl(q.media_files.find((m) => m.media_type === "AUDIO")?.file ?? "");
    setVideoUrl(q.media_files.find((m) => m.media_type === "VIDEO")?.file ?? "");

    // Restore options. The persisted options include TEXT/MATCH_A/MATCH_B/
    // DRAG_POOL/RANK/FORCED_CHOICE — we keep TEXT and IMAGE for MCQ/FITB and
    // rebuild match pairs from MATCH_A/MATCH_B pairs.
    const textOptions: OptionData[] = q.options
      .filter((o) => o.option_type === "TEXT" || o.option_type === "IMAGE")
      .map((o) => ({
        sub_question_index: o.sub_question_index,
        option_type: o.option_type,
        label: o.label ?? "",
        text_value: o.text_value ?? "",
        image_file: o.image_file ?? "",
        is_correct: o.is_correct,
        match_pair_id: o.match_pair_id,
        predefined_score: o.predefined_score ?? 1,
        order: o.order,
        correct_answers: (o.correct_answers ?? []).map((ca) => ({
          answer_text: ca.answer_text,
          order: ca.order,
        })),
      }));
    setOptions(textOptions);

    // Rebuild match pairs from MATCH_A / MATCH_B option pairs (matched by match_pair_id).
    const matchA = q.options.filter((o) => o.option_type === "MATCH_A");
    const matchB = q.options.filter((o) => o.option_type === "MATCH_B");
    if (matchA.length > 0 && matchB.length > 0) {
      const rebuiltPairs: MatchPairData[] = matchA.map((a, i) => {
        const b = matchB.find((x) => x.match_pair_id === a.match_pair_id);
        const pairId = a.match_pair_id ?? i + 1;
        return {
          pairId,
          groupA: {
            id: a.id,
            sub_question_index: a.sub_question_index,
            option_type: "MATCH_A",
            label: a.label ?? "",
            text_value: a.text_value ?? "",
            image_file: a.image_file ?? null,
            is_correct: a.is_correct,
            match_pair_id: a.match_pair_id,
            predefined_score: a.predefined_score ?? 1,
            order: a.order,
            correct_answers: [],
          },
          groupB: {
            id: b?.id,
            sub_question_index: b?.sub_question_index ?? 0,
            option_type: "MATCH_B",
            label: b?.label ?? "",
            text_value: b?.text_value ?? "",
            image_file: b?.image_file ?? null,
            is_correct: b?.is_correct ?? false,
            match_pair_id: b?.match_pair_id ?? pairId,
            predefined_score: b?.predefined_score ?? 1,
            order: b?.order ?? i * 2 + 1,
            correct_answers: [],
          },
        };
      });
      setPairs(rebuiltPairs);
    } else {
      setPairs([]);
    }

    setRowLabels([]);
    setColLabels([]);
    setCorrectCells([]);
    setIsMultipleAnswer(textOptions.filter((o) => o.is_correct).length > 1);
    setScaleLabels(
      textOptions
        .filter((o) => o.label?.startsWith("Point "))
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        .map((o) => o.text_value ?? ""),
    );
    setHotspotAreas(
      q.hotspot_areas.map((h) => ({
        x: h.x,
        y: h.y,
        width_px: h.width_px,
        height_px: h.height_px,
        area_size_code: h.area_size_code ?? "",
        sub_question_index: h.sub_question_index,
      })),
    );
    setError(null);
  };

  // Fetch the question detail when opening in edit mode.
  // The query is only enabled when both `open` and `questionId` are truthy.
  // Note: TanStack Query v5 removed `onSuccess` — we use a useEffect below
  // to call populateForm when the data arrives.
  const { data: existingQuestion, isFetching: isLoadingQuestion } = useQuery({
    queryKey: ["question-bank", "question", questionId],
    queryFn: () => retrieveQuestion(questionId as number),
    enabled: Boolean(open && questionId),
    staleTime: 0, // always refetch on open so we have fresh data
  });

  // When the fetched question data changes (e.g. on first load or refetch),
  // populate the form fields. Using useEffect instead of onSuccess because
  // TanStack Query v5 removed the onSuccess callback.
  useEffect(() => {
    if (existingQuestion && isEditMode) {
      populateForm(existingQuestion);
    }
  }, [existingQuestion, isEditMode]);

  // Reset the form when the modal closes (so the next open starts clean).
  // For edit mode, populateForm runs via the useEffect above when data arrives.
  useEffect(() => {
    if (!open) {
      // Small delay so the close animation doesn't show a half-empty form.
      const t = setTimeout(() => resetForm(), 100);
      return () => clearTimeout(t);
    }
    // When opening in CREATE mode, ensure the form is fresh.
    // In EDIT mode, populateForm runs via the useEffect above.
    if (open && !questionId) {
      resetForm();
    }
  }, [open, questionId]);

  const mutation = useMutation({
    mutationFn: async (params: {
      payload: Record<string, unknown>;
      opts: typeof options;
      prs: typeof pairs;
      img?: string;
      aud?: string;
      vid?: string;
      hotspots?: {
        x: number;
        y: number;
        width_px: number;
        height_px: number;
        area_size_code?: string;
        sub_question_index?: number;
      }[];
      gridCorrectCells?: { row: number; col: number; rowLabel: string; colLabel: string }[];
      scaleLabels?: string[];
    }) => {
      const { payload, opts, prs, img, aud, vid, hotspots, gridCorrectCells, scaleLabels } = params;

      // 1a. CREATE or UPDATE the question (with image URL if set).
      // For edit mode, PATCH the existing question; for create mode, POST a new one.
      if (img) payload.image = img;
      const question = isEditMode
        ? await updateQuestion(questionId as number, payload)
        : await createQuestion(payload);

      // 1b. In edit mode, also delete existing media files and hotspots before
      // recreating them (since they don't have a bulk-sync endpoint like options).
      // The bulkSaveOptions call below handles create/update/delete for options.
      if (isEditMode) {
        // Fetch current question detail to get existing media/hotspot IDs.
        const current = await retrieveQuestion(questionId as number);
        // Delete all existing media files (audio/video) — they'll be recreated below.
        for (const m of current.media_files) {
          await deleteMediaFile(questionId as number, m.id);
        }
        // Delete all existing hotspot areas — they'll be recreated below.
        for (const h of current.hotspot_areas) {
          await deleteHotspot(questionId as number, h.id);
        }
      }

      // 2. Save audio/video as MediaFile records (create new ones)
      if (aud) await createMediaFile(question.id, { media_type: "AUDIO", file: aud });
      if (vid) await createMediaFile(question.id, { media_type: "VIDEO", file: vid });

      // 3. Save options (includes correct_answers for FITB).
      // bulkSaveOptions syncs create/update/delete in one request — works for
      // both create and edit modes.
      if (opts.length > 0) {
        const optionsPayload = opts.map((opt, i) => ({
          sub_question_index: opt.sub_question_index,
          option_type: opt.option_type,
          label: opt.label,
          text_value: opt.text_value,
          image_file: opt.image_file,
          is_correct: opt.is_correct,
          match_pair_id: opt.match_pair_id,
          predefined_score: opt.predefined_score,
          order: i,
          correct_answers: opt.correct_answers?.map((ca) => ({
            answer_text: ca.answer_text,
            order: ca.order,
          })),
        }));
        await bulkSaveOptions(question.id, optionsPayload);
      }

      // 4. Save match pairs
      if (prs.length > 0) {
        const pairOptions: Record<string, unknown>[] = [];
        prs.forEach((pair, i) => {
          pairOptions.push({
            sub_question_index: 0,
            option_type: "MATCH_A",
            text_value: pair.groupA.text_value,
            match_pair_id: pair.pairId,
            is_correct: false,
            predefined_score: 1.0,
            order: i * 2,
          });
          pairOptions.push({
            sub_question_index: 0,
            option_type: "MATCH_B",
            text_value: pair.groupB.text_value,
            match_pair_id: pair.pairId,
            is_correct: false,
            predefined_score: 1.0,
            order: i * 2 + 1,
          });
        });
        await bulkSaveOptions(question.id, pairOptions);
      }

      // 5. Save grid correct cells as options
      if (gridCorrectCells && gridCorrectCells.length > 0) {
        const gridOptions = gridCorrectCells.map((cell, i) => ({
          sub_question_index: 0,
          option_type: "DRAG_POOL",
          label: `${cell.rowLabel} → ${cell.colLabel}`,
          text_value: `${cell.rowLabel} → ${cell.colLabel}`,
          is_correct: true,
          predefined_score: 1.0,
          order: i,
        }));
        await bulkSaveOptions(question.id, gridOptions);
      }

      // 6. Save rating scale labels as options
      if (scaleLabels && scaleLabels.length > 0) {
        const ratingOptions = scaleLabels.map((label, i) => ({
          sub_question_index: 0,
          option_type: "TEXT",
          label: `Point ${i + 1}`,
          text_value: label,
          is_correct: false,
          predefined_score: 1.0,
          order: i,
        }));
        await bulkSaveOptions(question.id, ratingOptions);
      }

      // 7. Save hotspot areas (create new ones — old ones already deleted above if editing)
      if (hotspots && hotspots.length > 0) {
        for (const hs of hotspots) {
          await createHotspot(question.id, hs);
        }
      }

      return question;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
      // Also invalidate the question detail query so a re-open shows fresh data.
      void queryClient.invalidateQueries({
        queryKey: ["question-bank", "question", questionId],
      });
      resetForm();
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const handleSubmit = () => {
    setError(null);
    if (!questionText1.trim()) {
      setError("Question text is required.");
      return;
    }

    const payload: Record<string, unknown> = {
      question_type: questionType,
      question_text_1: questionText1,
      question_text_2: questionText2,
      scoring_type: scoringType,
      difficulty_level: difficulty,
      cognitive_level: cognitiveLevel,
    };

    // Type-specific fields
    if (passageTitle) payload.passage_title = passageTitle;
    if (passageBody) payload.passage_body = passageBody;
    if (displayDuration) payload.display_duration_seconds = parseInt(displayDuration);
    if (caseSensitive) payload.case_sensitive = true;
    if (pctThreshold) payload.pct_match_threshold = parseFloat(pctThreshold);
    if (flashInterval) payload.flash_interval_ms = parseInt(flashInterval);
    if (flashCount) payload.flash_display_count = parseInt(flashCount);
    if (gridRows) payload.grid_rows = parseInt(gridRows);
    if (gridCols) payload.grid_cols = parseInt(gridCols);
    if (ratingScalePoints) payload.rating_scale_points = parseInt(ratingScalePoints);
    if (ratingDirection) payload.rating_direction = ratingDirection;

    // Build grid correct cells from correctCells array
    const gridCorrectCells: { row: number; col: number; rowLabel: string; colLabel: string }[] = [];
    if (correctCells.length > 0) {
      for (let r = 0; r < correctCells.length; r++) {
        for (let c = 0; c < (correctCells[r]?.length ?? 0); c++) {
          if (correctCells[r][c]) {
            gridCorrectCells.push({
              row: r,
              col: c,
              rowLabel: rowLabels[r] || `Row ${r + 1}`,
              colLabel: colLabels[c] || `Col ${c + 1}`,
            });
          }
        }
      }
    }

    mutation.mutate({
      payload,
      opts: options,
      prs: pairs,
      img: imageUrl || undefined,
      aud: audioUrl || undefined,
      vid: videoUrl || undefined,
      hotspots: hotspotAreas.length > 0 ? hotspotAreas : undefined,
      gridCorrectCells: gridCorrectCells.length > 0 ? gridCorrectCells : undefined,
      scaleLabels: scaleLabels.length > 0 ? scaleLabels : undefined,
    });
  };

  // Determine which editor to render
  const isMCQ = questionType.startsWith("MCQ_");
  const isFITB = questionType.startsWith("FITB_");
  const isMatch = questionType === "MATCH_FOLLOWING";
  const isGrid = questionType === "GRID_LIST_SELECTION";
  const isHotspot = questionType.startsWith("HOTSPOT_");
  const isRank = questionType === "RANK_SIMPLE";
  const isRankRate = questionType === "RANK_THEN_RATE";
  const isRating = questionType === "STANDARD_RATING_SCALE";
  const isForcedChoice = questionType.startsWith("FORCED_CHOICE_");

  const mcqData = {
    question_text_1: questionText1,
    question_text_2: questionText2,
    scoring_type: scoringType,
    passage_title: passageTitle,
    passage_body: passageBody,
    display_duration_seconds: displayDuration,
    imageUrl,
    audioUrl,
    videoUrl,
    options,
    isMultipleAnswer,
  };

  const fitbData = {
    question_text_1: questionText1,
    scoring_type: scoringType,
    case_sensitive: caseSensitive,
    pct_match_threshold: pctThreshold,
    flash_interval_ms: flashInterval,
    flash_display_count: flashCount,
    options,
  };

  const matchData = { question_text_1: questionText1, scoring_type: "PARTIAL", pairs };

  const gridData = {
    question_text_1: questionText1,
    grid_rows: gridRows,
    grid_cols: gridCols,
    rowLabels,
    colLabels,
    correctCells,
  };

  const hotspotData = {
    question_text_1: questionText1,
    image_url: imageUrl,
    scoring_type: scoringType,
    areas: hotspotAreas,
  };

  const rankData = { question_text_1: questionText1, options };
  const rankRateData = {
    question_text_1: questionText1,
    rating_scale_points: ratingScalePoints,
    options,
  };
  const ratingData = {
    question_text_1: questionText1,
    rating_scale_points: ratingScalePoints,
    rating_direction: ratingDirection,
    scaleLabels,
  };
  const forcedChoiceData = {
    question_text_1: questionText1,
    rating_scale_points: ratingScalePoints,
    options,
  };

  return (
    <Modal
      open={open}
      onClose={() => {
        resetForm();
        onClose();
      }}
      title={isEditMode ? "Edit Question" : "Question Designer"}
      description={
        isEditMode
          ? "Update the question configuration. Child resources (options, media, hotspots) will be re-synced."
          : "Create a new question with full type-specific configuration."
      }
      size="xl"
    >
      {isLoadingQuestion && isEditMode && (
        <div className="mb-4 flex items-center justify-center py-8">
          <Spinner size="md" />
          <span className="ml-2 text-sm text-slate-500">Loading question…</span>
        </div>
      )}

      {!isLoadingQuestion && (
        <>
          {error && (
            <Alert variant="error" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

      <div className="space-y-4">
        {/* Type + difficulty + cognitive level */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <Label htmlFor="qtype" required>
              Question type
            </Label>
            <select
              id="qtype"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={questionType}
              onChange={(e) => {
                setQuestionType(e.target.value);
                setOptions([]);
                setPairs([]);
              }}
            >
              {QUESTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="diff">Difficulty</Label>
            <select
              id="diff"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              <option value="">Select...</option>
              {DIFFICULTY_LEVELS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="cog">Cognitive level</Label>
            <select
              id="cog"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={cognitiveLevel}
              onChange={(e) => setCognitiveLevel(e.target.value)}
            >
              <option value="">Select...</option>
              <option value="Recall">Recall</option>
              <option value="Understanding">Understanding</option>
              <option value="Application">Application</option>
              <option value="Analysis">Analysis</option>
              <option value="Evaluation">Evaluation</option>
              <option value="Synthesis">Synthesis</option>
            </select>
          </div>
        </div>

        {/* Type-specific editor */}
        <div className="rounded-md border border-slate-200 p-4">
          {isMCQ && (
            <MCQEditor
              questionType={questionType}
              data={mcqData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setQuestionText2(d.question_text_2);
                setScoringType(d.scoring_type);
                setPassageTitle(d.passage_title);
                setPassageBody(d.passage_body);
                setDisplayDuration(d.display_duration_seconds);
                setImageUrl(d.imageUrl);
                setAudioUrl(d.audioUrl);
                setVideoUrl(d.videoUrl);
                setOptions(d.options);
                setIsMultipleAnswer(d.isMultipleAnswer);
              }}
            />
          )}
          {isFITB && (
            <FITBEditor
              questionType={questionType}
              data={fitbData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setScoringType(d.scoring_type);
                setCaseSensitive(d.case_sensitive);
                setPctThreshold(d.pct_match_threshold);
                setFlashInterval(d.flash_interval_ms);
                setFlashCount(d.flash_display_count);
                setOptions(d.options);
              }}
            />
          )}
          {isMatch && (
            <MatchEditor
              data={matchData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setPairs(d.pairs);
              }}
            />
          )}
          {isGrid && (
            <GridEditor
              data={gridData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setGridRows(d.grid_rows);
                setGridCols(d.grid_cols);
                setRowLabels(d.rowLabels);
                setColLabels(d.colLabels);
                setCorrectCells(d.correctCells);
              }}
            />
          )}
          {isHotspot && (
            <HotspotEditor
              questionType={questionType}
              data={hotspotData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setImageUrl(d.image_url);
                setScoringType(d.scoring_type);
                setHotspotAreas(d.areas);
              }}
            />
          )}
          {isRank && (
            <RankEditor
              data={rankData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setOptions(d.options);
              }}
            />
          )}
          {isRankRate && (
            <RankRateEditor
              data={rankRateData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setRatingScalePoints(d.rating_scale_points);
                setOptions(d.options);
              }}
            />
          )}
          {isRating && (
            <RatingEditor
              data={ratingData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setRatingScalePoints(d.rating_scale_points);
                setRatingDirection(d.rating_direction);
                setScaleLabels(d.scaleLabels);
              }}
            />
          )}
          {isForcedChoice && (
            <ForcedChoiceEditor
              questionType={questionType}
              data={forcedChoiceData}
              onChange={(d) => {
                setQuestionText1(d.question_text_1);
                setRatingScalePoints(d.rating_scale_points);
                setOptions(d.options);
              }}
            />
          )}
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              resetForm();
              onClose();
            }}
          >
            Cancel
          </Button>
          <Button type="button" loading={mutation.isPending} onClick={handleSubmit}>
            {isEditMode ? "Update question" : "Create question"}
          </Button>
        </div>
      </div>
        </>
      )}
    </Modal>
  );
}
