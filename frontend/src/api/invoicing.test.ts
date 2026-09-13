import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client";
import { createInvoice, listMyInvoices, INVOICING_EMPANELLED_ROLES } from "./invoicing";

// Same stubbing approach as client.test.ts — no real HTTP is performed.
const mockAdapter = vi.fn();

beforeEach(() => {
  apiClient.defaults.adapter = mockAdapter as unknown as typeof apiClient.defaults.adapter;
  mockAdapter.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("invoicing API client (H14)", () => {
  it("listMyInvoices reads the raw DRF pagination shape (no {message,data} envelope)", async () => {
    // InvoiceViewSet.my_invoices() returns DRF's default paginated response
    // directly ({count, next, previous, results}) — NOT wrapped like the
    // create/submit/approve/... actions are. Confirms invoicing.ts fetches
    // it directly instead of via apiGetPaged (which expects the envelope).
    mockAdapter.mockImplementation(async (config) => ({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [{ id: 1, invoice_number: "INV-2026-0001", status: "draft" }],
      },
      status: 200,
      statusText: "OK",
      headers: {},
      config,
    }));

    const result = await listMyInvoices();
    expect(result.count).toBe(1);
    expect(result.results[0]?.invoice_number).toBe("INV-2026-0001");
    expect(mockAdapter.mock.calls[0]?.[0].url).toBe("/invoicing/invoices/my_invoices/");
  });

  it("createInvoice posts to /invoicing/invoices/ and unwraps the {message,data} envelope", async () => {
    mockAdapter.mockImplementation(async (config) => ({
      data: {
        message: "Invoice created.",
        data: { id: 2, invoice_number: "INV-2026-0002", status: "draft" },
      },
      status: 201,
      statusText: "Created",
      headers: {},
      config,
    }));

    const invoice = await createInvoice({ description: "Reviewed 10 questions", amount: "500" });
    expect(invoice.id).toBe(2);
    expect(invoice.status).toBe("draft");
    const call = mockAdapter.mock.calls[0]?.[0];
    expect(call.url).toBe("/invoicing/invoices/");
    expect(call.method).toBe("post");
  });

  it("INVOICING_EMPANELLED_ROLES matches the roles Doc 4 empanels (mirrors the backend gate)", () => {
    expect(INVOICING_EMPANELLED_ROLES.sort()).toEqual(
      ["sme", "reviewer", "trainer", "counsellor", "channel_partner", "psychometrician"].sort(),
    );
  });
});
