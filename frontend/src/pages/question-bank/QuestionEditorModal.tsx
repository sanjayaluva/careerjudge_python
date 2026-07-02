/**
 * Question Editor Modal — dynamic question creation/editing with type-specific editors.
 * Renders the correct editor (MCQ, FITB, Match, Grid, Hotspot, Rank, Rating, Forced-Choice)
 * based on the selected question type.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, AlertDescription, Button, Label, Modal } from "@/components/ui";
import { createQuestion, DIFFICULTY_LEVELS, QUESTION_TYPES } from "@/api/questionBank";
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
}

export function QuestionEditorModal({ open, onClose }: QuestionEditorModalProps) {
  const queryClient = useQueryClient();
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
  const [options, setOptions] = useState<OptionData[]>([]);
  const [pairs, setPairs] = useState<MatchPairData[]>([]);
  const [rowLabels, setRowLabels] = useState<string[]>([]);
  const [colLabels, setColLabels] = useState<string[]>([]);
  const [correctCells, setCorrectCells] = useState<boolean[][]>([]);

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
    setOptions([]);
    setPairs([]);
    setRowLabels([]);
    setColLabels([]);
    setCorrectCells([]);
    setError(null);
  };

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createQuestion(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QB_KEY });
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

    mutation.mutate(payload);
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
    options,
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
    areas: [],
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
    options,
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
      title="Question Designer"
      description="Create a new question with full type-specific configuration."
      size="xl"
    >
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
                setOptions(d.options);
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
                setOptions(d.options);
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
            Create question
          </Button>
        </div>
      </div>
    </Modal>
  );
}
