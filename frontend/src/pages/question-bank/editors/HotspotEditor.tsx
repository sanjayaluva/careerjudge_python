/**
 * Hotspot Editor — for types 5a (single), 5b (multi)
 *
 * Features:
 * 1. Image selection via MediaManager (upload, URL, gallery)
 * 2. Shape designer with 3 shape types:
 *    - Rectangle: click-drag to draw
 *    - Circle: click center, then drag radius
 *    - Custom polygon: click to add points, double-click or click first point to close
 *      Delete key undoes last point
 * 3. Each shape can be marked as correct or incorrect
 */
import { useRef, useState } from "react";
import { Button, Label, MediaManager } from "@/components/ui";
import { SCORING_TYPES } from "@/api/questionBank";

type ShapeType = "RECTANGLE" | "CIRCLE" | "POLYGON";

interface HotspotArea {
  x: number;
  y: number;
  width_px: number;
  height_px: number;
  area_size_code: string;
  sub_question_index?: number;
  shape_type: ShapeType;
  is_correct: boolean;
  radius?: number;
  points?: { x: number; y: number }[];
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
  const imgRef = useRef<HTMLImageElement>(null);
  const [drawMode, setDrawMode] = useState<ShapeType | null>(null);
  const [drawingArea, setDrawingArea] = useState<HotspotArea | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);

  // Convert mouse event to image-relative coordinates
  const getCoords = (e: React.MouseEvent): { x: number; y: number } => {
    const img = imgRef.current;
    if (!img) return { x: 0, y: 0 };
    const rect = img.getBoundingClientRect();
    return {
      x: Math.round(e.clientX - rect.left),
      y: Math.round(e.clientY - rect.top),
    };
  };

  const addArea = (shape: ShapeType) => {
    const newArea: HotspotArea = {
      x: 50,
      y: 50,
      width_px: shape === "RECTANGLE" ? 100 : 50,
      height_px: shape === "RECTANGLE" ? 100 : 50,
      area_size_code: "",
      shape_type: shape,
      is_correct: true,
      radius: shape === "CIRCLE" ? 50 : undefined,
      points: shape === "POLYGON" ? [] : undefined,
    };
    onChange({ ...data, areas: [...data.areas, newArea] });
  };

  const updateArea = (index: number, area: Partial<HotspotArea>) => {
    const newAreas = [...data.areas];
    newAreas[index] = { ...newAreas[index], ...area };
    onChange({ ...data, areas: newAreas });
  };

  const removeArea = (index: number) => {
    onChange({ ...data, areas: data.areas.filter((_, i) => i !== index) });
  };

  // Drawing handlers for the image overlay
  const handleImageMouseDown = (e: React.MouseEvent) => {
    if (!drawMode || !data.image_url) return;
    const coords = getCoords(e);
    setDragStart(coords);

    if (drawMode === "RECTANGLE") {
      setDrawingArea({
        x: coords.x,
        y: coords.y,
        width_px: 0,
        height_px: 0,
        area_size_code: "",
        shape_type: "RECTANGLE",
        is_correct: true,
      });
    } else if (drawMode === "CIRCLE") {
      setDrawingArea({
        x: coords.x,
        y: coords.y,
        width_px: 0,
        height_px: 0,
        area_size_code: "",
        shape_type: "CIRCLE",
        is_correct: true,
        radius: 0,
      });
    } else if (drawMode === "POLYGON") {
      // For polygon, each click adds a point to the current drawing
      const currentPoints = drawingArea?.points || [];
      const newPoints = [...currentPoints, coords];

      // Check if clicking near the first point to close the polygon
      if (currentPoints.length >= 3) {
        const first = currentPoints[0];
        const dist = Math.sqrt((coords.x - first.x) ** 2 + (coords.y - first.y) ** 2);
        if (dist < 10) {
          // Close polygon — finalize
          const minX = Math.min(...newPoints.map((p) => p.x));
          const minY = Math.min(...newPoints.map((p) => p.y));
          const maxX = Math.max(...newPoints.map((p) => p.x));
          const maxY = Math.max(...newPoints.map((p) => p.y));
          onChange({
            ...data,
            areas: [
              ...data.areas,
              {
                x: minX,
                y: minY,
                width_px: maxX - minX,
                height_px: maxY - minY,
                area_size_code: "",
                shape_type: "POLYGON",
                is_correct: true,
                points: newPoints,
              },
            ],
          });
          setDrawingArea(null);
          setDrawMode(null);
          return;
        }
      }

      setDrawingArea({
        x: 0,
        y: 0,
        width_px: 0,
        height_px: 0,
        area_size_code: "",
        shape_type: "POLYGON",
        is_correct: true,
        points: newPoints,
      });
    }
  };

  const handleImageMouseMove = (e: React.MouseEvent) => {
    if (!drawMode || !dragStart) return;
    const coords = getCoords(e);

    if (drawMode === "RECTANGLE" && drawingArea) {
      setDrawingArea({
        ...drawingArea,
        x: Math.min(dragStart.x, coords.x),
        y: Math.min(dragStart.y, coords.y),
        width_px: Math.abs(coords.x - dragStart.x),
        height_px: Math.abs(coords.y - dragStart.y),
      });
    } else if (drawMode === "CIRCLE" && drawingArea) {
      const radius = Math.sqrt((coords.x - dragStart.x) ** 2 + (coords.y - dragStart.y) ** 2);
      setDrawingArea({ ...drawingArea, radius: Math.round(radius) });
    }
  };

  const handleImageMouseUp = () => {
    if (drawMode === "RECTANGLE" && drawingArea && drawingArea.width_px > 5) {
      onChange({ ...data, areas: [...data.areas, drawingArea] });
    } else if (
      drawMode === "CIRCLE" &&
      drawingArea &&
      drawingArea.radius &&
      drawingArea.radius > 5
    ) {
      onChange({ ...data, areas: [...data.areas, drawingArea] });
    }
    // For POLYGON, mouseUp doesn't finalize — clicks add points, double-click closes
    if (drawMode !== "POLYGON") {
      setDrawingArea(null);
      setDragStart(null);
      setDrawMode(null);
    }
  };

  const handleImageDoubleClick = () => {
    if (drawMode === "POLYGON" && drawingArea?.points && drawingArea.points.length >= 3) {
      const points = drawingArea.points;
      const minX = Math.min(...points.map((p) => p.x));
      const minY = Math.min(...points.map((p) => p.y));
      const maxX = Math.max(...points.map((p) => p.x));
      const maxY = Math.max(...points.map((p) => p.y));
      onChange({
        ...data,
        areas: [
          ...data.areas,
          {
            ...drawingArea,
            x: minX,
            y: minY,
            width_px: maxX - minX,
            height_px: maxY - minY,
          },
        ],
      });
      setDrawingArea(null);
      setDrawMode(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Delete" && drawMode === "POLYGON" && drawingArea?.points) {
      e.preventDefault();
      const newPoints = drawingArea.points.slice(0, -1);
      if (newPoints.length === 0) {
        setDrawingArea(null);
        setDrawMode(null);
      } else {
        setDrawingArea({ ...drawingArea, points: newPoints });
      }
    }
    if (e.key === "Escape") {
      setDrawingArea(null);
      setDragStart(null);
      setDrawMode(null);
    }
  };

  return (
    <div className="space-y-4" tabIndex={0} onKeyDown={handleKeyDown}>
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

      {/* Image selection via MediaManager */}
      <div>
        <Label>Question image</Label>
        <MediaManager
          label="Hotspot image"
          accept="image/*"
          modes={["upload", "url", "gallery"]}
          value={data.image_url}
          onChange={(url) => onChange({ ...data, image_url: url })}
        />
        <p className="mt-1 text-xs text-slate-500">
          Upload or paste the image that candidates will click on.
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
        {(() => {
          const selected = SCORING_TYPES.find((s) => s.value === data.scoring_type);
          return selected?.description ? (
            <p className="mt-2 text-xs leading-relaxed text-slate-600">
              <span className="font-medium text-slate-700">How it works: </span>
              {selected.description}
            </p>
          ) : null;
        })()}
      </div>

      {/* Shape drawing tools */}
      {data.image_url && (
        <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-600">Draw hotspot:</span>
            <button
              type="button"
              onClick={() => {
                setDrawMode("RECTANGLE");
                setDrawingArea(null);
              }}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                drawMode === "RECTANGLE"
                  ? "border-primary-600 bg-primary-100 text-primary-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              ▭ Rectangle
            </button>
            <button
              type="button"
              onClick={() => {
                setDrawMode("CIRCLE");
                setDrawingArea(null);
              }}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                drawMode === "CIRCLE"
                  ? "border-primary-600 bg-primary-100 text-primary-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              ◯ Circle
            </button>
            <button
              type="button"
              onClick={() => {
                setDrawMode("POLYGON");
                setDrawingArea(null);
              }}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                drawMode === "POLYGON"
                  ? "border-primary-600 bg-primary-100 text-primary-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              ⬠ Custom shape
            </button>
            <Button type="button" variant="ghost" size="sm" onClick={() => addArea("RECTANGLE")}>
              + Add manually
            </Button>
          </div>
          {drawMode && (
            <p className="text-xs text-slate-500">
              {drawMode === "RECTANGLE" && "Click and drag on the image to draw a rectangle."}
              {drawMode === "CIRCLE" && "Click center, then drag to set radius."}
              {drawMode === "POLYGON" &&
                "Click to add points. Double-click or click first point to close. Delete key undoes last point."}
            </p>
          )}
        </div>
      )}

      {/* Image with drawing overlay */}
      {data.image_url && (
        <div className="relative inline-block">
          <img
            ref={imgRef}
            src={data.image_url}
            alt="Hotspot"
            className="max-w-full rounded-md border border-slate-300"
            style={{ cursor: drawMode ? "crosshair" : "default" }}
            onMouseDown={handleImageMouseDown}
            onMouseMove={handleImageMouseMove}
            onMouseUp={handleImageMouseUp}
            onDoubleClick={handleImageDoubleClick}
          />
          {/* SVG overlay for shapes */}
          <svg
            className="pointer-events-none absolute left-0 top-0 h-full w-full"
            style={{ overflow: "visible" }}
          >
            {/* Existing areas */}
            {data.areas.map((area, i) => (
              <g key={i}>
                {area.shape_type === "RECTANGLE" && (
                  <rect
                    x={area.x}
                    y={area.y}
                    width={area.width_px}
                    height={area.height_px}
                    fill={area.is_correct ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}
                    stroke={area.is_correct ? "#22c55e" : "#ef4444"}
                    strokeWidth="2"
                  />
                )}
                {area.shape_type === "CIRCLE" && (
                  <circle
                    cx={area.x}
                    cy={area.y}
                    r={area.radius || 50}
                    fill={area.is_correct ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}
                    stroke={area.is_correct ? "#22c55e" : "#ef4444"}
                    strokeWidth="2"
                  />
                )}
                {area.shape_type === "POLYGON" && area.points && (
                  <polygon
                    points={area.points.map((p) => `${p.x},${p.y}`).join(" ")}
                    fill={area.is_correct ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}
                    stroke={area.is_correct ? "#22c55e" : "#ef4444"}
                    strokeWidth="2"
                  />
                )}
                {/* Label */}
                <text
                  x={area.x + 4}
                  y={area.y - 4}
                  fill={area.is_correct ? "#22c55e" : "#ef4444"}
                  fontSize="12"
                  fontWeight="bold"
                >
                  {i + 1}
                  {area.is_correct ? " ✓" : " ✗"}
                </text>
              </g>
            ))}
            {/* Currently drawing shape */}
            {drawingArea?.shape_type === "RECTANGLE" && (
              <rect
                x={drawingArea.x}
                y={drawingArea.y}
                width={drawingArea.width_px}
                height={drawingArea.height_px}
                fill="rgba(59,130,246,0.2)"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="4"
              />
            )}
            {drawingArea?.shape_type === "CIRCLE" && (
              <circle
                cx={drawingArea.x}
                cy={drawingArea.y}
                r={drawingArea.radius || 0}
                fill="rgba(59,130,246,0.2)"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="4"
              />
            )}
            {drawingArea?.shape_type === "POLYGON" &&
              drawingArea.points &&
              drawingArea.points.length > 0 && (
                <>
                  <polyline
                    points={drawingArea.points.map((p) => `${p.x},${p.y}`).join(" ")}
                    fill="rgba(59,130,246,0.1)"
                    stroke="#3b82f6"
                    strokeWidth="2"
                    strokeDasharray="4"
                  />
                  {/* Draw points */}
                  {drawingArea.points.map((p, idx) => (
                    <circle key={idx} cx={p.x} cy={p.y} r="4" fill="#3b82f6" />
                  ))}
                  {/* First point indicator (for closing) */}
                  {drawingArea.points.length >= 3 && (
                    <circle
                      cx={drawingArea.points[0].x}
                      cy={drawingArea.points[0].y}
                      r="8"
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="2"
                    />
                  )}
                </>
              )}
          </svg>
        </div>
      )}

      {/* Hotspot areas list */}
      {data.areas.length > 0 && (
        <div className="space-y-2">
          <Label>Hotspot Areas ({data.areas.length})</Label>
          {data.areas.map((area, i) => (
            <div key={i} className="flex items-center gap-2 rounded-md border border-slate-200 p-2">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                  area.is_correct ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                }`}
              >
                {i + 1}
              </span>
              <span className="text-xs text-slate-600">
                {area.shape_type === "RECTANGLE" && `Rectangle ${area.width_px}×${area.height_px}`}
                {area.shape_type === "CIRCLE" && `Circle r=${area.radius || 50}`}
                {area.shape_type === "POLYGON" && `Polygon (${area.points?.length || 0} points)`}
                {" at "}({area.x}, {area.y})
              </span>
              <label className="flex items-center gap-1 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={area.is_correct}
                  onChange={(e) => updateArea(i, { is_correct: e.target.checked })}
                  className="h-3 w-3"
                />
                Correct
              </label>
              <button
                type="button"
                onClick={() => removeArea(i)}
                className="ml-auto rounded px-2 py-0.5 text-xs text-danger hover:bg-danger-50"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

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
            <svg className="pointer-events-none absolute left-0 top-0 h-full w-full">
              {data.areas.map((area, i) => (
                <g key={i}>
                  {area.shape_type === "RECTANGLE" && (
                    <rect
                      x={area.x}
                      y={area.y}
                      width={area.width_px}
                      height={area.height_px}
                      fill={area.is_correct ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.1)"}
                      stroke={area.is_correct ? "#22c55e" : "#ef4444"}
                      strokeWidth="2"
                    />
                  )}
                  {area.shape_type === "CIRCLE" && (
                    <circle
                      cx={area.x}
                      cy={area.y}
                      r={area.radius || 50}
                      fill={area.is_correct ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.1)"}
                      stroke={area.is_correct ? "#22c55e" : "#ef4444"}
                      strokeWidth="2"
                    />
                  )}
                  {area.shape_type === "POLYGON" && area.points && (
                    <polygon
                      points={area.points.map((p) => `${p.x},${p.y}`).join(" ")}
                      fill={area.is_correct ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.1)"}
                      stroke={area.is_correct ? "#22c55e" : "#ef4444"}
                      strokeWidth="2"
                    />
                  )}
                  <text
                    x={area.x + 4}
                    y={area.y - 4}
                    fill={area.is_correct ? "#22c55e" : "#ef4444"}
                    fontSize="12"
                    fontWeight="bold"
                  >
                    {i + 1}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Green = correct answer zone. Red = incorrect zone (distractor).{" "}
          {isMulti
            ? "Multi-hotspot: candidate selects multiple."
            : "Single hotspot: only one click evaluated."}
        </p>
      </div>
    </div>
  );
}
