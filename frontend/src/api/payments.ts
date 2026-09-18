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

export interface CheckoutResponse {
  checkout_url?: string;
  status?: "free" | "paid" | "manual" | "pending";
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

/** E-PLT-2: admin lists payments awaiting manual authorisation. */
export function listPendingPayments(): Promise<Payment[]> {
  return apiGet<Payment[]>(`${BASE}/pending/`);
}

/** E-PLT-2: admin manually authorises (marks paid) a pending payment. */
export function authorisePayment(id: number, reference?: string): Promise<Payment> {
  return apiPost<Payment>(`${BASE}/${id}/authorise/`, { reference: reference ?? "" });
}
