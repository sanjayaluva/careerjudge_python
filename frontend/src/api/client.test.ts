import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient, extractApiError } from "./client";
import { useAuthStore } from "@/stores/auth";
import type { LoginResponse } from "@/api/types";

// We exercise the request interceptor only. Network calls are stubbed via
// axios adapters so no real HTTP is performed.
const mockAdapter = vi.fn();

beforeEach(() => {
  localStorage.clear();
  useAuthStore.getState().clear();
  useAuthStore.getState().hydrate();
  // Replace the real adapter with our stub so requests don't hit the network.
  apiClient.defaults.adapter = mockAdapter as unknown as typeof apiClient.defaults.adapter;
  mockAdapter.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function buildLoginResponse(): LoginResponse {
  return {
    access: "ACCESS",
    refresh: "REFRESH",
    user: {
      id: 1,
      email: "u@example.com",
      full_name: "U",
      role: "individual",
      is_email_verified: true,
    },
  };
}

describe("apiClient request interceptor", () => {
  it("does NOT attach an Authorization header when no token is stored", async () => {
    mockAdapter.mockImplementation(async (config) => ({
      data: { message: "OK", data: null },
      status: 200,
      statusText: "OK",
      headers: {},
      config,
    }));

    await apiClient.get("/anything/");

    const config = mockAdapter.mock.calls[0]![0];
    expect(config.headers.Authorization).toBeUndefined();
  });

  it("attaches `Authorization: Bearer <token>` when a token is stored", async () => {
    useAuthStore.getState().login(buildLoginResponse());

    mockAdapter.mockImplementation(async (config) => ({
      data: { message: "OK", data: null },
      status: 200,
      statusText: "OK",
      headers: {},
      config,
    }));

    await apiClient.get("/anything/");

    const config = mockAdapter.mock.calls[0]![0];
    expect(config.headers.Authorization).toBe("Bearer ACCESS");
  });
});

describe("extractApiError", () => {
  it("reads the envelope `error.message` when present", () => {
    const err = {
      isAxiosError: true,
      response: {
        status: 401,
        data: { error: { code: "unauthorized", message: "Token expired." } },
      },
      message: "Request failed",
    };
    expect(extractApiError(err)).toBe("Token expired.");
  });

  it("includes field-specific details from the envelope", () => {
    const err = {
      isAxiosError: true,
      response: {
        status: 400,
        data: {
          error: {
            code: "validation_error",
            message: "Validation failed.",
            details: {
              name: ["A role with this name already exists."],
            },
          },
        },
      },
      message: "Request failed",
    };
    const result = extractApiError(err);
    expect(result).toContain("Validation failed.");
    expect(result).toContain("name: A role with this name already exists.");
  });

  it("falls back to DRF `detail` field when no envelope", () => {
    const err = {
      isAxiosError: true,
      response: { status: 403, data: { detail: "You do not have permission." } },
      message: "Request failed",
    };
    expect(extractApiError(err)).toBe("You do not have permission.");
  });

  it("falls back to DRF validation error shape (field -> string[])", () => {
    const err = {
      isAxiosError: true,
      response: {
        status: 400,
        data: { email: ["This field is required."], password: ["Too short."] },
      },
      message: "Request failed",
    };
    const msg = extractApiError(err);
    expect(msg).toContain("email: This field is required.");
    expect(msg).toContain("password: Too short.");
  });

  it("falls back to err.message when no response body", () => {
    const err = { isAxiosError: true, message: "Some other error" };
    expect(extractApiError(err)).toBe("Some other error");
  });

  it("provides helpful message for Network Error", () => {
    const err = { isAxiosError: true, message: "Network Error" };
    const result = extractApiError(err);
    expect(result).toContain("Network error");
    expect(result).toContain("DNS or connection");
  });

  it("handles plain Error instances", () => {
    expect(extractApiError(new Error("boom"))).toBe("boom");
  });
});
