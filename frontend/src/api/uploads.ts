/**
 * Uploads used across modules.
 */
import { apiPost } from "./client";

/** Signed Doc 3 §2.1.2: limits checked again by the backend. */
export const EDITOR_IMAGE_MAX_BYTES = 5 * 1024 * 1024;
export const EDITOR_IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];

/** Uploads an image picked in the rich-text editor; resolves to the URL to
 * insert (`/api/uploads/editor-images/<name>`, served by the backend). */
export function uploadEditorImage(file: File): Promise<{ url: string }> {
  const form = new FormData();
  form.append("image", file);
  return apiPost<{ url: string }>("/uploads/editor-images/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}
