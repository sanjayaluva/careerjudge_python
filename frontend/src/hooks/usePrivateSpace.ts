/**
 * usePrivateSpace — Report 9 #39-#47: the Corporate Exclusive Admin works in
 * his organization's private content space (question bank, assessments,
 * reports, courses), never in CareerJudge's. The backend scopes every list;
 * this hook tells the screens who he is, which organizations he authors for,
 * and whether an item is his to change (licensed CJ items are not).
 */
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { listOrganizations } from "@/api/organizations";
import { getPrivateOrgId, setPrivateOrgId } from "@/lib/privateSpace";
import { useAuthStore } from "@/stores/auth";

export interface PrivateSpace {
  isPrivateAuthor: boolean;
  orgs: { id: number; name: string }[];
  selectedOrgId: number | null;
  selectOrg: (id: number) => void;
  /** May he change this item? Only his organization's own (owned) items. */
  ownsItem: (item: { owner_organization?: number | null } | null | undefined) => boolean;
}

export function usePrivateSpace(): PrivateSpace {
  const role = useAuthStore((s) => s.user?.role ?? null);
  const isPrivateAuthor = role === "corp_exclusive";
  const [selected, setSelected] = useState<number | null>(getPrivateOrgId);
  const { data } = useQuery({
    queryKey: ["organizations", "private-space"],
    queryFn: () => listOrganizations({ page: 1 }),
    enabled: isPrivateAuthor,
    staleTime: 5 * 60 * 1000,
  });
  const orgs = (data?.results ?? [])
    .filter((o) => o.type === "corp_exclusive")
    .map((o) => ({ id: o.id, name: o.name }));
  const selectedOrgId = orgs.some((o) => o.id === selected) ? selected : (orgs[0]?.id ?? null);
  // A remembered choice that is no longer one of his organizations would be
  // refused by the server on every create — fall back to the first one.
  const loaded = data !== undefined;
  useEffect(() => {
    if (!isPrivateAuthor || !loaded) return;
    const stored = getPrivateOrgId();
    if (stored !== null && stored !== selectedOrgId) {
      setPrivateOrgId(selectedOrgId);
      setSelected(selectedOrgId);
    }
  }, [isPrivateAuthor, loaded, selectedOrgId]);
  return {
    isPrivateAuthor,
    orgs,
    selectedOrgId,
    selectOrg: (id: number) => {
      setPrivateOrgId(id);
      setSelected(id);
    },
    ownsItem: (item) => isPrivateAuthor && Boolean(item?.owner_organization),
  };
}
