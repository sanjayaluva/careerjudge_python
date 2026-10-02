import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client";
import { listCategories, setCounsellorCategories } from "./counseling";
import { uploadEditorImage } from "./uploads";

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

describe("editor image upload (Signed Doc 3 §2.1.2)", () => {
  it("posts the file as multipart and returns the URL to insert", async () => {
    respond({ message: "Image uploaded.", data: { url: "/api/uploads/editor-images/a.png" } });
    const file = new File(["x"], "chart.png", { type: "image/png" });
    const { url } = await uploadEditorImage(file);
    expect(url).toBe("/api/uploads/editor-images/a.png");
    const config = mockAdapter.mock.calls[0]?.[0];
    expect(config.url).toBe("/uploads/editor-images/");
    expect(config.data).toBeInstanceOf(FormData);
    expect((config.data as FormData).get("image")).toBeInstanceOf(File);
  });
});

describe("counselling categories (Report 9 #105)", () => {
  it("listCategories reads the plain list in the envelope", async () => {
    respond({ message: "OK", data: [{ id: 3, name: "career", label: "Career counselling" }] });
    const rows = await listCategories({ activeOnly: true });
    expect(rows.map((c) => c.label)).toEqual(["Career counselling"]);
    expect(mockAdapter.mock.calls[0]?.[0].params).toEqual({ active: "true" });
  });

  it("setCounsellorCategories sends category ids", async () => {
    respond({ message: "Categories updated.", data: { id: 9 } });
    await setCounsellorCategories(9, [3, 4]);
    const config = mockAdapter.mock.calls[0]?.[0];
    expect(config.url).toBe("/counseling/counsellors/9/set-categories/");
    expect(JSON.parse(config.data as string)).toEqual({ categories: [3, 4] });
  });
});
