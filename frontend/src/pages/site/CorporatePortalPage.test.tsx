import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CorporatePortalPage from "./CorporatePortalPage";
import { textOn } from "./PortalLogo";
import LoginPage from "@/pages/auth/LoginPage";
import * as orgApi from "@/api/organizations";
import type * as OrgApiModule from "@/api/organizations";
import type { PublicSite } from "@/api/organizations";
import * as meApi from "@/api/me";
import type * as MeApiModule from "@/api/me";
import { useAuthStore } from "@/stores/auth";

// Report 9 #48/#95: the public branded portal. Stub the API so no network
// call happens.
vi.mock("@/api/organizations", async () => {
  const actual = await vi.importActual<typeof OrgApiModule>("@/api/organizations");
  return { ...actual, getPublicSite: vi.fn() };
});
vi.mock("@/api/me", async () => {
  const actual = await vi.importActual<typeof MeApiModule>("@/api/me");
  return { ...actual, getMe: vi.fn() };
});

const SITE: PublicSite = {
  organization_id: 7,
  slug: "acme",
  company_name: "Acme Industries",
  logo_url: "/api/organizations/site/acme/logo/?v=1",
  layout: "classic",
  primary_color: "#0055aa",
};

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/site/:slug" element={<CorporatePortalPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.getState().clear();
});

describe("<CorporatePortalPage />", () => {
  it.each(["classic", "modern", "minimal"] as const)(
    "renders the %s layout with company name, logo and a branded sign-in link",
    async (layout) => {
      vi.mocked(orgApi.getPublicSite).mockResolvedValue({ ...SITE, layout });
      const { container } = renderAt("/site/acme");

      expect(await screen.findByRole("heading", { name: /acme industries/i })).toBeInTheDocument();
      expect(container.querySelector(`[data-layout="${layout}"]`)).not.toBeNull();
      const logo = screen.getByAltText(/acme industries logo/i);
      expect(logo.getAttribute("src")).toContain("/api/organizations/site/acme/logo/");
      const signIn = screen.getAllByRole("link", { name: /^sign in$/i })[0];
      expect(signIn).toHaveAttribute("href", "/login?site=acme");
      expect(orgApi.getPublicSite).toHaveBeenCalledWith("acme");
    },
  );

  it("offers the dashboard to a signed-in visitor without calling /api/me/", async () => {
    vi.mocked(orgApi.getPublicSite).mockResolvedValue(SITE);
    useAuthStore.getState().login({
      access: "a",
      refresh: "r",
      user: {
        id: 1,
        email: "u@example.com",
        full_name: "U",
        role: "individual",
        is_email_verified: true,
        is_superuser: false,
        is_staff: false,
      },
    });
    renderAt("/site/acme");
    const links = await screen.findAllByRole("link", { name: /go to dashboard/i });
    expect(links[0]).toHaveAttribute("href", "/dashboard");
    expect(meApi.getMe).not.toHaveBeenCalled();
  });

  it("shows a not-available message for an unknown or inactive portal", async () => {
    vi.mocked(orgApi.getPublicSite).mockRejectedValue(new Error("404"));
    renderAt("/site/nope");
    expect(await screen.findByText(/this portal is not available/i)).toBeInTheDocument();
  });

  it("carries the portal branding onto the login card", async () => {
    vi.mocked(orgApi.getPublicSite).mockResolvedValue(SITE);
    renderAt("/login?site=acme");
    expect(
      await screen.findByRole("heading", { name: /sign in to acme industries/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("portal-brand")).toHaveTextContent("Acme Industries");
    expect(
      screen.getByRole("link", { name: /back to the acme industries portal/i }),
    ).toHaveAttribute("href", "/site/acme");
  });
});

describe("textOn", () => {
  it("picks a readable text colour for the portal colour", () => {
    expect(textOn("#0b6e4f")).toBe("#ffffff"); // dark green
    expect(textOn("#4f46e5")).toBe("#ffffff"); // indigo
    expect(textOn("#f5c518")).toBe("#0f172a"); // yellow
    expect(textOn("#fff")).toBe("#0f172a");
  });
});
