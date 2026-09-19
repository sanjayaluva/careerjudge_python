/**
 * Payments API client.
 */
import { apiGet, apiPost } from "./client";

const BASE = "/payments";

export interface PaymentConfig {
  active_provider: string;
  is_active: boolean;
  is_stripe_configured: boolean;
  is_razorpay_configured: boolean;
  stripe_publishable_key: string;
  currency: string;
}

export interface RazorpayOrder {
  order_id: string;
  key_id: string;
  amount: number;
  currency: string;
  name: string;
}

export interface CheckoutResponse {
  checkout_url?: string;
  status?: "free" | "paid" | "manual" | "pending";
  /** E-PLT-4: present when Razorpay is the active gateway. */
  provider?: "razorpay";
  order?: RazorpayOrder;
}

export interface PaymentStatus {
  status: string;
  is_paid: boolean;
  amount?: string;
}

export function getPaymentConfig(): Promise<PaymentConfig> {
  return apiGet<PaymentConfig>(`${BASE}/config/`);
}

export function createCheckout(payload: {
  module: string;
  item_id: number;
  amount: string;
  description?: string;
}): Promise<CheckoutResponse> {
  return apiPost<CheckoutResponse>(`${BASE}/checkout/`, payload);
}

export function getPaymentStatus(module: string, itemId: number): Promise<PaymentStatus> {
  return apiGet<PaymentStatus>(`${BASE}/status/${module}/${itemId}/`);
}

export function verifyPayment(sessionId: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`${BASE}/verify/`, { session_id: sessionId });
}

export interface Payment {
  id: number;
  user: number;
  module: string;
  item_id: number;
  amount: string;
  currency: string;
  status: string;
  provider: string;
  description: string;
  created_at: string;
  paid_at: string | null;
}

// E-PLT-4: Razorpay Checkout widget. Loads the hosted script on demand, opens
// the widget for the order, and verifies the signed result server-side.
interface RazorpayWindow extends Window {
  Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
}

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    const w = window as RazorpayWindow;
    if (w.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

/**
 * Open the Razorpay Checkout widget for an order created by the backend, then
 * verify the signed result. Resolves true once the payment is verified paid.
 */
export async function openRazorpayCheckout(
  order: RazorpayOrder,
  opts?: { prefillEmail?: string },
): Promise<boolean> {
  const loaded = await loadRazorpayScript();
  const w = window as RazorpayWindow;
  if (!loaded || !w.Razorpay) {
    throw new Error("Could not load the Razorpay checkout. Please try again.");
  }
  return new Promise<boolean>((resolve, reject) => {
    const rzp = new w.Razorpay!({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      name: order.name,
      order_id: order.order_id,
      prefill: opts?.prefillEmail ? { email: opts.prefillEmail } : undefined,
      handler: async (res: {
        razorpay_payment_id: string;
        razorpay_order_id: string;
        razorpay_signature: string;
      }) => {
        try {
          const verified = await verifyRazorpayPayment(res);
          resolve(verified.status === "paid");
        } catch (e) {
          reject(e);
        }
      },
      modal: { ondismiss: () => resolve(false) },
    });
    rzp.open();
  });
}

/** E-PLT-4: verify a Razorpay result server-side (HMAC signature check). */
export function verifyRazorpayPayment(res: {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`${BASE}/verify/`, res);
}

/** E-PLT-2: admin lists payments awaiting manual authorisation. */
export function listPendingPayments(): Promise<Payment[]> {
  return apiGet<Payment[]>(`${BASE}/pending/`);
}

/** E-PLT-2: admin manually authorises (marks paid) a pending payment. */
export function authorisePayment(id: number, reference?: string): Promise<Payment> {
  return apiPost<Payment>(`${BASE}/${id}/authorise/`, { reference: reference ?? "" });
}
