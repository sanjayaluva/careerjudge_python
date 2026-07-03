/**
 * Static application constants — role names, module visibility map,
 * nav item configuration. Source of truth for role-based navigation.
 *
 * SME vs Reviewer (split per client clarification 2026-06-30):
 *   - sme:      Subject Matter Expert. Creates / views / edits / deletes OWN
 *               questions (only while unreviewed). Once reviewed, can only
 *               request admin deletion.
 *   - reviewer: Reviews questions submitted by SMEs. Cannot create / edit /
 *               delete questions. Can approve / reject.
 */

export type RoleName =
  | "cj_admin"
  | "corp_admin"
  | "corp_exclusive"
  | "psychometrician"
  | "sme"
  | "reviewer"
  | "trainer"
  | "group_admin"
  | "counsellor"
  | "channel_partner"
  | "individual";

export type ModuleKey =
  | "dashboard"
  | "profile"
  | "users"
  | "roles"
  | "organizations"
  | "question_bank"
  | "assessments"
  | "career_profiling"
  | "reports"
  | "training"
  | "counseling"
  | "cms";

export const ROLE_LABELS: Record<RoleName, string> = {
  cj_admin: "CareerJudge Admin",
  corp_admin: "Corporate Admin",
  corp_exclusive: "Corporate Exclusive",
  psychometrician: "Psychometrician",
  sme: "SME (Subject Matter Expert)",
  reviewer: "Reviewer",
  trainer: "Trainer",
  group_admin: "Group Admin",
  counsellor: "Counsellor",
  channel_partner: "Channel Partner",
  individual: "Individual",
};

/** Allowed role names when creating a new role via the admin API. */
export const ROLE_NAME_CHOICES: RoleName[] = [
  "cj_admin",
  "corp_admin",
  "corp_exclusive",
  "psychometrician",
  "sme",
  "reviewer",
  "trainer",
  "group_admin",
  "counsellor",
  "channel_partner",
  "individual",
];

/**
 * Module visibility per role. ✓ means visible in the sidebar.
 *
 * SME vs Reviewer:
 *   - sme:      sees Question Bank (to author own questions), Assessments (view).
 *   - reviewer: sees Question Bank (to review), Assessments (view).
 */
export const MODULE_VISIBILITY: Record<RoleName, ModuleKey[]> = {
  cj_admin: [
    "dashboard",
    "profile",
    "users",
    "roles",
    "organizations",
    "question_bank",
    "assessments",
    "career_profiling",
    "reports",
    "training",
    "counseling",
    "cms",
  ],
  corp_admin: [
    "dashboard",
    "profile",
    "users",
    "organizations",
    "assessments",
    "reports",
    "training",
  ],
  corp_exclusive: ["dashboard", "profile", "users", "organizations", "assessments", "reports"],
  psychometrician: [
    "dashboard",
    "profile",
    "question_bank",
    "assessments",
    "career_profiling",
    "reports",
  ],
  sme: ["dashboard", "profile", "question_bank", "assessments"],
  reviewer: ["dashboard", "profile", "question_bank", "assessments"],
  trainer: ["dashboard", "profile", "assessments", "training"],
  group_admin: ["dashboard", "profile", "organizations", "assessments"],
  counsellor: ["dashboard", "profile", "assessments", "career_profiling", "reports", "counseling"],
  channel_partner: ["dashboard", "profile", "users", "organizations", "assessments", "reports"],
  individual: [
    "dashboard",
    "profile",
    "assessments",
    "career_profiling",
    "reports",
    "training",
    "counseling",
  ],
};

export interface NavItem {
  key: ModuleKey;
  label: string;
  to: string;
  icon: string; // lucide icon name
  /** Roles that can access this module. Derived from MODULE_VISIBILITY. */
  roles: RoleName[];
}

/** Icon names must match imports in Sidebar.tsx */
export const NAV_ITEMS: NavItem[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    to: "/dashboard",
    icon: "LayoutDashboard",
    roles: roleListFor("dashboard"),
  },
  {
    key: "profile",
    label: "Profile",
    to: "/profile",
    icon: "UserCircle",
    roles: roleListFor("profile"),
  },
  { key: "users", label: "Users", to: "/admin/users", icon: "Users", roles: roleListFor("users") },
  {
    key: "roles",
    label: "Roles & Permissions",
    to: "/admin/roles",
    icon: "ShieldCheck",
    roles: roleListFor("roles"),
  },
  {
    key: "organizations",
    label: "Organizations",
    to: "/organizations",
    icon: "Building2",
    roles: roleListFor("organizations"),
  },
  {
    key: "question_bank",
    label: "Question Bank",
    to: "/question-bank",
    icon: "BookOpen",
    roles: roleListFor("question_bank"),
  },
  {
    key: "assessments",
    label: "Assessments",
    to: "/assessments",
    icon: "ClipboardList",
    roles: roleListFor("assessments"),
  },
  {
    key: "career_profiling",
    label: "Career Profiling",
    to: "/career-profiling",
    icon: "Compass",
    roles: roleListFor("career_profiling"),
  },
  {
    key: "reports",
    label: "Reports",
    to: "/reports",
    icon: "BarChart3",
    roles: roleListFor("reports"),
  },
  {
    key: "training",
    label: "Training",
    to: "/training",
    icon: "GraduationCap",
    roles: roleListFor("training"),
  },
  {
    key: "counseling",
    label: "Counseling",
    to: "/counseling",
    icon: "MessageSquare",
    roles: roleListFor("counseling"),
  },
  { key: "cms", label: "CMS", to: "/cms", icon: "FileText", roles: roleListFor("cms") },
];

/** Helper that returns the list of roles that can see a given module. */
function roleListFor(module: ModuleKey): RoleName[] {
  return (Object.keys(MODULE_VISIBILITY) as RoleName[]).filter((role) =>
    MODULE_VISIBILITY[role].includes(module),
  );
}

export const APP_NAME = "CareerJudge";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/api";

export const TOKEN_STORAGE_KEY = "cj_auth_v1";

/** Modules that require cj_admin only (admin-only section). */
export const ADMIN_ONLY_MODULES: ModuleKey[] = ["users", "roles"];

/** Pretty label for a module key. */
export const MODULE_LABELS: Record<ModuleKey, string> = {
  dashboard: "Dashboard",
  profile: "Profile",
  users: "Users",
  roles: "Roles & Permissions",
  organizations: "Organizations",
  question_bank: "Question Bank",
  assessments: "Assessments",
  career_profiling: "Career Profiling",
  reports: "Reports",
  training: "Training",
  counseling: "Counseling",
  cms: "CMS",
};

/** Short description shown on the dashboard cards. */
export const MODULE_DESCRIPTIONS: Record<ModuleKey, string> = {
  dashboard: "Your personalized overview at a glance.",
  profile: "View and update your personal information.",
  users: "Manage user accounts, roles, and status.",
  roles: "Configure roles and assign module permissions.",
  organizations: "Manage corporate and group entities.",
  question_bank: "Author and curate assessment questions.",
  assessments: "Configure and run assessments.",
  career_profiling: "Map candidates to career paths.",
  reports: "Generate and download reports.",
  training: "Plan and deliver training programs.",
  counseling: "Schedule and track counseling sessions.",
  cms: "Manage static content and pages.",
};
