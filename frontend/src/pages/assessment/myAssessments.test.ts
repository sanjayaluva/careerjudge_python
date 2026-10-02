import { describe, expect, it } from "vitest";

import { isMine } from "./myAssessments";

describe("isMine (Report 9 #72)", () => {
  it("follows the server's unlocked flag", () => {
    expect(isMine({ price: "500.00", is_unlocked: true })).toBe(true);
    expect(isMine({ price: "500.00", is_unlocked: false })).toBe(false);
    expect(isMine({ price: "0.00", is_unlocked: true })).toBe(true);
  });

  it("keeps an assessment already begun, even if unpaid", () => {
    expect(isMine({ price: "500.00", is_unlocked: false }, true)).toBe(true);
  });

  it("falls back to free = mine when the flag is missing", () => {
    expect(isMine({ price: "0.00" })).toBe(true);
    expect(isMine({ price: "250.00" })).toBe(false);
  });
});
