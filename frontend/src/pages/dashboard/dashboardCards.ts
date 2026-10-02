import { MODULE_LABELS, type ModuleKey, type RoleName } from "@/lib/constants";

/**
 * Report 9 #82: the individual's dashboard cards read My Assessments » My
 * Profiling Solutions » My Reports » My Training Courses » My Counselling
 * Sessions (in that order, ahead of the rest). Other roles keep the module
 * names.
 */
const INDIVIDUAL_CARD_LABELS: Partial<Record<ModuleKey, string>> = {
  assessments: "My Assessments",
  career_profiling: "My Profiling Solutions",
  reports: "My Reports",
  training: "My Training Courses",
  counseling: "My Counselling Sessions",
};
const INDIVIDUAL_CARD_ORDER = Object.keys(INDIVIDUAL_CARD_LABELS) as ModuleKey[];

export function dashboardCardLabel(role: RoleName, key: ModuleKey): string {
  return (role === "individual" && INDIVIDUAL_CARD_LABELS[key]) || MODULE_LABELS[key];
}

export function orderDashboardModules<T extends { key: ModuleKey }>(
  role: RoleName,
  items: T[],
): T[] {
  if (role !== "individual") return items;
  const rank = (k: ModuleKey) => {
    const i = INDIVIDUAL_CARD_ORDER.indexOf(k);
    return i === -1 ? INDIVIDUAL_CARD_ORDER.length : i;
  };
  return [...items].sort((a, b) => rank(a.key) - rank(b.key));
}
