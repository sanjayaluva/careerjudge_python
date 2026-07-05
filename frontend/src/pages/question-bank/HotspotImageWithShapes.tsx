/**
 * HotspotImageWithShapes — renders a hotspot image with SVG shape overlay
 * that properly scales shapes to match the displayed image size.
 *
 * The shapes were drawn in the editor at a specific image display size
 * (max 600px wide). On the detail page, the image may be displayed at
 * a different size (max-w-md = 448px). This component:
 * 1. Loads the image to get its natural dimensions
 * 2. Calculates the scale factor between draw-time and display-time
 * 3. Renders the SVG with viewBox = natural dimensions + preserveAspectRatio="none"
 *    so shapes scale proportionally to the displayed image
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
  maxWidth?: number;
}

export function HotspotImageWithShapes({
  imageUrl,
  areas,
  maxWidth = 500,
}: HotspotImageWithShapesProps) {
  const [imgSize, setImgSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  const handleLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    if (w > 0 && h > 0) {
      setImgSize({ w, h });
    }
  };

  const fillColor = (correct: boolean) =>
    correct ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.2)";
  const strokeColor = (correct: boolean) => (correct ? "#22c55e" : "#ef4444");

  return (
    <div className="relative inline-block" style={{ maxWidth }}>
      <img
        src={imageUrl}
        alt="Hotspot"
        onLoad={handleLoad}
        className="w-full rounded-md border border-slate-300"
        style={{ pointerEvents: "none", userSelect: "none", display: "block" }}
      />
      {imgSize.w > 0 && (
        <svg
          className="pointer-events-none absolute left-0 top-0"
          width="100%"
          height="100%"
          viewBox={`0 0 ${imgSize.w} ${imgSize.h}`}
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
                    strokeWidth="2"
                  />
                )}
                {ha.shape_type === "CIRCLE" && (
                  <circle
                    cx={ha.x}
                    cy={ha.y}
                    r={ha.radius || 50}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth="2"
                  />
                )}
                {ha.shape_type === "POLYGON" && ha.points && (
                  <polygon
                    points={ha.points.map((p) => `${p.x},${p.y}`).join(" ")}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth="2"
                  />
                )}
                <text
                  x={ha.x + 4}
                  y={ha.y - 4}
                  fill={stroke}
                  fontSize={Math.max(12, imgSize.w / 40)}
                  fontWeight="bold"
                >
                  {i + 1}
                  {ha.is_correct ? " ✓" : " ✗"}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
