import { Bell, ChevronDown, LogOut, Settings, UserCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  Avatar,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui";
import { ROLE_LABELS } from "@/lib/constants";
import { useAuth } from "@/hooks/useAuth";
import { logout as apiLogout } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { extractApiError } from "@/api/client";

export interface TopbarProps {
  /** Mobile: open the sidebar. */
  onOpenSidebar: () => void;
  /** Page title to display in the topbar. */
  title: string;
  /** Optional subtitle/description. */
  subtitle?: string;
}

export function Topbar({ onOpenSidebar, title, subtitle }: TopbarProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const clear = useAuthStore((s) => s.clear);

  const handleLogout = async () => {
    try {
      if (refreshToken && accessToken) {
        await apiLogout(refreshToken, accessToken);
      }
    } catch (err) {
      // Even if the network call fails, we still clear local state.
      console.warn("Logout API call failed:", extractApiError(err));
    } finally {
      clear();
      navigate("/login", { replace: true });
    }
  };

  const roleLabel = user?.role ? ROLE_LABELS[user.role] : null;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:px-6">
      <button
        type="button"
        onClick={onOpenSidebar}
        className="rounded-md p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
        aria-label="Open sidebar"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-slate-900">{title}</h1>
        {subtitle && <p className="truncate text-xs text-slate-500">{subtitle}</p>}
      </div>

      <Button
        variant="ghost"
        size="icon"
        aria-label="Notifications (placeholder)"
        className="text-slate-500"
      >
        <Bell className="h-5 w-5" />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-transparent p-1 pr-2 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
            aria-label="Open user menu"
          >
            <Avatar name={user?.full_name} email={user?.email} size="sm" />
            <span className="hidden text-sm font-medium text-slate-700 sm:inline">
              {user?.full_name || user?.email}
            </span>
            <ChevronDown className="hidden h-4 w-4 text-slate-400 sm:inline" aria-hidden="true" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel>
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-semibold normal-case text-slate-900">
                {user?.full_name || "Account"}
              </span>
              <span className="text-xs font-normal normal-case text-slate-500">
                {roleLabel ? roleLabel : "Signed in"}
              </span>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate("/profile")}>
            <UserCircle className="h-4 w-4" aria-hidden="true" />
            <span>Profile</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/settings")}>
            <Settings className="h-4 w-4" aria-hidden="true" />
            <span>Settings</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem destructive onClick={handleLogout}>
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span>Logout</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
