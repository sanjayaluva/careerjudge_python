/**
 * Public Homepage — the landing page for careerjudge.pp.ua
 *
 * Shows a static marketing landing page:
 * - Hero banner with title, subtitle, CTA
 * - Services overview (sections pointing to modules)
 * - Call-to-action section
 *
 * Content is static and user-aware (guest vs. signed-in CTAs). The SRS does
 * not require a CMS-driven homepage, so the copy is hardcoded here (BUG-3:
 * a previous comment claimed CMS-driven content that was never fetched).
 */
import { Link } from "react-router-dom";

import { PublicLayout } from "@/components/layout/PublicLayout";
import { useAuth } from "@/hooks/useAuth";

export function PublicHomepage() {
  const { user } = useAuth();

  return (
    <PublicLayout>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 py-20 text-white sm:py-24">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-white/10 blur-3xl"
        />
        <div className="relative mx-auto max-w-6xl px-4 text-center sm:px-6">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Your Career, Our Expertise
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg leading-relaxed text-primary-100">
            Comprehensive career assessment, profiling, counseling, and training — all in one
            platform. Discover your strengths, match with careers, and grow with expert guidance.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
            {user ? (
              <Link
                to="/dashboard"
                className="inline-flex h-12 items-center justify-center rounded-lg bg-white px-6 font-semibold text-primary-700 shadow-sm transition-colors hover:bg-primary-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-700"
              >
                Go to Dashboard →
              </Link>
            ) : (
              <>
                <Link
                  to="/signup"
                  className="inline-flex h-12 items-center justify-center rounded-lg bg-white px-6 font-semibold text-primary-700 shadow-sm transition-colors hover:bg-primary-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-700"
                >
                  Get Started Free
                </Link>
                <Link
                  to="/login"
                  className="inline-flex h-12 items-center justify-center rounded-lg border border-white/30 px-6 font-semibold text-white transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-700"
                >
                  Login
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Services Overview */}
      <section className="bg-white py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            What We Offer
          </h2>
          <p className="mt-2 text-center text-slate-500">End-to-end career development platform</p>

          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {/* Assessments */}
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-card transition-all hover:border-primary-200 hover:shadow-popover">
              <div className="text-3xl">📝</div>
              <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-900">
                Assessments
              </h3>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                21 question types with 9 scoring modes. Psychometric analysis with item difficulty +
                discrimination indices.
              </p>
            </div>

            {/* Career Profiling */}
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-card transition-all hover:border-primary-200 hover:shadow-popover">
              <div className="text-3xl">🎯</div>
              <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-900">
                Career Profiling
              </h3>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                Match index computation with banding, mapping, and ranking. Find your best-fit
                careers with FMI/PMI/VMI scores.
              </p>
            </div>

            {/* Reports */}
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-card transition-all hover:border-primary-200 hover:shadow-popover">
              <div className="text-3xl">📊</div>
              <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-900">Reports</h3>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                Descriptive, typological, interpretative, and group reports with PDF download.
                HFMI/LFMI data selection.
              </p>
            </div>

            {/* Training */}
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-card transition-all hover:border-primary-200 hover:shadow-popover">
              <div className="text-3xl">🎓</div>
              <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-900">Training</h3>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                Online courses with video content, interactive questions, assignments, live
                sessions, and progress tracking.
              </p>
            </div>

            {/* Counseling */}
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-card transition-all hover:border-primary-200 hover:shadow-popover">
              <div className="text-3xl">💬</div>
              <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-900">
                Counseling
              </h3>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                Book sessions with professional counsellors. Online (Zoom) or offline. Cancellation
                with refund tiers, feedback, follow-ups.
              </p>
            </div>

            {/* Question Bank */}
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-card transition-all hover:border-primary-200 hover:shadow-popover">
              <div className="text-3xl">📚</div>
              <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-900">
                Question Bank
              </h3>
              <p className="mt-2 text-sm leading-snug text-slate-500">
                21 question types with a 3-stage review workflow. Category management, bulk
                operations, psychometric validation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-slate-200 bg-slate-50 py-16 sm:py-20">
        <div className="mx-auto max-w-4xl px-4 text-center sm:px-6">
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Ready to take the next step?
          </h2>
          <p className="mt-2 leading-relaxed text-slate-500">
            Sign up today and get access to assessments, career profiling, training, and counseling.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            {user ? (
              <Link
                to="/dashboard"
                className="inline-flex h-12 items-center justify-center rounded-lg bg-primary-600 px-6 font-semibold text-white shadow-sm transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
              >
                Go to Dashboard →
              </Link>
            ) : (
              <Link
                to="/signup"
                className="inline-flex h-12 items-center justify-center rounded-lg bg-primary-600 px-6 font-semibold text-white shadow-sm transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
              >
                Sign up free
              </Link>
            )}
          </div>
        </div>
      </section>
    </PublicLayout>
  );
}
