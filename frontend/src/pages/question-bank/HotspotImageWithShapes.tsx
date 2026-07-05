/**
 * HotspotImageWithShapes — renders a hotspot image with SVG shape overlay
 * that properly scales shapes to match the displayed image size.
 *
 * Uses the image_width/image_height saved on the Question (the dimensions
 * at draw time in the editor) as the SVG viewBox. With preserveAspectRatio="none",
 * the SVG coordinate system stretches to match the displayed image — so shapes
 * drawn at 600px wide will align correctly even when displayed at 400px wide.
 */
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
  const fillColor = (correct: boolean) =>
    correct ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.2)";
  const strokeColor = (correct: boolean) => (correct ? "#22c55e" : "#ef4444");

  // Use saved draw-time dimensions for the viewBox. This ensures shapes
  // align correctly regardless of the display size.
  // Fallback to 400x300 if not saved (old questions without the field).
  const vbW = drawWidth && drawWidth > 0 ? drawWidth : 400;
  const vbH = drawHeight && drawHeight > 0 ? drawHeight : 300;

  return (
    <div className="relative inline-block" style={{ maxWidth }}>
      <img
        src={imageUrl}
        alt="Hotspot"
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
                fontSize={Math.max(12, vbW / 40)}
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
