/**
 * Corporate portal branding helpers (Report 9 #48/#49/#95): the company logo
 * (or its initial when no logo is set or it fails to load) and a readable text
 * colour for the portal's primary colour.
 */
import { useState } from "react";

import { resolveLogoSrc } from "@/api/organizations";
import { cn } from "@/lib/utils";

/** Black or white, whichever reads better on `hex` (WCAG relative luminance). */
export function textOn(hex: string): "#ffffff" | "#0f172a" {
  const m = /^#?([0-9a-f]{6}|[0-9a-f]{3})/i.exec(hex ?? "");
  if (!m) return "#ffffff";
  const h = m[1].length === 3 ? [...m[1]].map((c) => c + c).join("") : m[1];
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  // Contrast against white vs. against slate-900 (luminance ~0.008).
  const onWhite = 1.05 / (luminance + 0.05);
  const onDark = (luminance + 0.05) / 0.058;
  return onDark > onWhite ? "#0f172a" : "#ffffff";
}

/** The company logo at `size` px high (up to 4x as wide), or its initial. */
export function PortalLogo({
  src,
  name,
  color,
  size = 40,
  className,
}: {
  src: string | null | undefined;
  name: string;
  color: string;
  size?: number;
  className?: string;
}) {
  // Remember which URL failed, so a newly uploaded logo gets a fresh try.
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const url = resolveLogoSrc(src);
  if (url && url !== failedUrl) {
    return (
      <img
        src={url}
        alt={`${name} logo`}
        className={cn("object-contain", className)}
        style={{ height: size, maxWidth: size * 4 }}
        onError={() => setFailedUrl(url)}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md font-bold",
        className,
      )}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.45,
        backgroundColor: color,
        color: textOn(color),
      }}
    >
      {(name.trim()[0] ?? "?").toUpperCase()}
    </span>
  );
}
