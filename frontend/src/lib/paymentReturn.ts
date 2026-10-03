/**
 * Where to send the user back after an online (Stripe) payment.
 *
 * Stripe returns to the generic /payments/success page, which used to offer
 * only "Go to Dashboard" — the candidate then had to find the assessment
 * again. Before redirecting to Stripe the page that started the payment
 * stashes its own path here (per tab, sessionStorage); the success page
 * reads it and offers "Continue to the assessment".
 */
const KEY = "cj_payment_return_v1";
/** A stash older than this is ignored (an abandoned earlier payment). */
const MAX_AGE_MS = 2 * 60 * 60 * 1000;

export interface PaymentReturn {
  path: string;
  label: string;
}

/** Only same-site paths ("/x", never "//host" or "https://…"). */
function isLocalPath(path: unknown): path is string {
  return typeof path === "string" && path.startsWith("/") && !path.startsWith("//");
}

export function stashPaymentReturn(path: string, label: string): void {
  if (!isLocalPath(path)) return;
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ path, label, at: Date.now() }));
  } catch {
    // storage unavailable — the success page falls back to the dashboard
  }
}

export function readPaymentReturn(now: number = Date.now()): PaymentReturn | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { path?: unknown; label?: unknown; at?: unknown };
    if (!isLocalPath(parsed.path) || typeof parsed.label !== "string") return null;
    if (typeof parsed.at !== "number" || now - parsed.at > MAX_AGE_MS) return null;
    return { path: parsed.path, label: parsed.label };
  } catch {
    return null;
  }
}

export function clearPaymentReturn(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
