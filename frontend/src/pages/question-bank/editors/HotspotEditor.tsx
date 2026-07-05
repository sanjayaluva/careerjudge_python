/**
 * Hotspot Editor — for types 5a (single), 5b (multi)
 *
 * Features:
 * 1. Image selection via MediaManager (upload, URL, gallery)
 * 2. Shape designer with 3 shape types drawn on an SVG overlay:
 *    - Rectangle: click-drag to draw
 *    - Circle: click center, then drag radius
 *    - Custom polygon: click to add points, double-click or click first point to close
 *      Delete key undoes last point
 * 3. Each shape can be marked as correct or incorrect
 * 4. Shapes are selectable, movable, and resizable after drawing
 *
 * Technical: The image is set as a CSS background-image on a div, with an SVG
 * overlay on top. This prevents the browser's native image drag behavior.
 */
import { useCallback, useRef, useState } from "react";
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
  const containerRef = useRef<HTMLDivElement>(null);
  const [drawMode, setDrawMode] = useState<ShapeType | null>(null);
  const [drawingArea, setDrawingArea] = useState<HotspotArea | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [selectedArea, setSelectedArea] = useState<number | null>(null);
  const [dragMode, setDragMode] = useState<"move" | "resize" | null>(null);
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  // Convert mouse event to container-relative coordinates
  const getCoords = useCallback((e: React.MouseEvent): { x: number; y: number } => {
    const container = containerRef.current;
    if (!container) return { x: 0, y: 0 };
    const rect = container.getBoundingClientRect();
    return {
      x: Math.round(e.clientX - rect.left),
      y: Math.round(e.clientY - rect.top),
    };
  }, []);

  // Handle image load to get displayed dimensions
  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    // Cap the display size to max 600px wide for the editor
    const maxW = 600;
    const naturalW = img.naturalWidth || img.offsetWidth;
    const naturalH = img.naturalHeight || img.offsetHeight;
    if (naturalW > maxW) {
      const scale = maxW / naturalW;
      setImageSize({ w: maxW, h: Math.round(naturalH * scale) });
    } else if (naturalW > 0 && naturalH > 0) {
      setImageSize({ w: naturalW, h: naturalH });
    }
  };

  const addManualArea = (shape: ShapeType) => {
    const newArea: HotspotArea = {
      x: 20,
      y: 20,
      width_px: shape === "RECTANGLE" ? 80 : 60,
      height_px: shape === "RECTANGLE" ? 80 : 60,
      area_size_code: "",
      shape_type: shape,
      is_correct: true,
      radius: shape === "CIRCLE" ? 40 : undefined,
      points:
        shape === "POLYGON"
          ? [
              { x: 20, y: 20 },
              { x: 80, y: 20 },
              { x: 80, y: 80 },
              { x: 20, y: 80 },
            ]
          : undefined,
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
    if (selectedArea === index) setSelectedArea(null);
  };

  // --- Drawing handlers ---
  const handleOverlayMouseDown = (e: React.MouseEvent) => {
    // Only handle left clicks
    if (e.button !== 0) return;

    // If clicking on an existing shape (for select/move), handle separately
    const target = e.target as SVGElement;
    const shapeIdx = target.getAttribute("data-shape-idx");
    const handle = target.getAttribute("data-handle");

    if (shapeIdx !== null && shapeIdx !== undefined) {
      const idx = parseInt(shapeIdx);
      setSelectedArea(idx);
      if (handle) {
        setDragMode("resize");
        setResizeHandle(handle);
      } else {
        setDragMode("move");
      }
      setDragStart(getCoords(e));
      e.preventDefault();
      return;
    }

    // If in draw mode, start drawing
    if (!drawMode) {
      setSelectedArea(null);
      return;
    }

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
      const currentPoints = drawingArea?.points || [];
      // Check if clicking near the first point to close
      if (currentPoints.length >= 3) {
        const first = currentPoints[0];
        const dist = Math.sqrt((coords.x - first.x) ** 2 + (coords.y - first.y) ** 2);
        if (dist < 12) {
          const minX = Math.min(...currentPoints.map((p) => p.x));
          const minY = Math.min(...currentPoints.map((p) => p.y));
          const maxX = Math.max(...currentPoints.map((p) => p.x));
          const maxY = Math.max(...currentPoints.map((p) => p.y));
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
                points: currentPoints,
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
        points: [...currentPoints, coords],
      });
    }
    e.preventDefault();
  };

  const handleOverlayMouseMove = (e: React.MouseEvent) => {
    const coords = getCoords(e);

    // Handle moving/resizing existing shape
    if (dragMode && selectedArea !== null && dragStart) {
      const dx = coords.x - dragStart.x;
      const dy = coords.y - dragStart.y;
      const area = data.areas[selectedArea];

      if (dragMode === "move") {
        if (area.shape_type === "RECTANGLE" || area.shape_type === "CIRCLE") {
          updateArea(selectedArea, { x: area.x + dx, y: area.y + dy });
        } else if (area.shape_type === "POLYGON" && area.points) {
          updateArea(selectedArea, {
            points: area.points.map((p) => ({ x: p.x + dx, y: p.y + dy })),
            x: area.x + dx,
            y: area.y + dy,
          });
        }
      } else if (dragMode === "resize" && resizeHandle) {
        if (area.shape_type === "RECTANGLE") {
          let { x, y, width_px, height_px } = area;
          if (resizeHandle.includes("e")) width_px = Math.max(10, area.width_px + dx);
          if (resizeHandle.includes("s")) height_px = Math.max(10, area.height_px + dy);
          if (resizeHandle.includes("w")) {
            x = area.x + dx;
            width_px = Math.max(10, area.width_px - dx);
          }
          if (resizeHandle.includes("n")) {
            y = area.y + dy;
            height_px = Math.max(10, area.height_px - dy);
          }
          updateArea(selectedArea, { x, y, width_px, height_px });
        } else if (area.shape_type === "CIRCLE") {
          const newRadius = Math.max(10, (area.radius || 50) + dx);
          updateArea(selectedArea, {
            radius: newRadius,
            width_px: newRadius * 2,
            height_px: newRadius * 2,
          });
        }
      }
      setDragStart(coords);
      return;
    }

    // Handle drawing new shape
    if (!drawMode || !dragStart) return;

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

  const handleOverlayMouseUp = () => {
    // Finalize drawing
    if (drawMode === "RECTANGLE" && drawingArea && drawingArea.width_px > 5) {
      onChange({ ...data, areas: [...data.areas, drawingArea] });
      setDrawingArea(null);
      setDragStart(null);
      setDrawMode(null);
    } else if (
      drawMode === "CIRCLE" &&
      drawingArea &&
      drawingArea.radius &&
      drawingArea.radius > 5
    ) {
      onChange({ ...data, areas: [...data.areas, drawingArea] });
      setDrawingArea(null);
      setDragStart(null);
      setDrawMode(null);
    }
    // For POLYGON, mouseUp doesn't finalize — clicks add points

    // End move/resize
    setDragMode(null);
    setResizeHandle(null);
    setDragStart(null);
  };

  const handleOverlayDoubleClick = () => {
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
          { ...drawingArea, x: minX, y: minY, width_px: maxX - minX, height_px: maxY - minY },
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
      setSelectedArea(null);
    }
    // Delete selected shape with Delete key (when not in polygon draw mode)
    if (e.key === "Delete" && !drawMode && selectedArea !== null) {
      e.preventDefault();
      removeArea(selectedArea);
    }
  };

  // Render resize handles for selected shape
  const renderResizeHandles = (area: HotspotArea, idx: number) => {
    if (selectedArea !== idx) return null;
    const handles: { name: string; x: number; y: number }[] = [];

    if (area.shape_type === "RECTANGLE") {
      handles.push(
        { name: "nw", x: area.x, y: area.y },
        { name: "ne", x: area.x + area.width_px, y: area.y },
        { name: "sw", x: area.x, y: area.y + area.height_px },
        { name: "se", x: area.x + area.width_px, y: area.y + area.height_px },
      );
    } else if (area.shape_type === "CIRCLE") {
      const r = area.radius || 50;
      handles.push(
        { name: "n", x: area.x, y: area.y - r },
        { name: "s", x: area.x, y: area.y + r },
        { name: "e", x: area.x + r, y: area.y },
        { name: "w", x: area.x - r, y: area.y },
      );
    }

    return handles.map((h) => (
      <rect
        key={h.name}
        x={h.x - 5}
        y={h.y - 5}
        width={10}
        height={10}
        fill="#3b82f6"
        stroke="white"
        strokeWidth={1.5}
        style={{ cursor: "pointer" }}
        data-shape-idx={idx}
        data-handle={h.name}
      />
    ));
  };

  const fillColor = (area: HotspotArea) =>
    area.is_correct ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.2)";
  const strokeColor = (area: HotspotArea) => (area.is_correct ? "#22c55e" : "#ef4444");

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
                setSelectedArea(null);
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
                setSelectedArea(null);
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
                setSelectedArea(null);
              }}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                drawMode === "POLYGON"
                  ? "border-primary-600 bg-primary-100 text-primary-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              ⬠ Custom shape
            </button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => addManualArea("RECTANGLE")}
            >
              + Add manually
            </Button>
            {drawMode && (
              <button
                type="button"
                onClick={() => {
                  setDrawMode(null);
                  setDrawingArea(null);
                }}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-50"
              >
                ✕ Cancel draw
              </button>
            )}
          </div>
          {drawMode && (
            <p className="text-xs text-slate-500">
              {drawMode === "RECTANGLE" && "Click and drag on the image to draw a rectangle."}
              {drawMode === "CIRCLE" && "Click center, then drag to set radius."}
              {drawMode === "POLYGON" &&
                "Click to add points. Double-click or click first point to close. Delete = undo last point."}
            </p>
          )}
          {!drawMode && (
            <p className="text-xs text-slate-500">
              Click a shape tool to draw, or click an existing shape to select/move/resize it.
              Delete key removes selected shape. Esc cancels.
            </p>
          )}
        </div>
      )}

      {/* Image with SVG drawing overlay — image is a CSS background to prevent drag */}
      {data.image_url && imageSize.w > 0 && (
        <div
          ref={containerRef}
          className="relative inline-block"
          style={{
            backgroundImage: `url(${data.image_url})`,
            backgroundRepeat: "no-repeat",
            backgroundSize: "100% 100%",
            width: imageSize.w,
            height: imageSize.h,
            cursor: drawMode ? "crosshair" : "default",
            userSelect: "none",
          }}
          onMouseDown={handleOverlayMouseDown}
          onMouseMove={handleOverlayMouseMove}
          onMouseUp={handleOverlayMouseUp}
          onMouseLeave={handleOverlayMouseUp}
          onDoubleClick={handleOverlayDoubleClick}
        >
          {/* SVG overlay for shapes — pointer-events: all so we can interact */}
          <svg
            className="absolute left-0 top-0"
            width={imageSize.w}
            height={imageSize.h}
            style={{ pointerEvents: "all" }}
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
                    fill={fillColor(area)}
                    stroke={strokeColor(area)}
                    strokeWidth={selectedArea === i ? 3 : 2}
                    strokeDasharray={selectedArea === i ? "0" : "0"}
                    style={{ cursor: drawMode ? "crosshair" : "move" }}
                    data-shape-idx={i}
                  />
                )}
                {area.shape_type === "CIRCLE" && (
                  <circle
                    cx={area.x}
                    cy={area.y}
                    r={area.radius || 50}
                    fill={fillColor(area)}
                    stroke={strokeColor(area)}
                    strokeWidth={selectedArea === i ? 3 : 2}
                    style={{ cursor: drawMode ? "crosshair" : "move" }}
                    data-shape-idx={i}
                  />
                )}
                {area.shape_type === "POLYGON" && area.points && (
                  <polygon
                    points={area.points.map((p) => `${p.x},${p.y}`).join(" ")}
                    fill={fillColor(area)}
                    stroke={strokeColor(area)}
                    strokeWidth={selectedArea === i ? 3 : 2}
                    style={{ cursor: drawMode ? "crosshair" : "move" }}
                    data-shape-idx={i}
                  />
                )}
                {/* Label */}
                <text
                  x={area.x + (area.shape_type === "CIRCLE" ? 0 : 4)}
                  y={area.y - (area.shape_type === "CIRCLE" ? (area.radius || 50) - 5 : 4)}
                  fill={strokeColor(area)}
                  fontSize="14"
                  fontWeight="bold"
                  style={{ pointerEvents: "none" }}
                >
                  {i + 1}
                  {area.is_correct ? " ✓" : " ✗"}
                </text>
                {/* Resize handles */}
                {renderResizeHandles(area, i)}
              </g>
            ))}

            {/* Currently drawing shape (blue dashed) */}
            {drawingArea?.shape_type === "RECTANGLE" && (
              <rect
                x={drawingArea.x}
                y={drawingArea.y}
                width={drawingArea.width_px}
                height={drawingArea.height_px}
                fill="rgba(59,130,246,0.2)"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="5"
                style={{ pointerEvents: "none" }}
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
                strokeDasharray="5"
                style={{ pointerEvents: "none" }}
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
                    strokeDasharray="5"
                    style={{ pointerEvents: "none" }}
                  />
                  {drawingArea.points.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={p.x}
                      cy={p.y}
                      r={4}
                      fill="#3b82f6"
                      style={{ pointerEvents: "none" }}
                    />
                  ))}
                  {drawingArea.points.length >= 3 && (
                    <circle
                      cx={drawingArea.points[0].x}
                      cy={drawingArea.points[0].y}
                      r={8}
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="2"
                      style={{ pointerEvents: "none" }}
                    />
                  )}
                </>
              )}
          </svg>
        </div>
      )}

      {/* Load image to get dimensions (shown until loaded) */}
      {data.image_url && imageSize.w === 0 && (
        <img
          src={data.image_url}
          alt="Loading..."
          onLoad={handleImageLoad}
          className="max-w-full rounded-md border border-slate-300"
        />
      )}

      {/* Hotspot areas list */}
      {data.areas.length > 0 && (
        <div className="space-y-2">
          <Label>Hotspot Areas ({data.areas.length})</Label>
          {data.areas.map((area, i) => (
            <div
              key={i}
              className={`flex items-center gap-2 rounded-md border p-2 ${
                selectedArea === i ? "border-primary-400 bg-primary-50" : "border-slate-200"
              }`}
              onClick={() => setSelectedArea(i)}
            >
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
                {area.shape_type === "POLYGON" && `Polygon (${area.points?.length || 0} pts)`}
                {" at ("}
                {area.x}, {area.y})
              </span>
              <label
                className="flex items-center gap-1 text-xs text-slate-600"
                onClick={(e) => e.stopPropagation()}
              >
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
                onClick={(e) => {
                  e.stopPropagation();
                  removeArea(i);
                }}
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
              style={{ userSelect: "none", pointerEvents: "none" }}
            />
            <svg
              className="pointer-events-none absolute left-0 top-0"
              width="100%"
              height="100%"
              viewBox={`0 0 ${imageSize.w || 400} ${imageSize.h || 300}`}
              preserveAspectRatio="xMidYMid meet"
            >
              {data.areas.map((area, i) => (
                <g key={i}>
                  {area.shape_type === "RECTANGLE" && (
                    <rect
                      x={area.x}
                      y={area.y}
                      width={area.width_px}
                      height={area.height_px}
                      fill={fillColor(area)}
                      stroke={strokeColor(area)}
                      strokeWidth="2"
                    />
                  )}
                  {area.shape_type === "CIRCLE" && (
                    <circle
                      cx={area.x}
                      cy={area.y}
                      r={area.radius || 50}
                      fill={fillColor(area)}
                      stroke={strokeColor(area)}
                      strokeWidth="2"
                    />
                  )}
                  {area.shape_type === "POLYGON" && area.points && (
                    <polygon
                      points={area.points.map((p) => `${p.x},${p.y}`).join(" ")}
                      fill={fillColor(area)}
                      stroke={strokeColor(area)}
                      strokeWidth="2"
                    />
                  )}
                  <text
                    x={area.x + 4}
                    y={area.y - 4}
                    fill={strokeColor(area)}
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
