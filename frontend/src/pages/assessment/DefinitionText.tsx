/**
 * Renders an assessment's Objective / Description / Instructions: sanitised
 * rich text from the editor (Report 9 #75), or plain text written before it
 * with its line breaks kept.
 */
import { RichText } from "@/components/ui";

import { looksLikeHtml } from "./richDefinition";

export function DefinitionText({ value }: { value: string }) {
  if (looksLikeHtml(value)) {
    return <RichText html={value} className="text-slate-700" />;
  }
  return <p className="whitespace-pre-line text-sm text-slate-700">{value}</p>;
}
