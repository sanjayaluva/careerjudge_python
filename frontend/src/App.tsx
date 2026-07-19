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
import PlaceholderPage from "@/pages/PlaceholderPage";
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
                <Route path="training" element={<PlaceholderPage title="Training" />} />
                <Route path="counseling" element={<PlaceholderPage title="Counseling" />} />
                <Route path="cms" element={<PlaceholderPage title="CMS" />} />
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

              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AuthHydrator>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
