import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, ChevronDown, LogOut, Settings, UserCircle } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Avatar,
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
import {
  deleteNotification,
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from "@/api/notifications";

export interface TopbarProps {
  /** Mobile: open the sidebar. */
  onOpenSidebar: () => void;
  /** Page title to display in the topbar. */
  title: string;
  /** Optional subtitle/description. */
  subtitle?: string;
}

const NOTIF_TYPE_COLORS: Record<string, string> = {
  info: "text-blue-500",
  success: "text-green-500",
  warning: "text-amber-500",
  error: "text-red-500",
  review: "text-purple-500",
  assessment: "text-indigo-500",
  session: "text-teal-500",
  system: "text-slate-500",
};

const NOTIF_TYPE_ICONS: Record<string, string> = {
  info: "ℹ",
  success: "✓",
  warning: "⚠",
  error: "✕",
  review: "🔍",
  assessment: "📋",
  session: "📝",
  system: "⚙",
};

export function Topbar({ onOpenSidebar, title, subtitle }: TopbarProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const clear = useAuthStore((s) => s.clear);
  const [notifOpen, setNotifOpen] = useState(false);

  // Poll unread count every 30 seconds
  const { data: unreadCount } = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: () => getUnreadCount(),
    refetchInterval: 30_000,
  });

  // Fetch notifications when the dropdown is opened
  const { data: notifications } = useQuery({
    queryKey: ["notifications-list"],
    queryFn: () => listNotifications(),
    enabled: notifOpen,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => markNotificationRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications-unread-count"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications-list"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications-unread-count"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications-list"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteNotification(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications-unread-count"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications-list"] });
    },
  });

  const handleNotificationClick = (notif: AppNotification) => {
    if (!notif.is_read) {
      markReadMutation.mutate(notif.id);
    }
    setNotifOpen(false);
    if (notif.link) {
      navigate(notif.link);
    }
  };

  const handleLogout = async () => {
    try {
      if (refreshToken && accessToken) {
        await apiLogout(refreshToken, accessToken);
      }
    } catch (err) {
      console.warn("Logout API call failed:", extractApiError(err));
    } finally {
      queryClient.clear();
      clear();
      navigate("/login", { replace: true });
    }
  };

  const roleLabel = user?.role ? ROLE_LABELS[user.role] : null;
  const notifList = (notifications ?? []).slice(0, 20);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:px-6">
      <button
        type="button"
        onClick={onOpenSidebar}
        className="rounded-md p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
        aria-label="Open sidebar"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-slate-900">{title}</h1>
        {subtitle && <p className="truncate text-xs text-slate-500">{subtitle}</p>}
      </div>

      {/* Notification bell with dropdown */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setNotifOpen((v) => !v)}
          className="relative rounded-md p-2 text-slate-500 hover:bg-slate-100"
          aria-label={`Notifications${unreadCount ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="h-5 w-5" />
          {unreadCount !== undefined && unreadCount > 0 && (
            <span className="absolute right-0.5 top-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>

        {notifOpen && (
          <>
            {/* Click-away overlay */}
            <div className="fixed inset-0 z-40" onClick={() => setNotifOpen(false)} />

            {/* Notification dropdown panel */}
            <div className="absolute right-0 top-full z-50 mt-2 w-96 max-w-[calc(100vw-2rem)] rounded-lg border border-slate-200 bg-white shadow-lg">
              <div className="flex items-center justify-between border-b border-slate-100 p-3">
                <h3 className="text-sm font-semibold text-slate-900">Notifications</h3>
                {unreadCount !== undefined && unreadCount > 0 && (
                  <button
                    onClick={() => markAllReadMutation.mutate()}
                    className="text-xs text-primary-600 hover:underline"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-96 overflow-y-auto">
                {notifList.length === 0 ? (
                  <p className="py-8 text-center text-sm text-slate-400">No notifications yet.</p>
                ) : (
                  notifList.map((notif) => (
                    <div
                      key={notif.id}
                      className={`flex items-start gap-3 border-b border-slate-50 p-3 transition-colors hover:bg-slate-50 ${
                        !notif.is_read ? "bg-blue-50/40" : ""
                      }`}
                    >
                      <span
                        className={`mt-0.5 text-lg ${NOTIF_TYPE_COLORS[notif.notification_type] ?? "text-slate-400"}`}
                      >
                        {NOTIF_TYPE_ICONS[notif.notification_type] ?? "•"}
                      </span>
                      <div
                        className="flex-1 cursor-pointer"
                        onClick={() => handleNotificationClick(notif)}
                      >
                        <div className="flex items-center gap-2">
                          {!notif.is_read && (
                            <span className="h-2 w-2 shrink-0 rounded-full bg-blue-500" />
                          )}
                          <p className="text-sm font-medium text-slate-900">{notif.title}</p>
                        </div>
                        <p className="mt-0.5 text-xs text-slate-600">{notif.message}</p>
                        <p className="mt-1 text-[10px] text-slate-400">
                          {new Date(notif.created_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMutation.mutate(notif.id);
                        }}
                        className="text-slate-300 hover:text-red-500"
                        aria-label="Delete notification"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </div>

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
