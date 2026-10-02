/**
 * Helpers for the candidate's "Take Assessment" flow (Report 9 #73/#75):
 * price formatting for the pay prompt and whether an online gateway is live.
 */
import type { PaymentConfig } from "@/api/payments";

/** The fields of an assessment the take flow needs (list rows and details both have them). */
export interface TakeableAssessment {
  id: number;
  title: string;
  price: string;
}

export function isPaidAssessment(a: Pick<TakeableAssessment, "price">): boolean {
  return Number(a.price) > 0;
}

/**
 * Format a price in the currency payments are taken in (Payment settings),
 * e.g. "₹500" or "₹1,250.50". Falls back to "<code> <amount>" for a code the
 * browser does not know.
 */
export function formatPrice(amount: string | number, currency = "INR"): string {
  const n = Number(amount);
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      minimumFractionDigits: Number.isInteger(n) ? 0 : 2,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `${currency} ${amount}`;
  }
}

/**
 * True when checkout can take the payment online (Razorpay as the active,
 * configured provider, or Stripe configured) — mirrors the checkout endpoint.
 * Otherwise a payment waits for CJ Admin to approve it (Admin › Payments).
 */
export function hasOnlineGateway(cfg: PaymentConfig | null | undefined): boolean {
  if (!cfg) return false;
  return (
    (cfg.active_provider === "razorpay" && cfg.is_razorpay_configured) || cfg.is_stripe_configured
  );
}
