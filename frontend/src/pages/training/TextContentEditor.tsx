/**
 * Rich-text editing for training "text" content (Report 8 #8/#9/#17):
 * long texts are written and formatted in a large pop-up editor (bold,
 * italics, underline, colour, font size, headings, bullets, alignment,
 * links, images) instead of a 3-line textarea. The server sanitises the HTML
 * (core/rich_html.py) before students see it.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Modal, WysiwygEditor, useToast } from "@/components/ui";
import { stripHtml } from "@/components/ui/RichText";
import { extractApiError } from "@/api/client";
import { updateContent, type SessionContent } from "@/api/training";

const LOOKS_LIKE_HTML = /<\s*\/?\s*[a-zA-Z][^>]*>/;

export function isHtml(text: string | null | undefined): boolean {
  return Boolean(text && LOOKS_LIKE_HTML.test(text));
}

/** Plain text (older content) → paragraphs, so the editor keeps its layout. */
function toEditorHtml(text: string): string {
  if (!text || isHtml(text)) return text || "";
  const esc = (t: string) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return text
    .split(/\n{2,}/)
    .map((para) => `<p>${esc(para).replace(/\n/g, "<br>")}</p>`)
    .join("");
}

export function TextEditorModal({
  open,
  title,
  initial,
  saving,
  onClose,
  onSave,
}: {
  open: boolean;
  title: string;
  initial: string;
  saving?: boolean;
  onClose: () => void;
  onSave: (html: string) => void;
}) {
  const [html, setHtml] = useState(() => toEditorHtml(initial));
  return (
    <Modal open={open} onClose={onClose} title={title} size="xl">
      <div className="space-y-3">
        <div className="max-h-[65vh] overflow-y-auto">
          <WysiwygEditor value={html} onChange={setHtml} minHeight={420} />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={saving} onClick={() => onSave(html)}>
            Save text
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/** Field used when adding text content: preview + "Open editor". */
export function TextContentField({
  value,
  onChange,
}: {
  value: string;
  onChange: (html: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const preview = isHtml(value) ? stripHtml(value) : value;
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <p className="line-clamp-3 whitespace-pre-line text-sm text-slate-600">
        {preview || <span className="text-slate-400">No text yet.</span>}
      </p>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="mt-2"
        onClick={() => setOpen(true)}
      >
        {value ? "Edit text in editor" : "Open text editor"}
      </Button>
      {open && (
        <TextEditorModal
          open
          title="Text content"
          initial={value}
          onClose={() => setOpen(false)}
          onSave={(html) => {
            onChange(html);
            setOpen(false);
          }}
        />
      )}
    </div>
  );
}

/** "Edit text" on an existing text content (structure editor). */
export function EditTextContentButton({ content }: { content: SessionContent }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const save = useMutation({
    mutationFn: (html: string) => updateContent(content.id, { text_content: html }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training", "courses"] });
      toast.success("Text saved.");
      setOpen(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        ✎ Edit text
      </Button>
      {open && (
        <TextEditorModal
          open
          title={`Edit text — ${content.title}`}
          initial={content.text_content ?? ""}
          saving={save.isPending}
          onClose={() => setOpen(false)}
          onSave={(html) => save.mutate(html)}
        />
      )}
    </>
  );
}
