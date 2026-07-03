/**
 * FlashItemsEditor — for flash question types 1e, 1f, 2c, 2d.
 *
 * Lets the user add/edit/delete the list of items (text or images) that will
 * flash before the candidate during the assessment. Each item can be:
 *   - TEXT: a word/phrase the candidate must recall
 *   - IMAGE: an image the candidate must recall
 *
 * Also includes flash timing settings:
 *   - Flash interval (ms): how long each item is displayed
 *   - Flash display count: how many items are shown (randomly selected from the pool)
 *
 * Props:
 *   items: FlashItemData[] — the current list of flash items
 *   flashIntervalMs: string — flash interval in milliseconds
 *   flashDisplayCount: string — how many items to flash
 *   onChange: callback when items or settings change
 *   itemType: "TEXT" | "IMAGE" — whether this question type uses text or image
 *             flashes (determined by the question type: 1e/2c = TEXT, 1f/2d = IMAGE)
 */
import { Image as ImageIcon, Trash2, Type } from "lucide-react";

import { Input, Label, MediaManager } from "@/components/ui";
import { createEmptyFlashItem, type FlashItemData } from "./shared";

interface FlashItemsEditorProps {
  items: FlashItemData[];
  flashIntervalMs: string;
  flashDisplayCount: string;
  itemType: "TEXT" | "IMAGE";
  onChange: (data: {
    items: FlashItemData[];
    flashIntervalMs: string;
    flashDisplayCount: string;
  }) => void;
}

export function FlashItemsEditor({
  items,
  flashIntervalMs,
  flashDisplayCount,
  itemType,
  onChange,
}: FlashItemsEditorProps) {
  const addItem = () => {
    const newItem = createEmptyFlashItem(items.length, itemType);
    onChange({
      items: [...items, newItem],
      flashIntervalMs,
      flashDisplayCount,
    });
  };

  const updateItem = (index: number, updates: Partial<FlashItemData>) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], ...updates };
    onChange({ items: newItems, flashIntervalMs, flashDisplayCount });
  };

  const removeItem = (index: number) => {
    onChange({
      items: items.filter((_, i) => i !== index),
      flashIntervalMs,
      flashDisplayCount,
    });
  };

  return (
    <div className="space-y-4 rounded-md border border-amber-200 bg-amber-50/50 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">Flash Items</p>
          <p className="text-xs text-slate-600">
            These {itemType === "TEXT" ? "words/phrases" : "images"} will flash before the
            candidate. They must recall them to answer the questions.
          </p>
        </div>
        <button
          type="button"
          onClick={addItem}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          + Add flash {itemType === "TEXT" ? "word" : "image"}
        </button>
      </div>

      {/* Flash timing settings */}
      <div className="grid grid-cols-2 gap-3 rounded-md border border-slate-200 bg-white p-3">
        <div>
          <Label htmlFor="flashint">Flash interval (ms)</Label>
          <Input
            id="flashint"
            type="number"
            value={flashIntervalMs}
            onChange={(e) =>
              onChange({ items, flashIntervalMs: e.target.value, flashDisplayCount })
            }
            placeholder="e.g. 500"
          />
          <p className="mt-1 text-xs text-slate-500">
            How long each item is displayed (in milliseconds).
          </p>
        </div>
        <div>
          <Label htmlFor="flashcount">Flash display count</Label>
          <Input
            id="flashcount"
            type="number"
            value={flashDisplayCount}
            onChange={(e) =>
              onChange({ items, flashIntervalMs, flashDisplayCount: e.target.value })
            }
            placeholder="e.g. 10"
          />
          <p className="mt-1 text-xs text-slate-500">
            How many items are randomly selected and flashed.
          </p>
        </div>
      </div>

      {/* Flash items list */}
      {items.length === 0 ? (
        <p className="rounded-md border border-dashed border-slate-300 bg-white py-6 text-center text-sm text-slate-500">
          No flash items yet. Click "Add flash {itemType === "TEXT" ? "word" : "image"}" to create
          one.
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-medium text-amber-700">
                {i + 1}
              </span>
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  {itemType === "TEXT" ? (
                    <Type className="h-4 w-4 text-slate-400" />
                  ) : (
                    <ImageIcon className="h-4 w-4 text-slate-400" />
                  )}
                  <span className="text-xs font-medium text-slate-500">
                    {itemType === "TEXT" ? "Text item" : "Image item"} #{i + 1}
                  </span>
                </div>
                {itemType === "TEXT" ? (
                  <Input
                    value={item.text_value}
                    onChange={(e) => updateItem(i, { text_value: e.target.value })}
                    placeholder={`Enter word/phrase to flash (e.g. "Apple", "Paris")`}
                  />
                ) : (
                  <MediaManager
                    label="Flash image"
                    value={item.image_file ?? ""}
                    onChange={(url) => updateItem(i, { image_file: url || null })}
                  />
                )}
                {item.image_file && itemType === "IMAGE" && (
                  <img
                    src={item.image_file}
                    alt={`Flash item ${i + 1}`}
                    className="max-h-24 rounded border border-slate-200"
                  />
                )}
              </div>
              <button
                type="button"
                onClick={() => removeItem(i)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded text-danger hover:bg-danger-50"
                aria-label="Remove flash item"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {items.length > 0 && (
        <p className="text-xs text-slate-500">
          {items.length} flash {itemType === "TEXT" ? "word(s)" : "image(s)"} in the pool. The
          candidate will see {flashDisplayCount || "?"} of them, each for {flashIntervalMs || "?"}{" "}
          ms.
        </p>
      )}
    </div>
  );
}
