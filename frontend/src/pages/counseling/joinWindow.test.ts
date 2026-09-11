import { describe, expect, it } from "vitest";

import { JOIN_WINDOW_AFTER_END_MIN, JOIN_WINDOW_BEFORE_MIN, computeJoinWindow } from "./joinWindow";

const START = "2026-09-11T10:00:00Z";
const END = "2026-09-11T11:00:00Z";
const startMs = new Date(START).getTime();
const endMs = new Date(END).getTime();
const MIN = 60 * 1000;

describe("computeJoinWindow (H16/D8 §2.3 live-delivery gate)", () => {
  it("is not joinable and has no label when there's no start time", () => {
    expect(computeJoinWindow(Date.now(), null, null)).toEqual({ canJoin: false, label: "" });
    expect(computeJoinWindow(Date.now(), undefined, undefined)).toEqual({
      canJoin: false,
      label: "",
    });
  });

  it("is NOT joinable well before the join window opens", () => {
    const now = startMs - (JOIN_WINDOW_BEFORE_MIN + 30) * MIN;
    const { canJoin, label } = computeJoinWindow(now, START, END);
    expect(canJoin).toBe(false);
    expect(label).toContain("Join opens in");
  });

  it("is joinable inside the pre-start window (but not yet started)", () => {
    const now = startMs - (JOIN_WINDOW_BEFORE_MIN - 1) * MIN;
    const { canJoin, label } = computeJoinWindow(now, START, END);
    expect(canJoin).toBe(true);
    expect(label).toContain("Starting in");
  });

  it("is joinable exactly at the session start", () => {
    const { canJoin, label } = computeJoinWindow(startMs, START, END);
    expect(canJoin).toBe(true);
    expect(label).toBe("Session is live");
  });

  it("is joinable shortly after the scheduled end (grace period)", () => {
    const now = endMs + (JOIN_WINDOW_AFTER_END_MIN - 1) * MIN;
    const { canJoin, label } = computeJoinWindow(now, START, END);
    expect(canJoin).toBe(true);
    expect(label).toBe("Session is live");
  });

  it("closes the window after the grace period has elapsed", () => {
    const now = endMs + (JOIN_WINDOW_AFTER_END_MIN + 5) * MIN;
    const { canJoin, label } = computeJoinWindow(now, START, END);
    expect(canJoin).toBe(false);
    expect(label).toBe("Session window closed");
  });

  it("falls back to a 1-hour session when no end time is given", () => {
    const impliedEndMs = startMs + 60 * MIN;
    const now = impliedEndMs + (JOIN_WINDOW_AFTER_END_MIN - 1) * MIN;
    const { canJoin } = computeJoinWindow(now, START, null);
    expect(canJoin).toBe(true);
  });
});
