import { describe, expect, it } from "vitest";

import { canNavigateBackToSection, sectionDeliveryOrder } from "./navigationRules";

describe("sectionDeliveryOrder", () => {
  it("returns unique section ids in first-occurrence order", () => {
    expect(sectionDeliveryOrder([1, 1, 2, 2, 3])).toEqual([1, 2, 3]);
  });

  it("handles a single null section (no sections configured)", () => {
    expect(sectionDeliveryOrder([null, null])).toEqual([null]);
  });
});

describe("canNavigateBackToSection", () => {
  const order = sectionDeliveryOrder([1, 1, 2, 2, 3, 3]);

  it("FREE: allows backward navigation to any earlier section", () => {
    expect(canNavigateBackToSection("FREE", order, 3, 1)).toBe(true);
    expect(canNavigateBackToSection("FREE", order, 3, 2)).toBe(true);
    expect(canNavigateBackToSection("FREE", order, 2, 1)).toBe(true);
  });

  it("defaults to FREE when navigationRule is missing", () => {
    expect(canNavigateBackToSection(null, order, 3, 1)).toBe(true);
    expect(canNavigateBackToSection(undefined, order, 3, 1)).toBe(true);
  });

  it("NO_BACKWARD_QUESTION: blocks all backward movement, even within a section", () => {
    expect(canNavigateBackToSection("NO_BACKWARD_QUESTION", order, 2, 2)).toBe(false);
    expect(canNavigateBackToSection("NO_BACKWARD_QUESTION", order, 2, 1)).toBe(false);
  });

  it("NO_BACKWARD_SECTION: allows within-section but blocks any section crossing", () => {
    expect(canNavigateBackToSection("NO_BACKWARD_SECTION", order, 2, 2)).toBe(true);
    expect(canNavigateBackToSection("NO_BACKWARD_SECTION", order, 2, 1)).toBe(false);
    expect(canNavigateBackToSection("NO_BACKWARD_SECTION", order, 3, 1)).toBe(false);
  });

  it("PREV_SECTION: allows within-section and exactly one section back", () => {
    expect(canNavigateBackToSection("PREV_SECTION", order, 3, 3)).toBe(true);
    expect(canNavigateBackToSection("PREV_SECTION", order, 3, 2)).toBe(true);
    expect(canNavigateBackToSection("PREV_SECTION", order, 2, 1)).toBe(true);
  });

  it("PREV_SECTION: blocks reaching a section further back than the previous one", () => {
    expect(canNavigateBackToSection("PREV_SECTION", order, 3, 1)).toBe(false);
  });

  it("PREV_SECTION: blocks when a section id isn't in the delivery order", () => {
    expect(canNavigateBackToSection("PREV_SECTION", order, 3, 99)).toBe(false);
  });
});
