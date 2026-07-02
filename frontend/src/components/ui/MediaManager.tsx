/**
 * Media Manager — reusable component for media field selection.
 *
 * Supports 3 modes (configurable per use case):
 * 1. Upload from user machine (file input → upload to backend)
 * 2. Select from already uploaded medias (gallery)
 * 3. Provide remote URL
 *
 * Usage:
 * <MediaManager
 *   label="Question image"
 *   accept="image/*"
 *   modes={["upload", "url"]}
 *   value={imageUrl}
 *   onChange={(url) => setImageUrl(url)}
 * />
 *
 * For now, upload mode stores the file as a data URL (base64) for preview.
 * Phase 2b will add a proper file upload endpoint.
 */
import { useRef, useState } from "react";
import { Button, Input, Label } from "@/components/ui";

export interface MediaManagerProps {
  label: string;
  accept?: string; // e.g. "image/*", "audio/*", "video/*", ".pdf,.doc"
  modes?: ("upload" | "url")[]; // which modes to show
  value: string; // current URL or data URL
  onChange: (value: string) => void;
  previewType?: "image" | "audio" | "video" | "none";
  helpText?: string;
}

export function MediaManager({
  label,
  accept = "image/*",
  modes = ["upload", "url"],
  value,
  onChange,
  previewType = "image",
  helpText,
}: MediaManagerProps) {
  const [activeMode, setActiveMode] = useState<string>(modes[0] ?? "url");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    // For now, convert to data URL for preview.
    // Phase 2b will upload to backend and return a URL.
    const reader = new FileReader();
    reader.onload = () => {
      onChange(reader.result as string);
      setUploading(false);
    };
    reader.onerror = () => {
      setUploading(false);
    };
    reader.readAsDataURL(file);
  };

  const handleClear = () => {
    onChange("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
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
              {mode === "upload" ? "Upload" : "URL"}
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
    </div>
  );
}
