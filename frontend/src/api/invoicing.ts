/**
 * Invoicing API client (H14).
 *
 * Per Doc 4: SME/Reviewer/Trainer/Counsellor/Channel Partner/Psychometrician
 * (+ CJ Admin) create invoices and submit them to CJ Admin, who
 * approves/rejects/marks-paid. See backend/apps/invoicing/views.py.
 */
import { apiClient, apiPost } from "./client";

const BASE = "/invoicing";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type InvoiceStatus = "draft" | "submitted" | "approved" | "rejected" | "paid" | "cancelled";

export type InvoiceType =
  | "question_creation"
  | "question_review"
  | "psychometric_review"
  | "training"
  | "counseling"
  | "channel_partner"
  | "other";

export interface InvoiceItem {
  id: number;
  invoice: number;
  description: string;
  quantity: number;
  unit_price: string;
  total: string;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  creator: number;
  creator_name: string;
  creator_role: string;
  invoice_type: InvoiceType;
  description: string;
  amount: string;
  currency: string;
  status: InvoiceStatus;
  reviewed_by: number | null;
  reviewed_by_name: string;
  review_comment: string;
  reviewed_at: string | null;
  paid_at: string | null;
  payment_reference: string;
  task: number | null;
  items: InvoiceItem[];
  created_at: string;
  updated_at: string;
}

export interface PagedResult<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---------------------------------------------------------------------------
// List endpoints — InvoiceViewSet.list/my_invoices/pending don't wrap the
// response in the {message, data} envelope (DRF's default paginated
// response is returned as-is), so fetch them directly rather than via the
// apiGet/apiGetPaged helpers (which expect that envelope).
// ---------------------------------------------------------------------------

async function getPaged<T>(url: string): Promise<PagedResult<T>> {
  const res = await apiClient.get<PagedResult<T>>(url);
  return res.data;
}

export function listInvoices(): Promise<PagedResult<Invoice>> {
  return getPaged<Invoice>(`${BASE}/invoices/`);
}

export function listMyInvoices(): Promise<PagedResult<Invoice>> {
  return getPaged<Invoice>(`${BASE}/invoices/my_invoices/`);
}

export function listPendingInvoices(): Promise<PagedResult<Invoice>> {
  return getPaged<Invoice>(`${BASE}/invoices/pending/`);
}

// ---------------------------------------------------------------------------
// Create + lifecycle actions
// ---------------------------------------------------------------------------

export function createInvoice(payload: {
  invoice_type?: InvoiceType;
  description: string;
  amount: string;
  currency?: string;
  task?: number;
}): Promise<Invoice> {
  return apiPost<Invoice>(`${BASE}/invoices/`, payload);
}

export function submitInvoice(id: number): Promise<Invoice> {
  return apiPost<Invoice>(`${BASE}/invoices/${id}/submit/`);
}

export function cancelInvoice(id: number): Promise<Invoice> {
  return apiPost<Invoice>(`${BASE}/invoices/${id}/cancel/`);
}

export function approveInvoice(id: number, comment?: string): Promise<Invoice> {
  return apiPost<Invoice>(`${BASE}/invoices/${id}/approve/`, { comment: comment ?? "" });
}

export function rejectInvoice(id: number, comment?: string): Promise<Invoice> {
  return apiPost<Invoice>(`${BASE}/invoices/${id}/reject/`, { comment: comment ?? "" });
}

export function payInvoice(id: number, paymentReference?: string): Promise<Invoice> {
  return apiPost<Invoice>(`${BASE}/invoices/${id}/pay/`, {
    payment_reference: paymentReference ?? "",
  });
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const INVOICE_TYPES: { value: InvoiceType; label: string }[] = [
  { value: "question_creation", label: "Question Creation" },
  { value: "question_review", label: "Question Review" },
  { value: "psychometric_review", label: "Psychometric Review" },
  { value: "training", label: "Training Services" },
  { value: "counseling", label: "Counseling Services" },
  { value: "channel_partner", label: "Channel Partner Commission" },
  { value: "other", label: "Other" },
];

/** Roles that may create invoices (Doc 4), mirrors backend EMPANELLED_ROLES
 * in apps/invoicing/views.py — used only for UI convenience (show/hide the
 * create form); the backend is the actual enforcement point. */
export const INVOICING_EMPANELLED_ROLES = [
  "sme",
  "reviewer",
  "trainer",
  "counsellor",
  "channel_partner",
  "psychometrician",
];
