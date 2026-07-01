import { type ReactNode } from "react";

import { APP_NAME } from "@/lib/constants";

export interface AuthLayoutProps {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Shared two-column layout for auth pages (login/signup/reset/etc).
 * Left: brand panel (indigo gradient, hidden on mobile).
 * Right: form card.
 */
export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <aside className="relative hidden w-1/2 flex-col justify-between bg-gradient-to-br from-primary-700 via-primary-600 to-primary-800 p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-white/15 font-bold"
          >
            CJ
          </span>
          <span className="text-xl font-bold tracking-tight">{APP_NAME}</span>
        </div>

        <div className="max-w-md space-y-4">
          <h2 className="text-3xl font-bold leading-tight">
            Modern career assessment, profiling, and counseling.
          </h2>
          <p className="text-primary-100">
            Assess candidates, profile careers, and deliver counseling — all from one platform built
            for educators and enterprises.
          </p>
        </div>

        <p className="text-xs text-primary-200">
          &copy; {new Date().getFullYear()} {APP_NAME}. All rights reserved.
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex w-full flex-col items-center justify-center bg-slate-50 px-4 py-12 lg:w-1/2">
        <div className="w-full max-w-md">
          {/* Mobile-only brand */}
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <span
              aria-hidden="true"
              className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 text-sm font-bold text-white"
            >
              CJ
            </span>
            <span className="text-lg font-bold tracking-tight text-slate-900">{APP_NAME}</span>
          </div>

          <div className="mb-6">
            <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
            {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
          </div>

          {children}

          {footer && <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>}
        </div>
      </main>
    </div>
  );
}
