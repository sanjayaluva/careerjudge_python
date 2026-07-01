import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "@/components/layout/AdminRoute";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ProtectedRoute, PublicRoute } from "@/components/layout/ProtectedRoute";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import LoginPage from "@/pages/auth/LoginPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";
import SignupPage from "@/pages/auth/SignupPage";
import VerifyEmailPage from "@/pages/auth/VerifyEmailPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import NotFoundPage from "@/pages/NotFoundPage";
import PlaceholderPage from "@/pages/PlaceholderPage";
import ProfilePage from "@/pages/account/ProfilePage";
import SettingsPage from "@/pages/account/SettingsPage";
import PermissionsPage from "@/pages/admin/PermissionsPage";
import RolesPage from "@/pages/admin/RolesPage";
import UsersPage from "@/pages/admin/UsersPage";
import UserViewPage from "@/pages/admin/UserViewPage";
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
              <Route path="organizations" element={<PlaceholderPage title="Organizations" />} />
              <Route path="question-bank" element={<PlaceholderPage title="Question Bank" />} />
              <Route path="assessments" element={<PlaceholderPage title="Assessments" />} />
              <Route
                path="career-profiling"
                element={<PlaceholderPage title="Career Profiling" />}
              />
              <Route path="reports" element={<PlaceholderPage title="Reports" />} />
              <Route path="training" element={<PlaceholderPage title="Training" />} />
              <Route path="counseling" element={<PlaceholderPage title="Counseling" />} />
              <Route path="cms" element={<PlaceholderPage title="CMS" />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthHydrator>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
