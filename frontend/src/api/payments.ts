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
