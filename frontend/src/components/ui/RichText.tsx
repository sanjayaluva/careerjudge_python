/**
 * RichText — renders an HTML string safely with prose styling.
 *
 * Use this everywhere WYSIWYG-produced HTML needs to be displayed
 * (question text 1/2, passage body, etc.). Centralises the
 * dangerouslySetInnerHTML usage so we can later add a sanitizer
 * (e.g. DOMPurify) in one place.
 *
 * For list/table snippets where HTML tags would be visible, use
 * `stripHtml()` from this module instead — render the plain-text
 * snippet, not the HTML.
 */
import { cn } from "@/lib/utils";

interface RichTextProps {
  /** HTML string to render. */
  html: string;
  /** Extra Tailwind classes for the wrapper. */
  className?: string;
  /** Fallback to show when html is empty. */
  fallback?: string;
}

export function RichText({ html, className, fallback }: RichTextProps) {
  const content = html?.trim() ? html : "";
  if (!content) {
    return fallback ? <p className={cn("text-sm text-slate-400", className)}>{fallback}</p> : null;
  }
  return (
    <div
      className={cn("prose prose-sm max-w-none", className)}
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
}

/**
 * Strip HTML tags from a string — for use in list/table snippets
 * where the raw HTML tags would be visible as literal text.
 *
 * Example: "<p>Hello <strong>world</strong></p>" → "Hello world"
 */
export function stripHtml(s: string | null | undefined): string {
  if (!s) return "";
  return s
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}
