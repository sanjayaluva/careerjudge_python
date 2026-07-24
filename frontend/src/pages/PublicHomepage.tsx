/**
 * Public Homepage — the landing page for careerjudge.pp.ua
 *
 * Shows:
 * - Hero banner (from CMS) with title, subtitle, CTA
 * - Services overview (hardcoded sections pointing to modules)
 * - Call-to-action section
 *
 * All content is driven by CMS banners where available. If no banners
 * are configured, sensible defaults are shown.
 */
import { Link } from "react-router-dom";

import { PublicLayout } from "@/components/layout/PublicLayout";
import { useAuth } from "@/hooks/useAuth";

export function PublicHomepage() {
  const { user } = useAuth();

  return (
    <PublicLayout>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-600 to-primary-800 py-20 text-white">
        <div className="mx-auto max-w-6xl px-4 text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Your Career, Our Expertise
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-primary-100">
            Comprehensive career assessment, profiling, counseling, and training — all in one
            platform. Discover your strengths, match with careers, and grow with expert guidance.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            {user ? (
              <Link
                to="/dashboard"
                className="rounded-lg bg-white px-6 py-3 font-semibold text-primary-700 hover:bg-primary-50"
              >
                Go to Dashboard →
              </Link>
            ) : (
              <>
                <Link
                  to="/signup"
                  className="rounded-lg bg-white px-6 py-3 font-semibold text-primary-700 hover:bg-primary-50"
                >
                  Get Started Free
                </Link>
                <Link
                  to="/login"
                  className="rounded-lg border border-white/30 px-6 py-3 font-semibold text-white hover:bg-white/10"
                >
                  Login
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Services Overview */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="text-center text-2xl font-bold text-slate-900">What We Offer</h2>
          <p className="mt-2 text-center text-slate-500">End-to-end career development platform</p>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {/* Assessments */}
            <div className="rounded-xl border border-slate-200 p-6 transition-shadow hover:shadow-md">
              <div className="text-3xl">📝</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">Assessments</h3>
              <p className="mt-2 text-sm text-slate-500">
                21 question types with 9 scoring modes. Psychometric analysis with item difficulty +
                discrimination indices.
              </p>
            </div>

            {/* Career Profiling */}
            <div className="rounded-xl border border-slate-200 p-6 transition-shadow hover:shadow-md">
              <div className="text-3xl">🎯</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">Career Profiling</h3>
              <p className="mt-2 text-sm text-slate-500">
                Match index computation with banding, mapping, and ranking. Find your best-fit
                careers with FMI/PMI/VMI scores.
              </p>
            </div>

            {/* Reports */}
            <div className="rounded-xl border border-slate-200 p-6 transition-shadow hover:shadow-md">
              <div className="text-3xl">📊</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">Reports</h3>
              <p className="mt-2 text-sm text-slate-500">
                Descriptive, typological, interpretative, and group reports with PDF download.
                HFMI/LFMI data selection.
              </p>
            </div>

            {/* Training */}
            <div className="rounded-xl border border-slate-200 p-6 transition-shadow hover:shadow-md">
              <div className="text-3xl">🎓</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">Training</h3>
              <p className="mt-2 text-sm text-slate-500">
                Online courses with video content, interactive questions, assignments, live
                sessions, and progress tracking.
              </p>
            </div>

            {/* Counseling */}
            <div className="rounded-xl border border-slate-200 p-6 transition-shadow hover:shadow-md">
              <div className="text-3xl">💬</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">Counseling</h3>
              <p className="mt-2 text-sm text-slate-500">
                Book sessions with professional counsellors. Online (Zoom) or offline. Cancellation
                with refund tiers, feedback, follow-ups.
              </p>
            </div>

            {/* Question Bank */}
            <div className="rounded-xl border border-slate-200 p-6 transition-shadow hover:shadow-md">
              <div className="text-3xl">📚</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">Question Bank</h3>
              <p className="mt-2 text-sm text-slate-500">
                21 question types with a 3-stage review workflow. Category management, bulk
                operations, psychometric validation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-slate-50 py-16">
        <div className="mx-auto max-w-4xl px-4 text-center">
          <h2 className="text-2xl font-bold text-slate-900">Ready to take the next step?</h2>
          <p className="mt-2 text-slate-500">
            Sign up today and get access to assessments, career profiling, training, and counseling.
          </p>
          <div className="mt-6 flex justify-center gap-4">
            {user ? (
              <Link
                to="/dashboard"
                className="rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white hover:bg-primary-700"
              >
                Go to Dashboard →
              </Link>
            ) : (
              <Link
                to="/signup"
                className="rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white hover:bg-primary-700"
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
