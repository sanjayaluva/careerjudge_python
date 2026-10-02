import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { listModificationRequests } from "./assessment";
import { apiClient } from "./client";
import { listDeletionRequests } from "./questionBank";

// Report 9 #107 / #108: the CJ Admin approval queues read these lists. The
// backend returns a plain list inside the {message, data} envelope (not a
// DRF page), and the old code read `.results` off it — always empty.
const mockAdapter = vi.fn();

beforeEach(() => {
  apiClient.defaults.adapter = mockAdapter as unknown as typeof apiClient.defaults.adapter;
  mockAdapter.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function respond(data: unknown) {
  mockAdapter.mockImplementation(async (config) => ({
    data,
    status: 200,
    statusText: "OK",
    headers: {},
    config,
  }));
}

describe("admin approval queues", () => {
  it("listModificationRequests reads the {message, data: [...]} list", async () => {
    respond({
      message: "OK",
      data: [{ id: 1, assessment: 7, action: "delete", status: "pending" }],
    });
    const rows = await listModificationRequests();
    expect(rows).toHaveLength(1);
    expect(rows[0]?.action).toBe("delete");
    expect(mockAdapter.mock.calls[0]?.[0].url).toBe("/assessment-modification-requests/");
  });

  it("listModificationRequests still accepts a paginated page", async () => {
    respond({ count: 1, next: null, previous: null, results: [{ id: 2, status: "pending" }] });
    const rows = await listModificationRequests();
    expect(rows.map((r) => r.id)).toEqual([2]);
  });

  it("listDeletionRequests reads the {message, data: [...]} list", async () => {
    respond({
      message: "OK",
      data: [
        { id: 3, target_type: "question", status: "pending" },
        { id: 4, target_type: "question", status: "approved" },
      ],
    });
    const rows = await listDeletionRequests();
    expect(rows.map((r) => r.id)).toEqual([3, 4]);
    expect(mockAdapter.mock.calls[0]?.[0].url).toBe("/question-bank/deletion-requests/");
  });

  it("listDeletionRequests still accepts a paginated page", async () => {
    respond({ count: 1, next: null, previous: null, results: [{ id: 5, status: "pending" }] });
    const rows = await listDeletionRequests();
    expect(rows.map((r) => r.id)).toEqual([5]);
  });
});
