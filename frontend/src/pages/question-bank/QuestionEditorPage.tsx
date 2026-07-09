/**
 * Question Editor Page — full-page question create/edit.
 *
 * Replaces the old QuestionEditorModal. Using a full page instead of a modal
 * gives more screen space for the type-specific editors and solves the
 * intermittent data-loading issue (modal state wasn't always syncing with
 * the fetched question detail).
 *
 * Routes:
 *   /question-bank/new           → create mode
 *   /question-bank/:id/edit      → edit mode (loads existing question)
 *
 * On successful save, navigates back to the question detail page (edit mode)
 * or the question bank list (create mode).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Link } from "react-router-dom";

import { Alert, AlertDescription, Button, Label, Spinner } from "@/components/ui";
import {
  bulkSaveOptions,
  createFlashItem,
  createHotspot,
  createMediaFile,
  createQuestion,
  deleteFlashItem,
  deleteHotspot,
  deleteMediaFile,
  DIFFICULTY_LEVELS,
  listCategories,
  QUESTION_TYPES,
  retrieveQuestion,
  updateQuestion,
  type QuestionDetail,
} from "@/api/questionBank";
import { extractApiError } from "@/api/client";
import type { FlashItemData, OptionData, MatchPairData } from "./editors/shared";
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

// Default scoring type per question type. Used when the type-specific editor
// doesn't expose its own scoring type selector (Match, Grid, Rank, Rating,
// Forced-Choice). Editors that DO have a selector (MCQ, FITB, Hotspot) will
// override this via their onChange callback.
const DEFAULT_SCORING_BY_TYPE: Record<string, string> = {
  MCQ_TEXT_IMAGE: "BINARY",
  MCQ_TEXT_IMAGE_IMG_OPTIONS: "BINARY",
  MCQ_AUDIO_MULTI: "BINARY",
  MCQ_VIDEO_MULTI: "BINARY",
  MCQ_WORD_FLASH_MULTI: "BINARY",
  MCQ_IMAGE_FLASH_MULTI: "BINARY",
  MCQ_PASSAGE_DISPLAY_MULTI: "BINARY",
  MCQ_IMAGE_DISPLAY_MULTI: "BINARY",
  FITB_SINGLE: "BINARY",
  FITB_MULTI_FIELD: "PARTIAL",
  FITB_WORD_FLASH_MULTI: "PARTIAL",
  FITB_IMAGE_FLASH_MULTI: "PARTIAL",
  MATCH_FOLLOWING: "PARTIAL",
  GRID_LIST_SELECTION: "PARTIAL",
  HOTSPOT_SINGLE: "BINARY",
  HOTSPOT_MULTI: "NEGATIVE",
  RANK_SIMPLE: "RANK",
  RANK_THEN_RATE: "RANK_RATE",
  STANDARD_RATING_SCALE: "RATING",
  FORCED_CHOICE_SINGLE_LEVEL: "FORCED_CHOICE",
  FORCED_CHOICE_TWO_LEVEL: "FORCED_CHOICE_RATED",
};

export default function QuestionEditorPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const questionId = id ? Number(id) : null;
  const isEditMode = Boolean(questionId);
  const queryClient = useQueryClient();

  const [questionType, setQuestionType] = useState("MCQ_TEXT_IMAGE");
  const [questionTitle, setQuestionTitle] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [cognitiveLevel, setCognitiveLevel] = useState("");
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  // Fetch categories for the category dropdown.
  const { data: categories } = useQuery({
    queryKey: ["question-bank", "categories"],
    queryFn: () => listCategories(),
    staleTime: 60_000,
  });

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
  const [flashOrder, setFlashOrder] = useState("SEQUENCE");
  const [imageWidth, setImageWidth] = useState(0);
  const [imageHeight, setImageHeight] = useState(0);
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
  const [cellContent, setCellContent] = useState<
    { text: string; image: string; is_correct: boolean }[][]
  >([]);
  const [isMultipleAnswer, setIsMultipleAnswer] = useState(false);
  const [scaleLabels, setScaleLabels] = useState<string[]>([]);
  const [flashItems, setFlashItems] = useState<FlashItemData[]>([]);
  const [hotspotAreas, setHotspotAreas] = useState<
    {
      x: number;
      y: number;
      width_px: number;
      height_px: number;
      area_size_code: string;
      sub_question_index?: number;
      shape_type: "RECTANGLE" | "CIRCLE" | "POLYGON";
      is_correct: boolean;
      radius?: number;
      points?: { x: number; y: number }[];
    }[]
  >([]);

  // Populate the form from an existing QuestionDetail (edit mode).
  const populateForm = (q: QuestionDetail) => {
    setQuestionType(q.question_type);
    setQuestionTitle(q.question_title ?? "");
    setDifficulty(q.difficulty_level ?? "");
    setCognitiveLevel(q.cognitive_level ?? "");
    setCategoryId(q.category ?? "");
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
    setFlashOrder(q.flash_order ?? "SEQUENCE");
    setGridRows(q.grid_rows != null ? String(q.grid_rows) : "3");
    setGridCols(q.grid_cols != null ? String(q.grid_cols) : "3");
    setRatingScalePoints(q.rating_scale_points != null ? String(q.rating_scale_points) : "5");
    setRatingDirection(q.rating_direction ?? "FORWARD");
    setImageUrl(q.image ?? "");
    setImageWidth(q.image_width ?? 0);
    setImageHeight(q.image_height ?? 0);
    setAudioUrl(q.media_files.find((m) => m.media_type === "AUDIO")?.file ?? "");
    setVideoUrl(q.media_files.find((m) => m.media_type === "VIDEO")?.file ?? "");

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

    // Rebuild grid state from DRAG_POOL options (for type 4: Grid-List Selection)
    const dragPoolOptions = q.options.filter((o) => o.option_type === "DRAG_POOL");
    if (dragPoolOptions.length > 0) {
      const numRows = q.grid_rows || 3;
      const numCols = q.grid_cols || 3;
      // Initialize empty grid
      const newCellContent: { text: string; image: string; is_correct: boolean }[][] = [];
      const newCorrectCells: boolean[][] = [];
      for (let r = 0; r < numRows; r++) {
        newCellContent.push([]);
        newCorrectCells.push([]);
        for (let c = 0; c < numCols; c++) {
          newCellContent[r].push({ text: "", image: "", is_correct: false });
          newCorrectCells[r].push(false);
        }
      }
      // Populate from DRAG_POOL options — sorted by order
      dragPoolOptions
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        .forEach((opt) => {
          // Parse row/col from the label "Row X → Col Y" or "RowLabel → ColLabel"
          const label = opt.label || "";
          const match = label.match(/^(.+?)\s*→\s*(.+)$/);
          if (match) {
            const rowLabel = match[1];
            const colLabel = match[2];
            // Try to find row index by label match or number
            let rowIdx = -1;
            let colIdx = -1;
            // Try "Row N" format
            const rowMatch = rowLabel.match(/Row\s*(\d+)/i);
            const colMatch = colLabel.match(/Col\s*(\d+)/i);
            if (rowMatch) rowIdx = parseInt(rowMatch[1]) - 1;
            if (colMatch) colIdx = parseInt(colMatch[1]) - 1;
            // Fallback: use order to determine position
            if (rowIdx < 0 || colIdx < 0) {
              const order = opt.order ?? 0;
              rowIdx = Math.floor(order / numCols);
              colIdx = order % numCols;
            }
            if (rowIdx >= 0 && rowIdx < numRows && colIdx >= 0 && colIdx < numCols) {
              newCellContent[rowIdx][colIdx] = {
                text: opt.text_value || "",
                image: opt.image_file || "",
                is_correct: opt.is_correct,
              };
              newCorrectCells[rowIdx][colIdx] = opt.is_correct;
            }
          }
        });
      setCellContent(newCellContent);
      setCorrectCells(newCorrectCells);
      // Rebuild row/col labels from the option labels
      const rLabels: string[] = [];
      const cLabels: string[] = [];
      for (let r = 0; r < numRows; r++) rLabels.push(`Row ${r + 1}`);
      for (let c = 0; c < numCols; c++) cLabels.push(`Col ${c + 1}`);
      dragPoolOptions.forEach((opt) => {
        const label = opt.label || "";
        const match = label.match(/^(.+?)\s*→\s*(.+)$/);
        if (match) {
          const rowLabel = match[1];
          const colLabel = match[2];
          const rowMatch = rowLabel.match(/Row\s*(\d+)/i);
          const colMatch = colLabel.match(/Col\s*(\d+)/i);
          if (rowMatch) rLabels[parseInt(rowMatch[1]) - 1] = rowLabel;
          if (colMatch) cLabels[parseInt(colMatch[1]) - 1] = colLabel;
        }
      });
      setRowLabels(rLabels);
      setColLabels(cLabels);
    } else {
      setRowLabels([]);
      setColLabels([]);
      setCorrectCells([]);
      setCellContent([]);
    }
    setIsMultipleAnswer(textOptions.filter((o) => o.is_correct).length > 1);
    setScaleLabels(
      textOptions
        .filter((o) => o.label?.startsWith("Point "))
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        .map((o) => o.text_value ?? ""),
    );
    setHotspotAreas(
      [...q.hotspot_areas]
        .sort((a, b) => a.id - b.id)
        .map((h) => ({
          x: h.x,
          y: h.y,
          width_px: h.width_px,
          height_px: h.height_px,
          area_size_code: h.area_size_code ?? "",
          sub_question_index: h.sub_question_index,
          shape_type: (h.shape_type as "RECTANGLE" | "CIRCLE" | "POLYGON") || "RECTANGLE",
          is_correct: h.is_correct ?? true,
          radius: h.radius ?? undefined,
          points: h.points ?? undefined,
        })),
    );
    // Load flash items for flash question types (1e, 1f, 2c, 2d)
    setFlashItems(
      q.flash_items.map((f) => ({
        id: f.id,
        item_type: f.item_type as "TEXT" | "IMAGE",
        text_value: f.text_value ?? "",
        image_file: f.image_file ?? null,
        order: f.order,
        is_in_display_pool: f.is_in_display_pool,
      })),
    );
    setError(null);
  };

  // Fetch the question detail in edit mode. Using a query keyed by questionId
  // ensures the data is fresh and properly cached.
  const { data: existingQuestion, isFetching: isLoadingQuestion } = useQuery({
    queryKey: ["question-bank", "question", questionId],
    queryFn: () => retrieveQuestion(questionId as number),
    enabled: Boolean(questionId),
    staleTime: 0,
  });

  // Populate the form when the fetched data arrives.
  useEffect(() => {
    if (existingQuestion && isEditMode) {
      populateForm(existingQuestion);
    }
  }, [existingQuestion, isEditMode]);

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
      gridCellOptions?: Record<string, unknown>[];
      scaleLabels?: string[];
      flashItems?: FlashItemData[];
    }) => {
      const {
        payload,
        opts,
        prs,
        img,
        aud,
        vid,
        hotspots,
        gridCellOptions,
        scaleLabels,
        flashItems,
      } = params;

      if (img) payload.image = img;
      if (imageWidth) payload.image_width = imageWidth;
      if (imageHeight) payload.image_height = imageHeight;
      const question = isEditMode
        ? await updateQuestion(questionId as number, payload)
        : await createQuestion(payload);

      // In edit mode, delete existing media files, hotspots, AND flash items
      // in PARALLEL (not sequentially) to reduce total wait time.
      if (isEditMode) {
        const current = await retrieveQuestion(questionId as number);
        const deletePromises: Promise<unknown>[] = [
          ...current.media_files.map((m) => deleteMediaFile(questionId as number, m.id)),
          ...current.hotspot_areas.map((h) => deleteHotspot(questionId as number, h.id)),
          ...current.flash_items.map((f) => deleteFlashItem(questionId as number, f.id)),
        ];
        if (deletePromises.length > 0) {
          await Promise.all(deletePromises);
        }
      }

      // Create new media files in parallel
      const mediaPromises: Promise<unknown>[] = [];
      if (aud) mediaPromises.push(createMediaFile(question.id, { media_type: "AUDIO", file: aud }));
      if (vid) mediaPromises.push(createMediaFile(question.id, { media_type: "VIDEO", file: vid }));
      if (mediaPromises.length > 0) await Promise.all(mediaPromises);

      // Combine ALL options (regular + match pairs + grid cells + rating labels)
      // into a SINGLE bulkSaveOptions call to minimize API round-trips.
      const allOptions: Record<string, unknown>[] = [];

      // Regular options (MCQ, FITB, Rank, Forced-Choice)
      if (opts.length > 0) {
        opts.forEach((opt, i) => {
          allOptions.push({
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
          });
        });
      }

      // Match pairs
      if (prs.length > 0) {
        prs.forEach((pair, i) => {
          allOptions.push({
            sub_question_index: 0,
            option_type: "MATCH_A",
            text_value: pair.groupA.text_value,
            match_pair_id: pair.pairId,
            is_correct: false,
            predefined_score: 1.0,
            order: i * 2,
          });
          allOptions.push({
            sub_question_index: 0,
            option_type: "MATCH_B",
            text_value: pair.groupB.text_value,
            match_pair_id: pair.pairId,
            is_correct: false,
            predefined_score: 1.0,
            order: i * 2 + 1,
          });
        });
      }

      // Grid cells with content (text/image per cell + correct flag)
      if (gridCellOptions && gridCellOptions.length > 0) {
        gridCellOptions.forEach((opt) => allOptions.push(opt));
      }

      // Rating scale labels
      if (scaleLabels && scaleLabels.length > 0) {
        scaleLabels.forEach((label, i) => {
          allOptions.push({
            sub_question_index: 0,
            option_type: "TEXT",
            label: `Point ${i + 1}`,
            text_value: label,
            is_correct: false,
            predefined_score: 1.0,
            order: i,
          });
        });
      }

      // Single bulk save for ALL options (replaces 4 separate API calls)
      if (allOptions.length > 0) {
        await bulkSaveOptions(question.id, allOptions);
      }

      // Create hotspot areas SEQUENTIALLY (not parallel) so DB id order
      // matches the array order — prevents shape shuffling on reload.
      if (hotspots && hotspots.length > 0) {
        for (const hs of hotspots) {
          await createHotspot(question.id, hs);
        }
      }

      // Create flash items SEQUENTIALLY (not parallel) so DB id order
      // matches the array order — prevents item shuffling on reload.
      if (flashItems && flashItems.length > 0) {
        for (const fi of flashItems) {
          await createFlashItem(question.id, {
            item_type: fi.item_type,
            text_value: fi.text_value,
            image_file: fi.image_file,
            order: flashItems.indexOf(fi),
            is_in_display_pool: fi.is_in_display_pool,
          });
        }
      }

      return question;
    },
    onSuccess: (question) => {
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
      void queryClient.invalidateQueries({
        queryKey: ["question-bank", "question", questionId],
      });
      // Navigate to the question detail page after save.
      navigate(`/question-bank/${question.id}`);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const handleSubmit = () => {
    setError(null);
    if (!questionTitle.trim()) {
      setError("Question title is required.");
      return;
    }
    if (!questionText1.trim()) {
      setError("Question text is required.");
      return;
    }

    const payload: Record<string, unknown> = {
      question_type: questionType,
      question_title: questionTitle,
      question_text_1: questionText1,
      question_text_2: questionText2,
      scoring_type: scoringType,
      difficulty_level: difficulty,
      cognitive_level: cognitiveLevel,
    };

    if (categoryId) payload.category = categoryId;
    else payload.category = null;

    if (passageTitle) payload.passage_title = passageTitle;
    if (passageBody) payload.passage_body = passageBody;
    if (displayDuration) payload.display_duration_seconds = parseInt(displayDuration);
    if (caseSensitive) payload.case_sensitive = true;
    if (pctThreshold) payload.pct_match_threshold = parseFloat(pctThreshold);
    if (flashInterval) payload.flash_interval_ms = parseInt(flashInterval);
    if (flashCount) payload.flash_display_count = parseInt(flashCount);
    if (flashOrder) payload.flash_order = flashOrder;
    if (gridRows) payload.grid_rows = parseInt(gridRows);
    if (gridCols) payload.grid_cols = parseInt(gridCols);
    if (ratingScalePoints) payload.rating_scale_points = parseInt(ratingScalePoints);
    if (ratingDirection) payload.rating_direction = ratingDirection;

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

    // Build grid cell options from cellContent (text + image per cell)
    const gridCellOptions: Record<string, unknown>[] = [];
    if (cellContent.length > 0) {
      let order = 0;
      for (let r = 0; r < cellContent.length; r++) {
        for (let c = 0; c < (cellContent[r]?.length ?? 0); c++) {
          const cell = cellContent[r][c];
          if (cell && (cell.text || cell.image)) {
            gridCellOptions.push({
              sub_question_index: 0,
              option_type: "DRAG_POOL",
              label: `${rowLabels[r] || `Row ${r + 1}`} → ${colLabels[c] || `Col ${c + 1}`}`,
              text_value: cell.text || "",
              image_file: cell.image || null,
              is_correct: correctCells?.[r]?.[c] || false,
              predefined_score: 1.0,
              order: order++,
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
      gridCellOptions: gridCellOptions.length > 0 ? gridCellOptions : undefined,
      scaleLabels: scaleLabels.length > 0 ? scaleLabels : undefined,
      flashItems: flashItems.length > 0 ? flashItems : undefined,
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
    flashItems,
    flashIntervalMs: flashInterval,
    flashDisplayCount: flashCount,
    flashOrder,
  };

  const fitbData = {
    question_text_1: questionText1,
    scoring_type: scoringType,
    case_sensitive: caseSensitive,
    pct_match_threshold: pctThreshold,
    flash_interval_ms: flashInterval,
    flash_display_count: flashCount,
    flash_order: flashOrder,
    options,
    flashItems,
  };

  const matchData = { question_text_1: questionText1, scoring_type: "PARTIAL", pairs };

  const gridData = {
    question_text_1: questionText1,
    grid_rows: gridRows,
    grid_cols: gridCols,
    rowLabels,
    colLabels,
    correctCells,
    cellContent,
  };

  const hotspotData = {
    question_text_1: questionText1,
    question_text_2: questionText2,
    image_url: imageUrl,
    scoring_type: scoringType,
    areas: hotspotAreas,
    image_width: imageWidth,
    image_height: imageHeight,
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
    <div className="space-y-6 p-6">
      {/* Breadcrumb + title */}
      <div>
        <Link to="/question-bank" className="text-sm text-primary-600 hover:underline">
          ← Back to Question Bank
        </Link>
        <h1 className="mt-2 text-xl font-bold text-slate-900">
          {isEditMode ? "Edit Question" : "Create Question"}
        </h1>
        <p className="text-sm text-slate-500">
          {isEditMode
            ? "Update the question configuration. Child resources (options, media, hotspots) will be re-synced."
            : "Create a new question with full type-specific configuration."}
        </p>
      </div>

      {/* Loading state for edit mode */}
      {isLoadingQuestion && isEditMode ? (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
          <span className="ml-3 text-sm text-slate-500">Loading question…</span>
        </div>
      ) : (
        <>
          {error && (
            <Alert variant="error">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Top form row: type + category + difficulty + cognitive level */}
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <Label htmlFor="qtype" required>
                  Question type
                </Label>
                <select
                  id="qtype"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                  value={questionType}
                  onChange={(e) => {
                    const newType = e.target.value;
                    setQuestionType(newType);
                    setOptions([]);
                    setPairs([]);
                    setScoringType(DEFAULT_SCORING_BY_TYPE[newType] ?? "BINARY");
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
                <Label htmlFor="cat">Category</Label>
                <select
                  id="cat"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : "")}
                >
                  <option value="">No category</option>
                  {(categories ?? []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.full_path || c.name}
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
          </div>

          {/* Type-specific editor (with Question title as the first field) */}
          <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            {/* Question title — mandatory, first field in this section */}
            <div>
              <Label htmlFor="qtitle" required>
                Question title
              </Label>
              <input
                id="qtitle"
                type="text"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                value={questionTitle}
                onChange={(e) => setQuestionTitle(e.target.value)}
                placeholder="Short title to identify this question (e.g. 'Capital Cities - Easy MCQ')"
                maxLength={255}
              />
              <p className="mt-1 text-xs text-slate-500">
                This title identifies the question in lists and previews. It is not shown to
                candidates.
              </p>
            </div>

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
                  setFlashItems(d.flashItems);
                  setFlashInterval(d.flashIntervalMs);
                  setFlashCount(d.flashDisplayCount);
                  setFlashOrder(d.flashOrder);
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
                  setFlashOrder(d.flash_order);
                  setOptions(d.options);
                  setFlashItems(d.flashItems);
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
                  setCellContent(d.cellContent);
                }}
              />
            )}
            {isHotspot && (
              <HotspotEditor
                questionType={questionType}
                data={hotspotData}
                onChange={(d) => {
                  setQuestionText1(d.question_text_1);
                  setQuestionText2(d.question_text_2);
                  setImageUrl(d.image_url);
                  setScoringType(d.scoring_type);
                  setHotspotAreas(d.areas);
                  setImageWidth(d.image_width);
                  setImageHeight(d.image_height);
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

          {/* Submit bar — sticky at bottom for easy access */}
          <div className="sticky bottom-0 flex justify-end gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(-1)}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
            <Button type="button" loading={mutation.isPending} onClick={handleSubmit}>
              {isEditMode ? "Update question" : "Create question"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
