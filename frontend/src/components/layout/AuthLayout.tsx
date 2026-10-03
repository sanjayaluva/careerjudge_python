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
      <aside className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-primary-700 via-primary-600 to-primary-900 p-12 text-white lg:flex">
        {/* Decorative glow — purely visual */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-white/10 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-40 -left-24 h-[24rem] w-[24rem] rounded-full bg-primary-400/30 blur-3xl"
        />

        <div className="relative flex items-center gap-3">
          <span
            aria-hidden="true"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/15 font-bold ring-1 ring-inset ring-white/20"
          >
            CJ
          </span>
          <span className="text-xl font-bold tracking-tight">{APP_NAME}</span>
        </div>

        <div className="relative max-w-md space-y-4">
          <h2 className="text-3xl font-bold leading-tight tracking-tight">
            Modern career assessment, profiling, and counseling.
          </h2>
          <p className="text-base leading-relaxed text-primary-100">
            Assess candidates, profile careers, and deliver counseling — all from one platform built
            for educators and enterprises.
          </p>
        </div>

        <p className="relative text-xs text-primary-200">
          &copy; {new Date().getFullYear()} {APP_NAME}. All rights reserved.
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex w-full flex-col items-center justify-center bg-slate-50 px-4 py-12 lg:w-1/2">
        <div className="w-full max-w-md">
          {/* Mobile-only brand */}
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <span
              aria-hidden="true"
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-sm font-bold text-white shadow-sm"
            >
              CJ
            </span>
            <span className="text-[17px] font-bold tracking-tight text-slate-900">{APP_NAME}</span>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
            <div className="mb-6">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
              {description && (
                <p className="mt-1.5 text-sm leading-snug text-slate-500">{description}</p>
              )}
            </div>

            {children}
          </div>

          {footer && <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>}
        </div>
      </main>
    </div>
  );
}
