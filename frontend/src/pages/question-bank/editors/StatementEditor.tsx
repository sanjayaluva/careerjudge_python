/**
 * Psychometric Statement Editor (9) — Report 7 §35/§36.
 *
 * A psychometric statement is BARE TEXT authored in the Question Bank
 * (PSY-A1 / Doc 1 §3.1.6: no options, no scoring — its rank/forced-choice
 * variant is formed at assessment-configuration time when statements are
 * drawn into groups). Without this editor the type-9 flow had no text
 * field at all, so no statements could ever be authored and the
 * psychometric groups tab had nothing to select ("there is no facility to
 * add statements on Qn Bank").
 *
 * The statement text is stored in question_text_1; an optional secondary
 * line goes to question_text_2.
 */
import { Label, RichText, WysiwygEditorLite } from "@/components/ui";

interface StatementEditorProps {
  data: {
    question_text_1: string;
    question_text_2: string;
  };
  onChange: (data: StatementEditorProps["data"]) => void;
}

export function PsychometricStatementEditor({ data, onChange }: StatementEditorProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="stmt-text" required>
          Statement text
        </Label>
        <WysiwygEditorLite
          value={data.question_text_1}
          onChange={(html) => onChange({ ...data, question_text_1: html })}
          minHeight={80}
          placeholder="Enter the psychometric statement, e.g. “I enjoy leading a team…”"
        />
        <p className="mt-1 text-xs text-slate-500">
          A statement is plain text — it has no options and no scoring here. At assessment
          configuration, statements are drawn into Rank Groups or Forced-Choice Pairs (Psychometric
          Groups tab), which is where the scoring form is decided.
        </p>
      </div>
      <div>
        <Label htmlFor="stmt-text2">Secondary text (optional)</Label>
        <WysiwygEditorLite
          value={data.question_text_2}
          onChange={(html) => onChange({ ...data, question_text_2: html })}
          minHeight={60}
          placeholder="Optional secondary line shown to the candidate…"
        />
      </div>
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <RichText
          html={data.question_text_1}
          fallback="(no statement text)"
          className="text-sm font-medium text-slate-900"
        />
        {data.question_text_2 && (
          <RichText html={data.question_text_2} className="mt-1 text-sm text-slate-700" />
        )}
      </div>
    </div>
  );
}
