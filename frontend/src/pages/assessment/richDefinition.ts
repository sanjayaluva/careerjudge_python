/**
 * Report 9 #75: an assessment's Description and Instructions are authored in
 * the rich-text editor. Older assessments hold plain text; these helpers let
 * both render and edit correctly.
 */
import { stripHtml } from "@/components/ui";

const LOOKS_LIKE_HTML = /<\s*\/?\s*[a-zA-Z][^>]*>/;

export function looksLikeHtml(value: string | null | undefined): boolean {
  return !!value && LOOKS_LIKE_HTML.test(value);
}

/** True when there is something to show — text or an image (an emptied editor leaves "<p></p>"). */
export function hasRichContent(value: string | null | undefined): boolean {
  if (!value) return false;
  if (!looksLikeHtml(value)) return value.trim() !== "";
  return stripHtml(value) !== "" || /<img\b/i.test(value);
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Plain text → one paragraph per line, so the editor keeps its line breaks. */
export function toEditorHtml(value: string | null | undefined): string {
  if (!value) return "";
  if (looksLikeHtml(value)) return value;
  return value
    .split(/\r?\n/)
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join("");
}

/** What to save from the editor: "" when it holds nothing. */
export function fromEditorHtml(value: string): string {
  return hasRichContent(value) ? value : "";
}
