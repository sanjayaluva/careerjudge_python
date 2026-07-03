import { useEffect, useState, type ReactNode } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { MODULE_LABELS } from "@/lib/constants";

export interface DashboardShellProps {
  children?: ReactNode;
}

/** Maps the current path to a topbar title — used when no explicit title is provided. */
function titleFromPath(pathname: string): { title: string; subtitle?: string } {
  if (pathname === "/" || pathname === "/dashboard") {
    return { title: "Dashboard", subtitle: "Your personalized overview" };
  }
  if (pathname.startsWith("/question-bank/categories")) {
    return {
      title: "Question Categories",
      subtitle: "Organize questions into hierarchical categories",
    };
  }
  if (pathname.startsWith("/admin/users")) return { title: "Users", subtitle: "Manage accounts" };
  if (pathname.startsWith("/admin/roles")) return { title: "Roles & Permissions" };
  if (pathname.startsWith("/admin/permissions")) return { title: "Permissions Catalog" };
  if (pathname.startsWith("/profile")) return { title: "Profile" };
  if (pathname.startsWith("/settings")) return { title: "Settings" };

  const segments = pathname.split("/").filter(Boolean);
  if (segments.length > 0) {
    const map: Record<string, string> = {
      organizations: MODULE_LABELS.organizations,
      "question-bank": MODULE_LABELS.question_bank,
      assessments: MODULE_LABELS.assessments,
      "career-profiling": MODULE_LABELS.career_profiling,
      reports: MODULE_LABELS.reports,
      training: MODULE_LABELS.training,
      counseling: MODULE_LABELS.counseling,
      cms: MODULE_LABELS.cms,
    };
    return { title: map[segments[0] ?? ""] ?? "Page" };
  }
  return { title: "CareerJudge" };
}

export function DashboardShell({ children }: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { title, subtitle } = titleFromPath(location.pathname);

  // Close the sidebar on every route change.
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Scroll to top on route change.
  useEffect(() => {
    const main = document.getElementById("dashboard-main");
    if (main) main.scrollTo({ top: 0 });
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} subtitle={subtitle} onOpenSidebar={() => setSidebarOpen(true)} />
        <main id="dashboard-main" className="flex-1 overflow-y-auto px-4 py-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">{children ?? <Outlet />}</div>
        </main>
      </div>
    </div>
  );
}
