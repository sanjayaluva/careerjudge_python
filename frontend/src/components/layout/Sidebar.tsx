import { X } from "lucide-react";

import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { RoleBasedNav } from "./RoleBasedNav";

export interface SidebarProps {
  /** Mobile: controlled open state. */
  open: boolean;
  onClose: () => void;
  className?: string;
}

export function Sidebar({ open, onClose, className }: SidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
          aria-hidden="true"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
          className,
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-6">
          <a
            href="/dashboard"
            className="flex items-center gap-2 font-bold text-slate-900"
            aria-label="CareerJudge home"
          >
            <span
              aria-hidden="true"
              className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 text-white"
            >
              CJ
            </span>
            <span className="text-lg tracking-tight">{APP_NAME}</span>
          </a>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-500 hover:bg-slate-100 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <RoleBasedNav onNavigate={onClose} />
        </div>

        <div className="border-t border-slate-200 p-4 text-xs text-slate-400">
          <p>&copy; {new Date().getFullYear()} {APP_NAME}</p>
        </div>
      </aside>
    </>
  );
}
