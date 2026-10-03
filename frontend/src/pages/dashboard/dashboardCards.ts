import { MODULE_DESCRIPTIONS, MODULE_LABELS, type ModuleKey, type RoleName } from "@/lib/constants";

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

/** Candidate-facing card descriptions for the individual's dashboard (the
 * defaults describe the author screens). */
const INDIVIDUAL_CARD_DESCRIPTIONS: Partial<Record<ModuleKey, string>> = {
  assessments: "Take, resume and review your assessments.",
  career_profiling: "See your profiling solutions and their progress.",
  reports: "View and download your assessment reports.",
  training: "Begin, resume and complete your courses.",
  counseling: "Book and follow your counselling sessions.",
};

export function dashboardCardDescription(role: RoleName, key: ModuleKey): string {
  return (role === "individual" && INDIVIDUAL_CARD_DESCRIPTIONS[key]) || MODULE_DESCRIPTIONS[key];
}
