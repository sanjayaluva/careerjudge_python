import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { RoleBasedNav } from "./RoleBasedNav";
import { useAuthStore } from "@/stores/auth";
import type { AuthUser, ModuleRightGrant } from "@/api/types";

function renderNav() {
  return render(
    <MemoryRouter>
      <RoleBasedNav />
    </MemoryRouter>,
  );
}

function setUser(role: AuthUser["role"], moduleRights?: ModuleRightGrant[]): void {
  const user: AuthUser = {
    id: 1,
    email: "u@example.com",
    full_name: "U",
    role,
    is_email_verified: true,
    is_superuser: false,
    is_staff: false,
    module_rights: moduleRights,
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

    // cj_admin sees every nav item (17 total: dashboard, profile, users,
    // roles, organizations, question_bank, assessments, career_profiling,
    // reports, training, counseling, cms, tasks, invoicing, payments, plus
    // the two universal capabilities Contact Admin + Messages).
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(17);
    expect(screen.getByText("Payments")).toBeInTheDocument();
    expect(screen.getByText("Contact Admin")).toBeInTheDocument();
    expect(screen.getByText("Messages")).toBeInTheDocument();
    expect(screen.getByText("CMS")).toBeInTheDocument();
    expect(screen.getByText("Roles & Permissions")).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.getByText("Invoicing")).toBeInTheDocument();
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
        // Signed Individual-User capabilities (User Details.pdf p.1).
        "Contact Admin",
        "Messages",
        "Live Chat",
      ]),
    );
    // individual must NOT see admin-only modules.
    expect(labels).not.toContain("Users");
    expect(labels).not.toContain("Roles & Permissions");
    expect(labels).not.toContain("CMS");
    expect(labels).not.toContain("Organizations");
    expect(labels).not.toContain("Question Bank");

    // 7 role modules + Contact Admin + Messages + Live Chat = 10.
    expect(within(list).getAllByRole("link")).toHaveLength(10);
  });

  it("shows the corp_admin subset (no Roles & Permissions / CMS / Question Bank)", () => {
    setUser("corp_admin");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    // Report 9 #5/#9: no CJ user list for Corp Admin — members are managed
    // from the organization page.
    expect(labels).not.toContain("Users");
    expect(labels).toContain("Organizations");
    expect(labels).not.toContain("Roles & Permissions");
    expect(labels).not.toContain("CMS");
    expect(labels).not.toContain("Question Bank");
  });

  it("shows the sme subset (no Assessments — Report 4 SME-3)", () => {
    setUser("sme");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    expect(labels).toEqual(
      expect.arrayContaining(["Dashboard", "Profile", "Question Bank", "Tasks", "Invoicing"]),
    );
    expect(labels).not.toContain("Assessments");
    // 5 role modules + Contact Admin + Messages = 7.
    expect(within(list).getAllByRole("link")).toHaveLength(7);
  });

  it("shows the reviewer subset (tab reads 'My Review Questions', no Assessments)", () => {
    setUser("reviewer");
    renderNav();

    const list = screen.getByRole("navigation");
    const labels = within(list)
      .getAllByRole("link")
      .map((a) => a.textContent?.trim() ?? "");

    expect(labels).toEqual(
      expect.arrayContaining(["Dashboard", "Profile", "My Review Questions", "Tasks", "Invoicing"]),
    );
    expect(labels).not.toContain("Assessments");
    expect(labels).not.toContain("Question Bank");
    expect(within(list).getAllByRole("link")).toHaveLength(7);
  });

  describe("module_rights-driven rendering (RBAC single source of truth)", () => {
    it("renders nav items for a custom role purely from module_rights", () => {
      // A custom role name (not one of the 12 seeded roles) is invisible to
      // the static MODULE_VISIBILITY map — the nav must fall back entirely
      // to the effective module_rights /api/me returns.
      setUser("senior_reviewer" as AuthUser["role"], [
        { module: "question_bank", action: "view" },
        { module: "question_bank", action: "review" },
        { module: "assessment", action: "view" },
      ]);
      renderNav();

      const list = screen.getByRole("navigation");
      const labels = within(list)
        .getAllByRole("link")
        .map((a) => a.textContent?.trim() ?? "");

      // Dashboard + Profile are always visible; Question Bank + Assessments
      // come from the granted modules; nothing else.
      expect(labels).toEqual(
        expect.arrayContaining(["Dashboard", "Profile", "Question Bank", "Assessments"]),
      );
      expect(labels).not.toContain("Users");
      expect(labels).not.toContain("Roles & Permissions");
      // Dashboard + Profile + Question Bank + Assessments + the two universal
      // capabilities (Contact Admin, Messages) = 6.
      expect(within(list).getAllByRole("link")).toHaveLength(6);
    });

    it("ignores a stray ModuleRight grant for a seeded role (signed role map wins)", () => {
      // Report 9: leftover rights (e.g. Assessments for a counsellor) used to
      // bring removed tabs back. Built-in roles now follow the role map only.
      setUser("counsellor", [
        { module: "assessment", action: "view" },
        { module: "accounts", action: "view" },
      ]);
      renderNav();

      const list = screen.getByRole("navigation");
      const labels = within(list)
        .getAllByRole("link")
        .map((a) => a.textContent?.trim() ?? "");

      expect(labels).not.toContain("Assessments");
      expect(labels).not.toContain("Users");
      expect(labels).toContain("Counseling");
    });

    it("still shows nothing extra for individual when module_rights matches the static set", () => {
      setUser("individual", [
        { module: "assessment", action: "view" },
        { module: "reporting", action: "view" },
        { module: "training", action: "view" },
        { module: "training", action: "add" },
        { module: "training", action: "change" },
        { module: "counseling", action: "view" },
        { module: "counseling", action: "add" },
        { module: "counseling", action: "change" },
      ]);
      renderNav();

      const list = screen.getByRole("navigation");
      const labels = within(list)
        .getAllByRole("link")
        .map((a) => a.textContent?.trim() ?? "");

      expect(labels).not.toContain("Users");
      expect(labels).not.toContain("Roles & Permissions");
      expect(labels).not.toContain("CMS");
      // career_profiling isn't in individual's seed_demo grants but stays
      // visible via the static fallback (union, not replacement).
      expect(labels).toContain("Career Profiling");
      // 7 role modules + Contact Admin + Messages + Live Chat = 10.
      expect(within(list).getAllByRole("link")).toHaveLength(10);
    });
  });
});
