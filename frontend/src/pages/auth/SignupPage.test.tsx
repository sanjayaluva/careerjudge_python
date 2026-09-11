import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, beforeEach } from "vitest";

import SignupPage from "./SignupPage";
import { useAuthStore } from "@/stores/auth";

function renderSignupPage() {
  return render(
    <MemoryRouter>
      <SignupPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  useAuthStore.getState().clear();
  useAuthStore.getState().hydrate();
});

describe("<SignupPage />", () => {
  it("renders the required fields and a submit button, with no password field", () => {
    renderSignupPage();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    // Password is now set at email-verification time, not at signup —
    // see the accounts audit gap fix (SignupSerializer / VerifyEmailPage).
    expect(document.getElementById("password")).not.toBeInTheDocument();
    expect(document.getElementById("confirmPassword")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows a validation error when required fields are empty", async () => {
    const user = userEvent.setup();
    renderSignupPage();

    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });
});
