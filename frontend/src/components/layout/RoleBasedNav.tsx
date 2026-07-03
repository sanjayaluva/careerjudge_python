/**
 * RoleBasedNav — config-driven nav, filtered by the current user's role.
 *
 * Reads NAV_ITEMS (constants.ts) and keeps only the ones whose `roles`
 * array contains the current user's role. Clicking an item navigates
 * via React Router's <Link>.
 */
import {
  BarChart3,
  BookOpen,
  Building2,
  ClipboardList,
  Compass,
  FileText,
  FolderTree,
  GraduationCap,
  LayoutDashboard,
  MessageSquare,
  ShieldCheck,
  UserCircle,
  Users,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { NAV_ITEMS, type ModuleKey } from "@/lib/constants";
import { usePermissions } from "@/hooks/usePermissions";
import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  LayoutDashboard,
  UserCircle,
  Users,
  ShieldCheck,
  Building2,
  BookOpen,
  ClipboardList,
  Compass,
  BarChart3,
  GraduationCap,
  MessageSquare,
  FileText,
  FolderTree,
};

export interface RoleBasedNavProps {
  /** Called after a nav item is clicked — used by mobile sidebar to close. */
  onNavigate?: () => void;
  className?: string;
}

export function RoleBasedNav({ onNavigate, className }: RoleBasedNavProps) {
  const { can } = usePermissions();
  const visibleItems = NAV_ITEMS.filter((item) => can(item.key));

  return (
    <nav aria-label="Primary" className={cn("flex flex-col gap-0.5", className)}>
      {visibleItems.map((item) => {
        const Icon = ICONS[item.icon] ?? LayoutDashboard;
        return (
          <NavLink
            key={item.key as ModuleKey}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-1",
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
              )
            }
            aria-current="page"
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
