import { describe, expect, it } from "vitest";

import type { PaymentConfig } from "@/api/payments";

import { formatPrice, hasOnlineGateway, isPaidAssessment } from "./takeAssessment";

const cfg = (over: Partial<PaymentConfig>): PaymentConfig => ({
  active_provider: "razorpay",
  is_active: false,
  is_stripe_configured: false,
  is_razorpay_configured: false,
  stripe_publishable_key: "",
  currency: "INR",
  ...over,
});

describe("formatPrice", () => {
  it("shows rupees without paise for whole amounts", () => {
    expect(formatPrice("500.00", "INR")).toBe("₹500");
  });

  it("keeps paise and Indian grouping", () => {
    expect(formatPrice("1250.5", "INR")).toBe("₹1,250.50");
  });

  it("defaults to INR", () => {
    expect(formatPrice(99)).toBe("₹99");
  });
});

describe("isPaidAssessment", () => {
  it("treats 0 / 0.00 as free", () => {
    expect(isPaidAssessment({ price: "0.00" })).toBe(false);
    expect(isPaidAssessment({ price: "0" })).toBe(false);
    expect(isPaidAssessment({ price: "10.00" })).toBe(true);
  });
});

describe("hasOnlineGateway", () => {
  it("is false with no gateway configured (admin-approval mode)", () => {
    expect(hasOnlineGateway(cfg({}))).toBe(false);
    expect(hasOnlineGateway(null)).toBe(false);
  });

  it("is true for an active, configured Razorpay", () => {
    expect(hasOnlineGateway(cfg({ is_razorpay_configured: true }))).toBe(true);
  });

  it("ignores a configured Razorpay that is not the active provider", () => {
    expect(hasOnlineGateway(cfg({ active_provider: "stripe", is_razorpay_configured: true }))).toBe(
      false,
    );
  });

  it("is true when Stripe is configured", () => {
    expect(hasOnlineGateway(cfg({ is_stripe_configured: true }))).toBe(true);
  });
});
