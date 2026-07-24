/**
 * WYSIWYG Editor — TipTap-based rich text editor for CMS pages + banners.
 *
 * Features: bold, italic, headings, lists, links, images, text alignment.
 * Outputs clean HTML.
 */
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import TextAlign from "@tiptap/extension-text-align";
import { useEffect } from "react";

interface WysiwygEditorProps {
  value: string;
  onChange: (html: string) => void;
  minHeight?: number;
}

export function WysiwygEditor({ value, onChange, minHeight = 200 }: WysiwygEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { class: "text-primary-600 underline" },
      }),
      Image.configure({ inline: false }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
    ],
    content: value,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "prose prose-sm max-w-none focus:outline-none px-4 py-3",
        style: `min-height: ${minHeight}px`,
      },
    },
  });

  // Sync external value changes (e.g., when loading existing content)
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || "");
    }
  }, [value, editor]);

  if (!editor) {
    return <div className="rounded-md border border-slate-200 p-4">Loading editor...</div>;
  }

  const btnClass =
    "px-2 py-1 text-sm rounded hover:bg-slate-100 transition-colors disabled:opacity-30";
  const activeClass = "bg-slate-200 font-semibold";

  return (
    <div className="overflow-hidden rounded-md border border-slate-200">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 border-b border-slate-100 bg-slate-50 p-2">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={`${btnClass} ${editor.isActive("bold") ? activeClass : ""}`}
          title="Bold"
        >
          B
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={`${btnClass} ${editor.isActive("italic") ? activeClass : ""}`}
          title="Italic"
        >
          I
        </button>
        <div className="mx-1 h-5 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={`${btnClass} ${editor.isActive("heading", { level: 1 }) ? activeClass : ""}`}
        >
          H1
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={`${btnClass} ${editor.isActive("heading", { level: 2 }) ? activeClass : ""}`}
        >
          H2
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={`${btnClass} ${editor.isActive("heading", { level: 3 }) ? activeClass : ""}`}
        >
          H3
        </button>
        <div className="mx-1 h-5 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`${btnClass} ${editor.isActive("bulletList") ? activeClass : ""}`}
        >
          • List
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`${btnClass} ${editor.isActive("orderedList") ? activeClass : ""}`}
        >
          1. List
        </button>
        <div className="mx-1 h-5 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => {
            const url = window.prompt("Enter URL:");
            if (url) editor.chain().focus().setLink({ href: url }).run();
          }}
          className={`${btnClass} ${editor.isActive("link") ? activeClass : ""}`}
        >
          🔗 Link
        </button>
        <button
          type="button"
          onClick={() => {
            const url = window.prompt("Enter image URL:");
            if (url) editor.chain().focus().setImage({ src: url }).run();
          }}
          className={btnClass}
        >
          🖼 Image
        </button>
        <div className="mx-1 h-5 w-px bg-slate-200" />
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
          className={`${btnClass} ${editor.isActive({ textAlign: "left" }) ? activeClass : ""}`}
        >
          ⬅
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
          className={`${btnClass} ${editor.isActive({ textAlign: "center" }) ? activeClass : ""}`}
        >
          ↔
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
          className={`${btnClass} ${editor.isActive({ textAlign: "right" }) ? activeClass : ""}`}
        >
          ➡
        </button>
      </div>
      {/* Editor */}
      <EditorContent editor={editor} />
    </div>
  );
}
