/**
 * Media Manager — reusable component for media field selection.
 *
 * Supports 3 modes (configurable per use case):
 * 1. Upload from user machine (file input → base64 data URL for preview)
 * 2. Select from already uploaded medias (gallery grid)
 * 3. Provide remote URL
 *
 * Gallery mode stores a list of previously uploaded media URLs in localStorage
 * so they persist across sessions. Phase 2b will replace with a backend API.
 */
import { useEffect, useRef, useState } from "react";
import { Button, Input, Label, Modal } from "@/components/ui";

export interface MediaManagerProps {
  label: string;
  accept?: string;
  modes?: ("upload" | "url" | "gallery")[];
  value: string;
  onChange: (value: string) => void;
  previewType?: "image" | "audio" | "video" | "none";
  helpText?: string;
  storageKey?: string; // localStorage key for gallery items
}

const DEFAULT_STORAGE_KEY = "cj_media_library";

function loadGallery(storageKey: string): string[] {
  try {
    const raw = localStorage.getItem(storageKey);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveGallery(storageKey: string, items: string[]) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(items));
  } catch {
    // quota exceeded — ignore
  }
}

export function MediaManager({
  label,
  accept = "image/*",
  modes = ["upload", "url"],
  value,
  onChange,
  previewType = "image",
  helpText,
  storageKey = DEFAULT_STORAGE_KEY,
}: MediaManagerProps) {
  const [activeMode, setActiveMode] = useState<string>(modes[0] ?? "url");
  const [uploading, setUploading] = useState(false);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [galleryItems, setGalleryItems] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (modes.includes("gallery")) {
      setGalleryItems(loadGallery(storageKey));
    }
  }, [modes, storageKey]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      onChange(dataUrl);

      // Save to gallery for future reuse
      if (modes.includes("gallery")) {
        const items = loadGallery(storageKey);
        if (!items.includes(dataUrl)) {
          items.unshift(dataUrl);
          // Keep max 50 items
          const trimmed = items.slice(0, 50);
          saveGallery(storageKey, trimmed);
          setGalleryItems(trimmed);
        }
      }

      setUploading(false);
    };
    reader.onerror = () => setUploading(false);
    reader.readAsDataURL(file);
  };

  const handleClear = () => {
    onChange("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleGallerySelect = (url: string) => {
    onChange(url);
    setGalleryOpen(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        {value && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-danger"
            onClick={handleClear}
          >
            Clear
          </Button>
        )}
      </div>

      {/* Mode tabs */}
      {modes.length > 1 && (
        <div className="flex gap-1">
          {modes.map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setActiveMode(mode)}
              className={`rounded-md border px-3 py-1 text-xs font-medium transition-colors ${
                activeMode === mode
                  ? "border-primary-600 bg-primary-50 text-primary-700"
                  : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
              }`}
            >
              {mode === "upload" ? "Upload" : mode === "url" ? "URL" : "Gallery"}
            </button>
          ))}
        </div>
      )}

      {/* Upload mode */}
      {activeMode === "upload" && (
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleFileSelect}
            className="block w-full text-sm text-slate-500 file:mr-3 file:rounded-md file:border-0 file:bg-primary-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-primary-700"
          />
          {uploading && <p className="mt-1 text-xs text-slate-500">Loading...</p>}
        </div>
      )}

      {/* URL mode */}
      {activeMode === "url" && (
        <Input
          type="url"
          value={value.startsWith("data:") ? "" : value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="https://example.com/media.jpg"
          className="text-sm"
        />
      )}

      {/* Gallery mode */}
      {activeMode === "gallery" && (
        <div>
          <Button type="button" variant="outline" size="sm" onClick={() => setGalleryOpen(true)}>
            Browse gallery ({galleryItems.length})
          </Button>
          <p className="mt-1 text-xs text-slate-500">
            Select from previously uploaded media. New uploads are automatically added to the
            gallery.
          </p>
        </div>
      )}

      {/* Help text */}
      {helpText && <p className="text-xs text-slate-500">{helpText}</p>}

      {/* Preview */}
      {value && previewType !== "none" && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
          {previewType === "image" && <img src={value} alt={label} className="max-h-40 rounded" />}
          {previewType === "audio" && <audio controls src={value} className="w-full" />}
          {previewType === "video" && (
            <video controls src={value} className="max-h-40 w-full rounded" />
          )}
        </div>
      )}

      {/* Gallery Modal */}
      <Modal
        open={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        title="Media Gallery"
        description="Select from previously uploaded media"
        size="xl"
      >
        {galleryItems.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-500">
            No media in gallery yet. Upload files first — they'll appear here automatically.
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
            {galleryItems.map((url, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleGallerySelect(url)}
                className="group relative aspect-square overflow-hidden rounded-md border border-slate-200 hover:border-primary-600"
              >
                {url.startsWith("data:image") || url.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i) ? (
                  <img src={url} alt={`Media ${i + 1}`} className="h-full w-full object-cover" />
                ) : url.startsWith("data:audio") || url.match(/\.(mp3|wav|ogg)$/i) ? (
                  <div className="flex h-full w-full items-center justify-center bg-slate-100 text-slate-400">
                    <span className="text-2xl">🎵</span>
                  </div>
                ) : url.startsWith("data:video") || url.match(/\.(mp4|webm|mov)$/i) ? (
                  <div className="flex h-full w-full items-center justify-center bg-slate-100 text-slate-400">
                    <span className="text-2xl">🎬</span>
                  </div>
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-slate-100 text-slate-400">
                    <span className="text-2xl">📄</span>
                  </div>
                )}
                <div className="absolute inset-0 flex items-center justify-center bg-primary-600/0 opacity-0 transition-all group-hover:bg-primary-600/20 group-hover:opacity-100">
                  <span className="rounded-md bg-white/90 px-2 py-1 text-xs font-medium text-primary-700">
                    Select
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
        <div className="mt-4 flex justify-end">
          <Button type="button" variant="outline" onClick={() => setGalleryOpen(false)}>
            Cancel
          </Button>
        </div>
      </Modal>
    </div>
  );
}
