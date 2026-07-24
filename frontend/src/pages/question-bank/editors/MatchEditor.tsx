/**
 * Match Editor — for type 3 (Match-the-Following)
 * Define Group A and Group B pairs, candidate drags to match.
 * Optional: add dummy (non-matching) options to Group B for added difficulty.
 * Per SRS feedback Issue 13 §1 — Add Dummy Option feature.
 */
import { Button, Input, Label } from "@/components/ui";
import {
  AddOptionButton,
  MatchPairRow,
  createEmptyMatchPair,
  type MatchPairData,
  type OptionData,
} from "./shared";

interface MatchEditorProps {
  data: {
    question_text_1: string;
    scoring_type: string;
    pairs: MatchPairData[];
    dummyOptions: OptionData[];
  };
  onChange: (data: MatchEditorProps["data"]) => void;
}

export function MatchEditor({ data, onChange }: MatchEditorProps) {
  const updatePair = (index: number, pair: MatchPairData) => {
    const newPairs = [...data.pairs];
    newPairs[index] = pair;
    onChange({ ...data, pairs: newPairs });
  };

  const addPair = () => {
    const nextId = data.pairs.length + 1;
    onChange({
      ...data,
      pairs: [...data.pairs, createEmptyMatchPair(nextId, data.pairs.length)],
    });
  };

  const removePair = (index: number) => {
    onChange({
      ...data,
      pairs: data.pairs.filter((_, i) => i !== index),
    });
  };

  const addDummy = () => {
    const newDummy: OptionData = {
      sub_question_index: 0,
      option_type: "MATCH_DUMMY",
      label: "",
      text_value: "",
      image_file: null,
      is_correct: false,
      match_pair_id: null,
      predefined_score: 0,
      order: data.dummyOptions.length,
      correct_answers: [],
    };
    onChange({ ...data, dummyOptions: [...data.dummyOptions, newDummy] });
  };

  const updateDummy = (index: number, dummy: OptionData) => {
    const newDummies = [...data.dummyOptions];
    newDummies[index] = dummy;
    onChange({ ...data, dummyOptions: newDummies });
  };

  const removeDummy = (index: number) => {
    onChange({
      ...data,
      dummyOptions: data.dummyOptions.filter((_, i) => i !== index),
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
          placeholder="Instructions for matching..."
        />
      </div>

      <div className="space-y-3">
        <Label>Match Pairs (Group A → Group B)</Label>
        {data.pairs.map((pair, i) => (
          <MatchPairRow key={i} pair={pair} index={i} onChange={updatePair} onRemove={removePair} />
        ))}
        <AddOptionButton onClick={addPair} label="Add pair" />
      </div>

      {/* Dummy options — added to Group B at delivery time to increase difficulty */}
      <div className="space-y-3 rounded-md border border-amber-200 bg-amber-50/40 p-3">
        <div className="flex items-center justify-between">
          <div>
            <Label>Dummy Options (optional)</Label>
            <p className="text-xs text-slate-500">
              Non-matching items added to Group B at delivery time. Shuffled together with correct
              matches to make guessing harder.
            </p>
          </div>
          <span className="text-xs text-slate-500">
            {data.dummyOptions.length} dummy option{data.dummyOptions.length !== 1 ? "s" : ""}
          </span>
        </div>
        {data.dummyOptions.map((dummy, i) => (
          <div
            key={i}
            className="flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3"
          >
            <div className="flex-1 space-y-1">
              <span className="text-xs font-medium text-slate-500">Dummy {i + 1}</span>
              <Input
                value={dummy.text_value}
                onChange={(e) => updateDummy(i, { ...dummy, text_value: e.target.value })}
                placeholder="Non-matching item (e.g. a person who is NOT associated with any Group A item)"
                className="text-sm"
              />
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-danger hover:bg-danger-50"
              onClick={() => removeDummy(i)}
            >
              Remove
            </Button>
          </div>
        ))}
        <AddOptionButton onClick={addDummy} label="Add dummy option" />
      </div>

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-1 text-xs font-medium text-slate-600">Group A</p>
            {data.pairs.map((p, i) => (
              <div
                key={i}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm"
              >
                {p.groupA.text_value || `(item ${i + 1})`}
              </div>
            ))}
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-slate-600">
              Group B (shuffled at delivery — {data.pairs.length + data.dummyOptions.length} items)
            </p>
            {data.pairs.map((p, i) => (
              <div
                key={i}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm"
              >
                {p.groupB.text_value || `(match ${i + 1})`}
              </div>
            ))}
            {data.dummyOptions.map((d, i) => (
              <div
                key={`d-${i}`}
                className="rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm italic text-amber-800"
              >
                {d.text_value || `(dummy ${i + 1})`}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
