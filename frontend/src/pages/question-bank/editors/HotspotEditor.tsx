/**
 * Hotspot Editor — for types 5a (single), 5b (multi)
 * Define hotspot areas on the question image.
 */
import { Input, Label } from "@/components/ui";
import { Button } from "@/components/ui";

interface HotspotArea {
  x: number;
  y: number;
  width_px: number;
  height_px: number;
  area_size_code: string;
}

interface HotspotEditorProps {
  questionType: string;
  data: {
    question_text_1: string;
    image_url: string;
    scoring_type: string;
    areas: HotspotArea[];
  };
  onChange: (data: HotspotEditorProps["data"]) => void;
}

export function HotspotEditor({ questionType, data, onChange }: HotspotEditorProps) {
  const isMulti = questionType === "HOTSPOT_MULTI";

  const addArea = () => {
    onChange({
      ...data,
      areas: [...data.areas, { x: 50, y: 50, width_px: 100, height_px: 100, area_size_code: "" }],
    });
  };

  const updateArea = (index: number, area: HotspotArea) => {
    const newAreas = [...data.areas];
    newAreas[index] = area;
    onChange({ ...data, areas: newAreas });
  };

  const removeArea = (index: number) => {
    onChange({ ...data, areas: data.areas.filter((_, i) => i !== index) });
  };

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Question text
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder="Click on the correct area in the image..."
        />
      </div>

      <div>
        <Label htmlFor="imgurl">Question image URL</Label>
        <Input
          id="imgurl"
          value={data.image_url}
          onChange={(e) => onChange({ ...data, image_url: e.target.value })}
          placeholder="https://example.com/image.png (upload in Phase 2b)"
        />
        <p className="mt-1 text-xs text-slate-500">
          For now, enter a URL. Image upload will be added in Phase 2b. At delivery time, the
          candidate sees this image and clicks on it.
        </p>
      </div>

      <div>
        <Label>Scoring type</Label>
        <select
          className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.scoring_type}
          onChange={(e) => onChange({ ...data, scoring_type: e.target.value })}
        >
          <option value="BINARY">Binary (single hotspot: 5a)</option>
          <option value="NEGATIVE">Negative marking (multi hotspot: 5b)</option>
        </select>
      </div>

      {/* Hotspot areas */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>Hotspot Areas (correct click zones)</Label>
          <Button type="button" variant="outline" size="sm" onClick={addArea}>
            + Add hotspot
          </Button>
        </div>
        {data.areas.map((area, i) => (
          <div key={i} className="space-y-2 rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Hotspot {i + 1}</span>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger hover:bg-danger-50"
                onClick={() => removeArea(i)}
              >
                Remove
              </Button>
            </div>
            <div className="grid grid-cols-4 gap-2">
              <div>
                <Label className="text-xs text-slate-500">X (px)</Label>
                <Input
                  type="number"
                  value={area.x}
                  onChange={(e) => updateArea(i, { ...area, x: parseInt(e.target.value) || 0 })}
                  className="text-xs"
                />
              </div>
              <div>
                <Label className="text-xs text-slate-500">Y (px)</Label>
                <Input
                  type="number"
                  value={area.y}
                  onChange={(e) => updateArea(i, { ...area, y: parseInt(e.target.value) || 0 })}
                  className="text-xs"
                />
              </div>
              <div>
                <Label className="text-xs text-slate-500">Width (px)</Label>
                <Input
                  type="number"
                  value={area.width_px}
                  onChange={(e) =>
                    updateArea(i, { ...area, width_px: parseInt(e.target.value) || 0 })
                  }
                  className="text-xs"
                />
              </div>
              <div>
                <Label className="text-xs text-slate-500">Height (px)</Label>
                <Input
                  type="number"
                  value={area.height_px}
                  onChange={(e) =>
                    updateArea(i, { ...area, height_px: parseInt(e.target.value) || 0 })
                  }
                  className="text-xs"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-2 text-sm text-slate-900">
          {data.question_text_1 || "(no question text)"}
        </p>
        {data.image_url && (
          <div className="relative inline-block">
            <img
              src={data.image_url}
              alt="Question"
              className="max-w-md rounded-md border border-slate-300"
            />
            {data.areas.map((area, i) => (
              <div
                key={i}
                className="absolute border-2 border-success-500 bg-success-500/20"
                style={{
                  left: `${area.x}px`,
                  top: `${area.y}px`,
                  width: `${area.width_px}px`,
                  height: `${area.height_px}px`,
                }}
              >
                <span className="absolute -top-5 left-0 text-xs text-success-600">#{i + 1}</span>
              </div>
            ))}
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          {isMulti
            ? "Multi-hotspot: candidate can select multiple areas. Negative marking applies."
            : "Single hotspot: only the LATEST click is evaluated."}
        </p>
      </div>
    </div>
  );
}
