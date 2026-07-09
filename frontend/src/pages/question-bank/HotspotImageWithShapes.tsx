/**
 * HotspotImageWithShapes — renders a hotspot image with SVG shape overlay
 * that properly scales shapes to match the displayed image size.
 *
 * Uses the image_width/image_height saved on the Question (the dimensions
 * at draw time in the editor) as the SVG viewBox. With preserveAspectRatio="none",
 * the SVG coordinate system stretches to match the displayed image — so shapes
 * drawn at 600px wide will align correctly even when displayed at 400px wide.
 *
 * Falls back to loading the image's naturalWidth/naturalHeight if the saved
 * dimensions are not available (old questions).
 */
import { useState } from "react";

interface HotspotAreaData {
  id: number;
  x: number;
  y: number;
  width_px: number;
  height_px: number;
  shape_type: string;
  is_correct: boolean;
  radius: number | null;
  points: { x: number; y: number }[] | null;
}

interface HotspotImageWithShapesProps {
  imageUrl: string;
  areas: HotspotAreaData[];
  /** Image width at draw time (saved on Question.image_width) */
  drawWidth?: number | null;
  /** Image height at draw time (saved on Question.image_height) */
  drawHeight?: number | null;
  maxWidth?: number;
}

export function HotspotImageWithShapes({
  imageUrl,
  areas,
  drawWidth,
  drawHeight,
  maxWidth = 500,
}: HotspotImageWithShapesProps) {
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  const fillColor = (correct: boolean) =>
    correct ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.25)";
  const strokeColor = (correct: boolean) => (correct ? "#22c55e" : "#ef4444");

  // Use saved draw-time dimensions, or fall back to natural dimensions loaded
  // from the image itself, or 400x300 as last resort.
  const vbW = drawWidth && drawWidth > 0 ? drawWidth : naturalSize.w || 400;
  const vbH = drawHeight && drawHeight > 0 ? drawHeight : naturalSize.h || 300;

  const handleImgLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    if (img.naturalWidth > 0 && img.naturalHeight > 0) {
      setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
    }
  };

  return (
    <div className="relative inline-block" style={{ maxWidth }}>
      <img
        src={imageUrl}
        alt="Hotspot"
        onLoad={handleImgLoad}
        className="w-full rounded-md border border-slate-300"
        style={{ pointerEvents: "none", userSelect: "none", display: "block" }}
      />
      <svg
        className="pointer-events-none absolute left-0 top-0"
        width="100%"
        height="100%"
        viewBox={`0 0 ${vbW} ${vbH}`}
        preserveAspectRatio="none"
      >
        {areas.map((ha, i) => {
          const fill = fillColor(ha.is_correct);
          const stroke = strokeColor(ha.is_correct);
          return (
            <g key={ha.id}>
              {(ha.shape_type === "RECTANGLE" || !ha.shape_type) && (
                <rect
                  x={ha.x}
                  y={ha.y}
                  width={ha.width_px}
                  height={ha.height_px}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth="3"
                />
              )}
              {ha.shape_type === "CIRCLE" && (
                <circle
                  cx={ha.x}
                  cy={ha.y}
                  r={ha.radius || 50}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth="3"
                />
              )}
              {ha.shape_type === "POLYGON" && ha.points && (
                <polygon
                  points={ha.points.map((p) => `${p.x},${p.y}`).join(" ")}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth="3"
                />
              )}
              <text
                x={ha.x + 4}
                y={ha.y - 4}
                fill={stroke}
                fontSize={Math.max(14, vbW / 30)}
                fontWeight="bold"
              >
                {i + 1}
                {ha.is_correct ? " ✓" : " ✗"}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
