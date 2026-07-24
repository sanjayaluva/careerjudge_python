import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "@/components/layout/AdminRoute";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ProtectedRoute, PublicRoute } from "@/components/layout/ProtectedRoute";
import { ToastProvider } from "@/components/ui";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import LoginPage from "@/pages/auth/LoginPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";
import SignupPage from "@/pages/auth/SignupPage";
import VerifyEmailPage from "@/pages/auth/VerifyEmailPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import NotFoundPage from "@/pages/NotFoundPage";
import CareerProfilingPage from "@/pages/career-profiling/CareerProfilingPage";
import ProfilingSolutionDetailPage from "@/pages/career-profiling/ProfilingSolutionDetailPage";
import ReportsPage from "@/pages/reporting/ReportsPage";
import ReportDetailPage from "@/pages/reporting/ReportDetailPage";
import TrainingPage from "@/pages/training/TrainingPage";
import TrainingCourseDetailPage from "@/pages/training/TrainingCourseDetailPage";
import TrainingCourseEditorPage from "@/pages/training/TrainingCourseEditorPage";
import CounselingPage from "@/pages/counseling/CounselingPage";
import CMSPage from "@/pages/cms/CMSPage";
import CMSPageViewer from "@/pages/cms/CMSPageViewer";
import TasksPage from "@/pages/tasks/TasksPage";
import TaskDetailPage from "@/pages/tasks/TaskDetailPage";
import { PaymentSuccessPage, PaymentCancelPage } from "@/pages/payments/PaymentResultPages";
import { PublicHomepage } from "@/pages/PublicHomepage";
import ProfilePage from "@/pages/account/ProfilePage";
import SettingsPage from "@/pages/account/SettingsPage";
import PermissionsPage from "@/pages/admin/PermissionsPage";
import RolesPage from "@/pages/admin/RolesPage";
import UsersPage from "@/pages/admin/UsersPage";
import UserViewPage from "@/pages/admin/UserViewPage";
import OrganizationsPage from "@/pages/organizations/OrganizationsPage";
import OrganizationDetailPage from "@/pages/organizations/OrganizationDetailPage";
import QuestionBankPage from "@/pages/question-bank/QuestionBankPage";
import QuestionDetailPage from "@/pages/question-bank/QuestionDetailPage";
import QuestionEditorPage from "@/pages/question-bank/QuestionEditorPage";
import AssessmentsPage from "@/pages/assessment/AssessmentsPage";
import AssessmentDetailPage from "@/pages/assessment/AssessmentDetailPage";
import SessionPlayerPage from "@/pages/assessment/SessionPlayerPage";
import SessionResultsPage from "@/pages/assessment/SessionResultsPage";
import { useAuthStore } from "@/stores/auth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function AuthHydrator({ children }: { children: React.ReactNode }) {
  const hydrate = useAuthStore((s) => s.hydrate);
  useEffect(() => {
    hydrate();
  }, [hydrate]);
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <AuthHydrator>
            <Routes>
              {/* Public */}
              <Route
                path="/login"
                element={
                  <PublicRoute>
                    <LoginPage />
                  </PublicRoute>
                }
              />
              <Route
                path="/signup"
                element={
                  <PublicRoute>
                    <SignupPage />
                  </PublicRoute>
                }
              />
              <Route path="/verify-email/:token" element={<VerifyEmailPage />} />
              <Route
                path="/forgot-password"
                element={
                  <PublicRoute>
                    <ForgotPasswordPage />
                  </PublicRoute>
                }
              />
              <Route path="/reset-password/:token" element={<ResetPasswordPage />} />

              {/* Protected */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardShell />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route
                  path="admin/users"
                  element={
                    <AdminRoute module="users">
                      <UsersPage />
                    </AdminRoute>
                  }
                />
                <Route
                  path="admin/users/:id"
                  element={
                    <AdminRoute module="users">
                      <UserViewPage />
                    </AdminRoute>
                  }
                />
                <Route
                  path="admin/roles"
                  element={
                    <AdminRoute module="roles">
                      <RolesPage />
                    </AdminRoute>
                  }
                />
                <Route
                  path="admin/permissions"
                  element={
                    <AdminRoute module="roles">
                      <PermissionsPage />
                    </AdminRoute>
                  }
                />
                {/* Placeholder routes for Phase 2+ modules */}
                <Route path="organizations" element={<OrganizationsPage />} />
                <Route path="organizations/:id" element={<OrganizationDetailPage />} />
                <Route path="question-bank" element={<QuestionBankPage />} />
                <Route path="question-bank/new" element={<QuestionEditorPage />} />
                <Route path="question-bank/:id/edit" element={<QuestionEditorPage />} />
                <Route path="question-bank/:id" element={<QuestionDetailPage />} />
                <Route path="assessments" element={<AssessmentsPage />} />
                <Route path="assessments/:id" element={<AssessmentDetailPage />} />
                <Route
                  path="assessments/sessions/:sessionId/results"
                  element={<SessionResultsPage />}
                />
                <Route path="career-profiling" element={<CareerProfilingPage />} />
                <Route path="career-profiling/:id" element={<ProfilingSolutionDetailPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="reports/:id" element={<ReportDetailPage />} />
                <Route path="training" element={<TrainingPage />} />
                <Route path="training/new" element={<TrainingCourseEditorPage />} />
                <Route path="training/:id" element={<TrainingCourseDetailPage />} />
                <Route path="training/:id/edit" element={<TrainingCourseEditorPage />} />
                <Route path="counseling" element={<CounselingPage />} />
                <Route path="cms" element={<CMSPage />} />
                <Route path="page/:slug" element={<CMSPageViewer />} />
                <Route path="tasks" element={<TasksPage />} />
                <Route path="tasks/:id" element={<TaskDetailPage />} />
              </Route>

              {/* Fullscreen session player — outside DashboardShell so the
                candidate gets a distraction-free test-taking experience
                with no app sidebar/topbar. Per SRS 00_question_types_spec.json
                the layout is three-panel: sidebar + content + footer. */}
              <Route
                path="/assessments/sessions/:sessionId"
                element={
                  <ProtectedRoute>
                    <SessionPlayerPage />
                  </ProtectedRoute>
                }
              />

              {/* Public homepage (landing page) */}
              <Route path="/" element={<PublicHomepage />} />

              {/* CMS page catch-all — tries to render a CMS page by slug
                  before falling back to 404. This makes /about-us work
                  without needing /page/about-us prefix. */}
              <Route path="/:slug" element={<CMSPageViewer />} />

              {/* Payment result pages (after Stripe/Razorpay redirect) */}
              <Route path="/payments/success" element={<PaymentSuccessPage />} />
              <Route path="/payments/cancel" element={<PaymentCancelPage />} />

              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AuthHydrator>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
