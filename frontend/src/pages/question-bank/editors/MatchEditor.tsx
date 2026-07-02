/**
 * Match Editor — for type 3 (Match-the-Following)
 * Define Group A and Group B pairs, candidate drags to match.
 */
import { Label } from "@/components/ui";
import { AddOptionButton, MatchPairRow, createEmptyMatchPair, type MatchPairData } from "./shared";

interface MatchEditorProps {
  data: {
    question_text_1: string;
    scoring_type: string;
    pairs: MatchPairData[];
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
            <p className="mb-1 text-xs font-medium text-slate-600">Group B (shuffle at delivery)</p>
            {data.pairs.map((p, i) => (
              <div
                key={i}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm"
              >
                {p.groupB.text_value || `(match ${i + 1})`}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
