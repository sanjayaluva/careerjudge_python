import { beforeEach, describe, expect, it } from "vitest";

import { clearPaymentReturn, readPaymentReturn, stashPaymentReturn } from "./paymentReturn";

beforeEach(() => sessionStorage.clear());

describe("payment return path", () => {
  it("round-trips a stashed path", () => {
    stashPaymentReturn("/assessments/7/start", "Continue to the assessment");
    expect(readPaymentReturn()).toEqual({
      path: "/assessments/7/start",
      label: "Continue to the assessment",
    });
    clearPaymentReturn();
    expect(readPaymentReturn()).toBeNull();
  });

  it("refuses paths that leave the site", () => {
    stashPaymentReturn("//evil.example/x", "x");
    expect(readPaymentReturn()).toBeNull();
    stashPaymentReturn("https://evil.example/x", "x");
    expect(readPaymentReturn()).toBeNull();
  });

  it("ignores a stale stash", () => {
    stashPaymentReturn("/assessments/7/start", "Continue");
    expect(readPaymentReturn(Date.now() + 3 * 60 * 60 * 1000)).toBeNull();
  });
});
