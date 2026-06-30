import { describe, expect, it, beforeEach } from "vitest";

import { useAuthStore } from "./auth";
import type { LoginResponse } from "@/api/types";

const mockLoginResponse: LoginResponse = {
  access: "access-token-123",
  refresh: "refresh-token-456",
  user: {
    id: 1,
    email: "test@example.com",
    full_name: "Test User",
    role: "individual",
    is_email_verified: true,
  },
};

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.getState().clear();
    useAuthStore.getState().hydrate();
  });

  it("login() stores tokens + user and sets isAuthenticated=true", () => {
    const { login } = useAuthStore.getState();
    login(mockLoginResponse);

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-token-123");
    expect(state.refreshToken).toBe("refresh-token-456");
    expect(state.user).toEqual(mockLoginResponse.user);
    expect(state.isAuthenticated).toBe(true);

    // Persisted to localStorage under the expected key.
    const raw = localStorage.getItem("cj_auth_v1");
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw!);
    expect(parsed.accessToken).toBe("access-token-123");
    expect(parsed.refreshToken).toBe("refresh-token-456");
    expect(parsed.user.email).toBe("test@example.com");
  });

  it("logout() / clear() removes tokens, user, and resets isAuthenticated", () => {
    useAuthStore.getState().login(mockLoginResponse);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    useAuthStore.getState().clear();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("");
    expect(state.refreshToken).toBe("");
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);

    expect(localStorage.getItem("cj_auth_v1")).toBeNull();
  });

  it("setTokens() updates tokens without losing the user", () => {
    useAuthStore.getState().login(mockLoginResponse);
    useAuthStore.getState().setTokens("new-access", "new-refresh");

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("new-access");
    expect(state.refreshToken).toBe("new-refresh");
    expect(state.user?.email).toBe("test@example.com");
  });

  it("setUser() replaces just the user object", () => {
    useAuthStore.getState().login(mockLoginResponse);
    useAuthStore.getState().setUser({ ...mockLoginResponse.user, full_name: "Renamed" });

    expect(useAuthStore.getState().user?.full_name).toBe("Renamed");
  });

  it("hydrate() re-reads from localStorage", () => {
    useAuthStore.getState().login(mockLoginResponse);
    // Simulate a page reload: create a fresh store by calling hydrate.
    useAuthStore.setState({
      user: null,
      accessToken: "",
      refreshToken: "",
      isAuthenticated: false,
    });
    useAuthStore.getState().hydrate();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-token-123");
    expect(state.user?.email).toBe("test@example.com");
    expect(state.isAuthenticated).toBe(true);
  });
});
