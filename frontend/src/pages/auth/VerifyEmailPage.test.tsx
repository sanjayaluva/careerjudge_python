import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VerifyEmailPage from "./VerifyEmailPage";
import * as authApi from "@/api/auth";
import type * as AuthApiModule from "@/api/auth";

// Accounts audit gap: this page now collects a password (instead of
// auto-verifying on mount) so a self-registered account — which no longer
// captures a password at signup — can set one once email ownership is
// proven. Stub the API module so no real network call happens.
vi.mock("@/api/auth", async () => {
  const actual = await vi.importActual<typeof AuthApiModule>("@/api/auth");
  return {
    ...actual,
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
  };
});

function renderPage(token = "abc-123") {
  return render(
    <MemoryRouter initialEntries={[`/verify-email/${token}`]}>
      <Routes>
        <Route path="/verify-email/:token" element={<VerifyEmailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("<VerifyEmailPage />", () => {
  it("shows a password form up front instead of auto-verifying", () => {
    renderPage();
    expect((document.getElementById("password") as HTMLInputElement)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /set password/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /skip/i })).toBeInTheDocument();
    expect(authApi.verifyEmail).not.toHaveBeenCalled();
  });

  it("verifies with the chosen password when the form is submitted", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.verifyEmail).mockResolvedValue(undefined);
    renderPage("tok-1");

    await user.type((document.getElementById("password") as HTMLInputElement), "StrongP@ss1");
    await user.type(screen.getByLabelText(/confirm password/i), "StrongP@ss1");
    await user.click(screen.getByRole("button", { name: /set password/i }));

    await waitFor(() => {
      expect(authApi.verifyEmail).toHaveBeenCalledWith("tok-1", "StrongP@ss1");
    });
    expect(await screen.findByText(/verified/i)).toBeInTheDocument();
  });

  it("verifies without a password when Skip is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.verifyEmail).mockResolvedValue(undefined);
    renderPage("tok-2");

    await user.click(screen.getByRole("button", { name: /skip/i }));

    await waitFor(() => {
      expect(authApi.verifyEmail).toHaveBeenCalledWith("tok-2", undefined);
    });
    expect(await screen.findByText(/verified/i)).toBeInTheDocument();
  });

  it("shows a validation error for a weak password and does not call the API", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type((document.getElementById("password") as HTMLInputElement), "short");
    await user.type(screen.getByLabelText(/confirm password/i), "short");
    await user.click(screen.getByRole("button", { name: /set password/i }));

    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
    expect(authApi.verifyEmail).not.toHaveBeenCalled();
  });

  it("shows a validation error when the passwords do not match", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type((document.getElementById("password") as HTMLInputElement), "StrongP@ss1");
    await user.type(screen.getByLabelText(/confirm password/i), "Different1");
    await user.click(screen.getByRole("button", { name: /set password/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(authApi.verifyEmail).not.toHaveBeenCalled();
  });

  it("shows an error state with a resend form when verification fails", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.verifyEmail).mockRejectedValue(new Error("Invalid or expired token."));
    renderPage();

    await user.click(screen.getByRole("button", { name: /skip/i }));

    expect(await screen.findByText(/invalid or expired token/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /resend verification/i })).toBeInTheDocument();
  });
});
