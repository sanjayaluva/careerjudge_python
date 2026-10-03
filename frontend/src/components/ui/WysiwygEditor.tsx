/**
 * WYSIWYG Editor — TipTap-based rich text editor for CMS pages + banners.
 *
 * Features: bold, italic, underline, text colour, font size, headings, lists,
 * links, images, text alignment (colour/size/underline: Report 8 #9).
 * Images are inserted by URL or uploaded from the author's computer (Signed
 * Doc 3 §2.1.2 "Image Upload"). Outputs clean HTML.
 */
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import TextAlign from "@tiptap/extension-text-align";
import { Color, FontSize, TextStyle } from "@tiptap/extension-text-style";
import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";

import { extractApiError } from "@/api/client";
import { EDITOR_IMAGE_MAX_BYTES, EDITOR_IMAGE_TYPES, uploadEditorImage } from "@/api/uploads";

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
      TextStyle,
      Color,
      FontSize,
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

  // Signed Doc 3 §2.1.2: the image button offers upload or URL.
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageMenuRef = useRef<HTMLDivElement>(null);
  const imageButtonRef = useRef<HTMLButtonElement>(null);
  const [imageMenuOpen, setImageMenuOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);

  useEffect(() => {
    if (!imageMenuOpen) return;
    const close = (e: MouseEvent) => {
      if (!imageMenuRef.current?.contains(e.target as Node)) setImageMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [imageMenuOpen]);

  // Keyboard users: Escape closes the image menu and returns focus to its
  // button — without also closing a dialog the editor sits in.
  const onImageMenuKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Escape" || !imageMenuOpen) return;
    e.preventDefault();
    e.stopPropagation();
    setImageMenuOpen(false);
    imageButtonRef.current?.focus();
  };

  // Sync external value changes (e.g., when loading existing content)
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || "");
    }
  }, [value, editor]);

  if (!editor) {
    return (
      <div className="rounded-md border border-slate-300 bg-white p-4 text-sm text-slate-500">
        Loading editor...
      </div>
    );
  }

  const insertImageFromUrl = () => {
    setImageMenuOpen(false);
    const url = window.prompt("Enter image URL:");
    if (url) editor.chain().focus().setImage({ src: url }).run();
  };

  const uploadImage = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // picking the same file again still fires onChange
    if (!file) return;
    if (!EDITOR_IMAGE_TYPES.includes(file.type)) {
      setImageError("Upload a PNG, JPEG, GIF or WebP image.");
      return;
    }
    if (file.size > EDITOR_IMAGE_MAX_BYTES) {
      setImageError("The image is larger than 5 MB.");
      return;
    }
    setImageError(null);
    setUploading(true);
    try {
      const { url } = await uploadEditorImage(file);
      const alt = file.name.replace(/\.[^.]+$/, "");
      editor.chain().focus().setImage({ src: url, alt }).run();
    } catch (err) {
      setImageError(extractApiError(err));
    } finally {
      setUploading(false);
    }
  };

  const btnClass =
    "inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-sm text-slate-600 transition-colors hover:bg-slate-200/70 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-30";
  const activeClass = "bg-white font-semibold text-primary-700 shadow-sm ring-1 ring-slate-200";

  return (
    // No overflow-hidden: the image menu may extend past a short editor.
    <div className="rounded-md border border-slate-300 bg-white shadow-sm transition-colors focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/25">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-0.5 rounded-t-md border-b border-slate-200 bg-slate-50 p-1.5">
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
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={`${btnClass} underline ${editor.isActive("underline") ? activeClass : ""}`}
          title="Underline"
        >
          U
        </button>
        <label className={`${btnClass} flex cursor-pointer items-center gap-1`} title="Text colour">
          <span style={{ color: editor.getAttributes("textStyle").color ?? undefined }}>A</span>
          <input
            type="color"
            className="h-4 w-4 cursor-pointer border-0 bg-transparent p-0"
            value={editor.getAttributes("textStyle").color ?? "#000000"}
            onChange={(e) => editor.chain().focus().setColor(e.target.value).run()}
          />
        </label>
        <select
          className="h-7 rounded border border-slate-200 bg-white px-1 text-xs"
          title="Font size"
          value={editor.getAttributes("textStyle").fontSize ?? ""}
          onChange={(e) =>
            e.target.value
              ? editor.chain().focus().setFontSize(e.target.value).run()
              : editor.chain().focus().unsetFontSize().run()
          }
        >
          <option value="">Size</option>
          {["12px", "14px", "16px", "18px", "22px", "28px"].map((sz) => (
            <option key={sz} value={sz}>
              {sz.replace("px", "")}
            </option>
          ))}
        </select>
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
        <div className="relative" ref={imageMenuRef} onKeyDown={onImageMenuKeyDown}>
          <button
            ref={imageButtonRef}
            type="button"
            onClick={() => setImageMenuOpen((open) => !open)}
            className={btnClass}
            disabled={uploading}
            aria-haspopup="menu"
            aria-expanded={imageMenuOpen}
          >
            {uploading ? "Uploading…" : "🖼 Image"}
          </button>
          {imageMenuOpen && (
            <div
              role="menu"
              className="absolute left-0 top-full z-20 mt-1 w-56 rounded-md border border-slate-200 bg-white py-1 shadow-lg"
            >
              <button
                type="button"
                role="menuitem"
                className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50"
                onClick={() => {
                  setImageMenuOpen(false);
                  fileInputRef.current?.click();
                }}
              >
                Upload image from computer
              </button>
              <button
                type="button"
                role="menuitem"
                className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50"
                onClick={insertImageFromUrl}
              >
                Insert image from URL
              </button>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept={EDITOR_IMAGE_TYPES.join(",")}
            className="hidden"
            aria-label="Upload image from computer"
            tabIndex={-1}
            onChange={(e) => void uploadImage(e)}
          />
        </div>
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
      {imageError && (
        <p
          role="alert"
          className="border-b border-danger-200 bg-danger-50 px-3 py-1.5 text-xs text-danger-700"
        >
          {imageError}
        </p>
      )}
      {/* Editor */}
      <EditorContent editor={editor} />
    </div>
  );
}
