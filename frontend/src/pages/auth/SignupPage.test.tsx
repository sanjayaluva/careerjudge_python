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
  it("renders all required fields and a submit button", () => {
    renderSignupPage();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(document.getElementById("password")).toBeInTheDocument();
    expect(document.getElementById("confirmPassword")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows a validation error when required fields are empty", async () => {
    const user = userEvent.setup();
    renderSignupPage();

    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });

  it("shows a validation error when passwords do not match", async () => {
    const user = userEvent.setup();
    renderSignupPage();

    await user.type(screen.getByLabelText(/full name/i), "Jane Doe");
    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(document.getElementById("password") as HTMLInputElement, "Password1");
    await user.type(
      document.getElementById("confirmPassword") as HTMLInputElement,
      "Password2",
    );
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
  });

  it("shows a validation error for a weak password", async () => {
    const user = userEvent.setup();
    renderSignupPage();

    await user.type(screen.getByLabelText(/full name/i), "Jane Doe");
    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(document.getElementById("password") as HTMLInputElement, "short");
    await user.type(
      document.getElementById("confirmPassword") as HTMLInputElement,
      "short",
    );
    await user.click(screen.getByRole("button", { name: /create account/i }));

    // The password is too short — error message must appear in the error area
    // (not the hint paragraph which has id="password-hint").
    const errorEl = await screen.findByText(
      (_, node) =>
        node?.tagName === "P" &&
        node.id === "password-error" &&
        !!node.textContent?.includes("at least 8 characters"),
    );
    expect(errorEl).toBeInTheDocument();
  });
});
