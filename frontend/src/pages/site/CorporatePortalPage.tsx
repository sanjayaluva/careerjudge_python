/**
 * Corporate branded portal — `/site/:slug`, no login needed (Report 9
 * #48/#51/#52/#95; CJ_UC054 "System displays the customized page", CJ_UC055).
 *
 * Renders the organization's company name, logo and primary colour in the
 * layout chosen on Organizations › [org] › Corporate website (classic, modern
 * or minimal). "Sign in" opens the normal login carrying the portal branding
 * (`/login?site=<slug>`); after sign-in employees land in the normal app,
 * which already shows only the work assigned to their organization.
 */
import { useQuery } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { getPublicSite, type PublicSite } from "@/api/organizations";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { APP_NAME } from "@/lib/constants";

import { PortalLogo, textOn } from "./PortalLogo";

export default function CorporatePortalPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const { data: site, isLoading } = useQuery({
    queryKey: ["public-site", slug],
    queryFn: () => getPublicSite(slug),
    enabled: Boolean(slug),
    retry: false,
  });

  useEffect(() => {
    if (!site) return;
    const previous = document.title;
    document.title = site.company_name;
    return () => {
      document.title = previous;
    };
  }, [site]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!site) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 px-4 text-center">
        <h1 className="text-xl font-semibold text-slate-900">This portal is not available</h1>
        <p className="text-sm text-slate-500">
          The address may be mistyped, or the organization&apos;s portal is not active.
        </p>
        <Link to="/" className="text-sm font-medium text-primary-600 hover:underline">
          Go to {APP_NAME}
        </Link>
      </div>
    );
  }

  if (site.layout === "modern") return <ModernLayout site={site} />;
  if (site.layout === "minimal") return <MinimalLayout site={site} />;
  return <ClassicLayout site={site} />;
}

const WELCOME =
  "Sign in to take the assessments and training courses your organization has assigned to you.";

/** "Sign in" (or "Go to dashboard" when already signed in), in the portal colour. */
function SignInButton({ site, inverted = false }: { site: PublicSite; inverted?: boolean }) {
  const { user } = useAuth();
  const bg = inverted ? textOn(site.primary_color) : site.primary_color;
  const fg = inverted ? site.primary_color : textOn(site.primary_color);
  return (
    <Link
      to={user ? "/dashboard" : `/login?site=${encodeURIComponent(site.slug)}`}
      className="inline-flex h-11 shrink-0 items-center justify-center whitespace-nowrap rounded-md px-5 text-sm font-semibold shadow-sm transition-opacity hover:opacity-90 sm:px-6"
      style={{ backgroundColor: bg, color: fg }}
    >
      {user ? "Go to dashboard" : "Sign in"}
    </Link>
  );
}

function PoweredBy({ className = "text-slate-400" }: { className?: string }) {
  return <p className={`text-xs ${className}`}>Powered by {APP_NAME}</p>;
}

/** Classic: header bar with logo and sign-in, a coloured welcome band, footer. */
function ClassicLayout({ site }: { site: PublicSite }) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50" data-layout="classic">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <PortalLogo src={site.logo_url} name={site.company_name} color={site.primary_color} />
            <span className="truncate text-lg font-semibold text-slate-900">
              {site.company_name}
            </span>
          </div>
          <SignInButton site={site} />
        </div>
      </header>
      <section
        className="px-4 py-16 sm:py-20"
        style={{ backgroundColor: site.primary_color, color: textOn(site.primary_color) }}
      >
        <div className="mx-auto max-w-5xl">
          <h1 className="text-3xl font-bold sm:text-4xl">Welcome to {site.company_name}</h1>
          <p className="mt-3 max-w-2xl text-base opacity-90">{WELCOME}</p>
          <div className="mt-8">
            <SignInButton site={site} inverted />
          </div>
        </div>
      </section>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <div className="grid gap-4 sm:grid-cols-2">
          <InfoTile title="Assessments" color={site.primary_color}>
            Take the assessments assigned to you.
          </InfoTile>
          <InfoTile title="Training" color={site.primary_color}>
            Follow your training courses.
          </InfoTile>
        </div>
      </main>
      <footer className="border-t border-slate-200 bg-white px-4 py-4 text-center">
        <PoweredBy />
      </footer>
    </div>
  );
}

function InfoTile({
  title,
  color,
  children,
}: {
  title: string;
  color: string;
  children: ReactNode;
}) {
  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-5"
      style={{ borderTopColor: color, borderTopWidth: 4 }}
    >
      <h2 className="font-semibold text-slate-900">{title}</h2>
      <p className="mt-1 text-sm text-slate-600">{children}</p>
    </div>
  );
}

/** Modern: full-page colour wash with a centred card. */
function ModernLayout({ site }: { site: PublicSite }) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center px-4 py-12"
      data-layout="modern"
      style={{
        background: `linear-gradient(135deg, ${site.primary_color} 0%, #0f172a 130%)`,
      }}
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-xl">
        <div className="flex justify-center">
          <PortalLogo
            src={site.logo_url}
            name={site.company_name}
            color={site.primary_color}
            size={72}
          />
        </div>
        <h1 className="mt-5 text-2xl font-bold text-slate-900">{site.company_name}</h1>
        <p className="mt-2 text-sm text-slate-600">{WELCOME}</p>
        <div className="mt-6">
          <SignInButton site={site} />
        </div>
      </div>
      <PoweredBy className="mt-6 text-white/70" />
    </div>
  );
}

/** Minimal: plain white page, logo, name and a single accent line. */
function MinimalLayout({ site }: { site: PublicSite }) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center bg-white px-4 py-12 text-center"
      data-layout="minimal"
    >
      <PortalLogo
        src={site.logo_url}
        name={site.company_name}
        color={site.primary_color}
        size={56}
      />
      <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900">
        {site.company_name}
      </h1>
      <span
        aria-hidden="true"
        className="mt-3 block h-1 w-12 rounded-full"
        style={{ backgroundColor: site.primary_color }}
      />
      <p className="mt-4 max-w-sm text-sm text-slate-500">{WELCOME}</p>
      <div className="mt-6">
        <SignInButton site={site} />
      </div>
      <PoweredBy className="mt-10 text-slate-400" />
    </div>
  );
}
