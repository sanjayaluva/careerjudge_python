/**
 * H16/D8 §2.3 — countdown + time-gated Join-Session control, shared by
 * CounselingPage.tsx (counselee) and CounsellorDashboard.tsx (counsellor).
 *
 * Assumption (not admin-configurable in this milestone): the Join button is
 * enabled from JOIN_WINDOW_BEFORE_MIN minutes before the session's scheduled
 * start, and stays enabled until JOIN_WINDOW_AFTER_END_MIN minutes after its
 * scheduled end (falling back to a 1-hour session when no end time is
 * known) — a fixed live-delivery gate mirroring how most video-conferencing
 * tools open their waiting room shortly before the call.
 */
import { useEffect, useState } from "react";

export const JOIN_WINDOW_BEFORE_MIN = 10;
export const JOIN_WINDOW_AFTER_END_MIN = 15;

export interface JoinWindowState {
  /** Whether the Join Session button should be enabled right now. */
  canJoin: boolean;
  /** Human-readable countdown / status label. */
  label: string;
}

/** Pure function — easy to unit test without mocking timers. */
export function computeJoinWindow(
  nowMs: number,
  startTime?: string | null,
  endTime?: string | null,
): JoinWindowState {
  if (!startTime) return { canJoin: false, label: "" };

  const start = new Date(startTime).getTime();
  if (Number.isNaN(start)) return { canJoin: false, label: "" };
  const end = endTime && !Number.isNaN(new Date(endTime).getTime())
    ? new Date(endTime).getTime()
    : start + 60 * 60 * 1000;

  const opensAt = start - JOIN_WINDOW_BEFORE_MIN * 60 * 1000;
  const closesAt = end + JOIN_WINDOW_AFTER_END_MIN * 60 * 1000;
  const canJoin = nowMs >= opensAt && nowMs <= closesAt;

  let label: string;
  if (nowMs < opensAt) {
    label = `Join opens in ${formatDuration(opensAt - nowMs)}`;
  } else if (nowMs < start) {
    label = `Starting in ${formatDuration(start - nowMs)}`;
  } else if (nowMs <= closesAt) {
    label = "Session is live";
  } else {
    label = "Session window closed";
  }
  return { canJoin, label };
}

/** React hook: ticks every second so the countdown label stays live. */
export function useJoinWindow(
  startTime?: string | null,
  endTime?: string | null,
): JoinWindowState {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!startTime) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startTime]);

  return computeJoinWindow(now, startTime, endTime);
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}
