/**
 * WysiwygEditorLite — lightweight rich-text editor for Question Bank text fields.
 *
 * A trimmed-down version of WysiwygEditor.tsx with only inline formatting
 * (bold, italic, headings, lists, alignment) — no images or links, since
 * question text is short and media is uploaded separately.
 *
 * Output is clean HTML stored on the existing question_text_1 / question_text_2
 * / passage_body fields (already TextField, no schema change needed).
 */
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { useEffect } from "react";

interface WysiwygEditorLiteProps {
  value: string;
  onChange: (html: string) => void;
  minHeight?: number;
  placeholder?: string;
}

export function WysiwygEditorLite({
  value,
  onChange,
  minHeight = 100,
  placeholder = "Type here…",
}: WysiwygEditorLiteProps) {
  const editor = useEditor({
    extensions: [StarterKit, Underline, TextAlign.configure({ types: ["heading", "paragraph"] })],
    content: value,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "prose prose-sm max-w-none focus:outline-none px-3 py-2",
        style: `min-height: ${minHeight}px`,
        "data-placeholder": placeholder,
      },
    },
  });

  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || "");
    }
  }, [value, editor]);

  if (!editor) {
    return (
      <div className="rounded-md border border-slate-200 p-4 text-sm text-slate-500">
        Loading editor…
      </div>
    );
  }

  const btnClass =
    "px-2 py-1 text-xs rounded hover:bg-slate-100 transition-colors disabled:opacity-30";
  const activeClass = "bg-slate-200 font-semibold";

  return (
    <div className="overflow-hidden rounded-md border border-slate-200">
      <div className="flex flex-wrap items-center gap-1 border-b border-slate-100 bg-slate-50 p-1.5">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={`${btnClass} ${editor.isActive("bold") ? activeClass : ""}`}
          title="Bold"
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={`${btnClass} ${editor.isActive("italic") ? activeClass : ""}`}
          title="Italic"
        >
          <em>I</em>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={`${btnClass} ${editor.isActive("underline") ? activeClass : ""}`}
          title="Underline"
        >
          <u>U</u>
        </button>
        <div className="mx-1 h-4 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={`${btnClass} ${editor.isActive("heading", { level: 3 }) ? activeClass : ""}`}
          title="Subtitle"
        >
          Subtitle
        </button>
        <div className="mx-1 h-4 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`${btnClass} ${editor.isActive("bulletList") ? activeClass : ""}`}
          title="Bullet list"
        >
          • List
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`${btnClass} ${editor.isActive("orderedList") ? activeClass : ""}`}
          title="Numbered list"
        >
          1. List
        </button>
        <div className="mx-1 h-4 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
          className={`${btnClass} ${editor.isActive({ textAlign: "left" }) ? activeClass : ""}`}
          title="Align left"
        >
          ⬅
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
          className={`${btnClass} ${editor.isActive({ textAlign: "center" }) ? activeClass : ""}`}
          title="Align center"
        >
          ↔
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
          className={`${btnClass} ${editor.isActive({ textAlign: "right" }) ? activeClass : ""}`}
          title="Align right"
        >
          ➡
        </button>
        <div className="mx-1 h-4 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().unsetAllMarks().run()}
          className={btnClass}
          title="Clear formatting"
        >
          ⌫ Clear
        </button>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
