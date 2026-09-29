import { describe, expect, it } from "vitest";

import { seededShuffle } from "./seededShuffle";

describe("seededShuffle", () => {
  const ids = [101, 102, 103, 104, 105, 106, 107, 108];

  it("is stable for a seed and keeps every item", () => {
    const a = seededShuffle(ids, 42);
    expect(seededShuffle(ids, 42)).toEqual(a);
    expect([...a].sort()).toEqual(ids);
  });

  it("actually reorders consecutive ids (Report 7 #17)", () => {
    const orders = new Set([1, 2, 3, 4, 5, 6].map((seed) => seededShuffle(ids, seed).join(",")));
    expect(orders.size).toBeGreaterThan(1);
    expect(orders.has(ids.join(","))).toBe(false);
  });
});
