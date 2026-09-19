/**
 * Public Layout — wraps public-facing pages with CMS-driven header + footer.
 *
 * Header: logo + CMS menu items (location='header')
 * Footer: CMS footer menu items + copyright
 *
 * Used by: PublicHomepage + CMSPageViewer (when accessed publicly)
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  listBanners,
  listMenuItems,
  listPages,
  PAGE_TYPES,
  type Banner,
  type MenuItem,
} from "@/api/cms";
import { useAuth } from "@/hooks/useAuth";

const POLICY_TYPES = new Set(["terms", "refund", "privacy"]);
const POLICY_LABEL: Record<string, string> = Object.fromEntries(
  PAGE_TYPES.map((t) => [t.value, t.label]),
);

export function PublicLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  const { data: headerMenu } = useQuery({
    queryKey: ["cms", "menu", "header"],
    queryFn: () => listMenuItems({ location: "header" }),
  });

  const { data: footerMenu } = useQuery({
    queryKey: ["cms", "menu", "footer"],
    queryFn: () => listMenuItems({ location: "footer" }),
  });

  const { data: footerBanners } = useQuery({
    queryKey: ["cms", "banners", "footer"],
    queryFn: () => listBanners({ active: true, position: "footer" }),
  });

  // E-X6: published policy pages (Terms / Refund / Privacy) linked in the footer.
  const { data: pages } = useQuery({
    queryKey: ["cms", "pages", "published"],
    queryFn: () => listPages({ status: "published" }),
  });
  const policyPages = (pages?.results ?? []).filter((p) => POLICY_TYPES.has(p.page_type));

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-lg font-bold text-primary-600">CareerJudge</span>
          </Link>

          {/* CMS-driven header navigation */}
          <nav className="flex items-center gap-4">
            {(headerMenu ?? []).map((item: MenuItem) => (
              <a
                key={item.id}
                href={item.url}
                target={item.opens_new_tab ? "_blank" : undefined}
                rel={item.opens_new_tab ? "noopener noreferrer" : undefined}
                className="text-sm text-slate-600 hover:text-primary-600"
              >
                {item.label}
              </a>
            ))}
            {user ? (
              <Link
                to="/dashboard"
                className="text-sm font-medium text-primary-600 hover:underline"
              >
                Dashboard →
              </Link>
            ) : (
              <>
                <Link to="/login" className="text-sm text-slate-600 hover:text-primary-600">
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
                >
                  Sign up
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">{children}</main>

      {/* Footer banners (from CMS) */}
      {(footerBanners?.results ?? []).length > 0 && (
        <div className="bg-slate-50 py-6">
          <div className="mx-auto max-w-6xl px-4">
            {(footerBanners?.results ?? []).map((banner: Banner) => (
              <div
                key={banner.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4"
              >
                <div>
                  <div className="font-semibold text-slate-900">{banner.title}</div>
                  {banner.subtitle && <p className="text-sm text-slate-500">{banner.subtitle}</p>}
                </div>
                {banner.link_url && (
                  <a
                    href={banner.link_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    {banner.link_text || "Learn more"}
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="text-sm text-slate-500">
              © {new Date().getFullYear()} CareerJudge. All rights reserved.
            </div>
            {/* CMS-driven footer navigation + policy pages (E-X6) */}
            <nav className="flex flex-wrap items-center gap-4">
              {(footerMenu ?? []).map((item: MenuItem) => (
                <a
                  key={item.id}
                  href={item.url}
                  target={item.opens_new_tab ? "_blank" : undefined}
                  rel={item.opens_new_tab ? "noopener noreferrer" : undefined}
                  className="text-sm text-slate-500 hover:text-primary-600"
                >
                  {item.label}
                </a>
              ))}
              {policyPages.map((p) => (
                <Link
                  key={p.id}
                  to={`/${p.slug}`}
                  className="text-sm text-slate-500 hover:text-primary-600"
                >
                  {POLICY_LABEL[p.page_type] ?? p.title}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </footer>
    </div>
  );
}
