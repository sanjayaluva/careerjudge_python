import { useQuery } from "@tanstack/react-query";

import { getMySite } from "@/api/organizations";
import { PortalLogo } from "@/pages/site/PortalLogo";

/**
 * Report 9 #51/#52: members of an organization with an active corporate
 * portal keep its branding (logo + company name) in the app's top bar after
 * signing in. Renders nothing for everyone else.
 */
export function PortalTopbarBrand() {
  const { data: site } = useQuery({
    queryKey: ["my-site"],
    queryFn: getMySite,
    staleTime: 5 * 60_000,
    retry: false,
  });
  if (!site) return null;
  return (
    <div
      className="flex shrink-0 items-center gap-2 border-r border-slate-200 pr-3"
      data-testid="portal-topbar-brand"
    >
      <PortalLogo
        src={site.logo_url}
        name={site.company_name}
        color={site.primary_color}
        size={32}
      />
      <span className="hidden max-w-[12rem] truncate text-sm font-semibold text-slate-800 md:inline">
        {site.company_name}
      </span>
    </div>
  );
}
