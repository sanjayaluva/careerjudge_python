/**
 * HotspotImageWithShapes — renders a hotspot image with SVG shape overlay
 * that properly scales shapes to match the displayed image size.
 *
 * Uses the image_width/image_height saved on the Question (the dimensions
 * at draw time in the editor) as the SVG viewBox. With preserveAspectRatio="none",
 * the SVG coordinate system stretches to match the displayed image.
 *
 * If saved dimensions are not available (old questions), loads the image
 * and uses its rendered offsetWidth/offsetHeight as the viewBox.
 */
import { useRef, useState } from "react";

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
  drawWidth?: number | null;
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
  const imgRef = useRef<HTMLImageElement>(null);
  const [renderedSize, setRenderedSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  const fillColor = (correct: boolean) =>
    correct ? "rgba(34,197,94,0.35)" : "rgba(239,68,68,0.25)";
  const strokeColor = (correct: boolean) => (correct ? "#22c55e" : "#ef4444");

  // Use saved draw-time dimensions, or fall back to rendered dimensions
  const vbW = drawWidth && drawWidth > 0 ? drawWidth : renderedSize.w || 400;
  const vbH = drawHeight && drawHeight > 0 ? drawHeight : renderedSize.h || 300;

  const handleImgLoad = () => {
    const img = imgRef.current;
    if (img && img.offsetWidth > 0 && img.offsetHeight > 0) {
      setRenderedSize({ w: img.offsetWidth, h: img.offsetHeight });
    }
  };

  return (
    <div className="relative inline-block" style={{ maxWidth }}>
      <img
        ref={imgRef}
        src={imageUrl}
        alt="Hotspot"
        onLoad={handleImgLoad}
        className="w-full rounded-md border border-slate-300"
        style={{ pointerEvents: "none", userSelect: "none", display: "block" }}
      />
      {/* SVG overlay — only render once we have valid dimensions */}
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
