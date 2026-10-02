import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client";
import { completionStatusLabel, deleteAssignment, startCourse, updateAssignment } from "./training";

// Same stubbing approach as client.test.ts — no real HTTP is performed.
const mockAdapter = vi.fn();

beforeEach(() => {
  apiClient.defaults.adapter = mockAdapter as unknown as typeof apiClient.defaults.adapter;
  mockAdapter.mockReset();
  mockAdapter.mockImplementation(async (config) => ({
    data: { message: "OK", data: { id: 7 } },
    status: 200,
    statusText: "OK",
    headers: {},
    config,
  }));
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("training API client", () => {
  it("edits and deletes an assignment at /training/assignments/<id>/ (Report 8.1 #61)", async () => {
    await updateAssignment(7, { title: "New" });
    await deleteAssignment(7);
    const [patch, del] = mockAdapter.mock.calls.map((c) => c[0]);
    expect(patch.method).toBe("patch");
    expect(patch.url).toBe("/training/assignments/7/");
    expect(del.method).toBe("delete");
    expect(del.url).toBe("/training/assignments/7/");
  });

  it("starts a course at /training/registrations/<id>/start/ (Report 8.1 #62)", async () => {
    await startCourse(3);
    const call = mockAdapter.mock.calls[0]?.[0];
    expect(call.method).toBe("post");
    expect(call.url).toBe("/training/registrations/3/start/");
  });

  it("labels progress statuses the same way everywhere", () => {
    expect(completionStatusLabel("not_started")).toBe("Not started");
    expect(completionStatusLabel("in_progress")).toBe("In progress");
  });
});
