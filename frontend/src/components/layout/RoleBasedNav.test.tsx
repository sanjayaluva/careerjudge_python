import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { RoleBasedNav } from "./RoleBasedNav";
import { useAuthStore } from "@/stores/auth";
import type { AuthUser } from "@/api/types";

function renderNav() {
  return render(
    <MemoryRouter>
      <RoleBasedNav />
    </MemoryRouter>,
  );
}

function setUser(role: AuthUser["role"]): void {
  const user: AuthUser = {
    id: 1,
    email: "u@example.com",
    full_name: "U",
    role,
    is_email_verified: true,
    is_superuser: false,
    is_staff: false,
  };
  useAuthStore.getState().login({
    access: "a",
    refresh: "r",
    user,
  });
}

beforeEach(() => {
  localStorage.clear();
  useAuthStore.getState().clear();
  useAuthStore.getState().hydrate();
});

describe("<RoleBasedNav />", () => {
  it("renders no items when the user has no role", () => {
    renderNav();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("shows ALL modules for cj_admin", () => {
    setUser("cj_admin");
    renderNav();

    // cj_admin sees every nav item (13 total: dashboard, profile, users,
    // roles, organizations, question_bank, assessments, career_profiling,
    // reports, training, counseling, cms, tasks).
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(13);
    expect(screen.getByText("CMS")).toBeInTheDocument();
    expect(screen.getByText("Roles & Permissions")).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
  });

  it("shows only the allowed subset for individual", () => {
    setUser("individual");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    expect(labels).toEqual(
      expect.arrayContaining([
        "Dashboard",
        "Profile",
        "Assessments",
        "Career Profiling",
        "Reports",
        "Training",
        "Counseling",
      ]),
    );
    // individual must NOT see admin-only modules.
    expect(labels).not.toContain("Users");
    expect(labels).not.toContain("Roles & Permissions");
    expect(labels).not.toContain("CMS");
    expect(labels).not.toContain("Organizations");
    expect(labels).not.toContain("Question Bank");

    // Exact count check: 7 modules for individual.
    expect(within(list).getAllByRole("link")).toHaveLength(7);
  });

  it("shows the corp_admin subset (no Roles & Permissions / CMS / Question Bank)", () => {
    setUser("corp_admin");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    expect(labels).toContain("Users");
    expect(labels).toContain("Organizations");
    expect(labels).not.toContain("Roles & Permissions");
    expect(labels).not.toContain("CMS");
    expect(labels).not.toContain("Question Bank");
  });

  it("shows the sme subset (Dashboard, Profile, Question Bank, Assessments, Tasks)", () => {
    setUser("sme");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    expect(labels).toEqual(
      expect.arrayContaining(["Dashboard", "Profile", "Question Bank", "Assessments", "Tasks"]),
    );
    expect(within(list).getAllByRole("link")).toHaveLength(5);
  });

  it("shows the reviewer subset (Dashboard, Profile, Question Bank, Assessments, Tasks)", () => {
    setUser("reviewer");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    expect(labels).toEqual(
      expect.arrayContaining(["Dashboard", "Profile", "Question Bank", "Assessments", "Tasks"]),
    );
    expect(within(list).getAllByRole("link")).toHaveLength(5);
  });
});
