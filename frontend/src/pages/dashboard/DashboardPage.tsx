import {
  BarChart3,
  BookOpen,
  Building2,
  ClipboardList,
  Compass,
  FileText,
  GraduationCap,
  LayoutDashboard,
  MessageSquare,
  ShieldCheck,
  UserCircle,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui";
import {
  MODULE_DESCRIPTIONS,
  MODULE_LABELS,
  NAV_ITEMS,
  ROLE_LABELS,
  type ModuleKey,
  type RoleName,
} from "@/lib/constants";
import { useAuth } from "@/hooks/useAuth";

const ICONS: Record<string, LucideIcon> = {
  LayoutDashboard,
  UserCircle,
  Users,
  ShieldCheck,
  Building2,
  BookOpen,
  ClipboardList,
  Compass,
  BarChart3,
  GraduationCap,
  MessageSquare,
  FileText,
};

export default function DashboardPage() {
  const { user, me } = useAuth();
  const [searchParams] = useSearchParams();
  const denied = searchParams.get("denied");

  const roleLabel = user?.role ? ROLE_LABELS[user.role] : null;

  // Filter modules by the user's role — only show what they can actually access.
  // Exclude 'dashboard' (we're on it) and 'profile' (shown in topbar avatar menu).
  const userRole = (user?.role ?? "individual") as RoleName;
  const visibleModules = NAV_ITEMS.filter(
    (item) => item.key !== "dashboard" && item.key !== "profile" && item.roles.includes(userRole),
  );

  return (
    <div className="space-y-6">
      {denied && (
        <Alert variant="warning">
          <AlertDescription>
            You don&apos;t have permission to access that page. You&apos;ve been redirected to your
            dashboard.
          </AlertDescription>
        </Alert>
      )}

      <Card className="border-l-0 border-t-0 border-r-0">
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-slate-500">Welcome back,</p>
              <CardTitle className="text-2xl">
                {me?.full_name || user?.full_name || user?.email}
              </CardTitle>
              <p className="mt-1 text-sm text-slate-500">{user?.email}</p>
            </div>
            <div className="flex flex-col items-start gap-2 sm:items-end">
              {roleLabel && (
                <Badge variant="primary" className="text-xs">
                  {roleLabel}
                </Badge>
              )}
              {me && !me.is_email_verified && (
                <Badge variant="warning" className="text-xs">
                  Email not verified
                </Badge>
              )}
              {me?.is_trial_user && (
                <Badge variant="default" className="text-xs">
                  Trial account
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-600">
            This is your personalized overview. The cards below show the modules you can access
            based on your role. More detailed dashboards will be available in Phase 2.
          </p>
        </CardContent>
      </Card>

      <div className="px-6 pb-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Your modules
        </h2>
        {visibleModules.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-slate-500">
              You don&apos;t have access to any modules yet. Contact an administrator if you believe
              this is an error.
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleModules.map((item) => {
              const Icon = ICONS[item.icon] ?? LayoutDashboard;
              return (
                <Link
                  key={item.key as ModuleKey}
                  to={item.to}
                  className="group block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-all hover:border-primary-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
                >
                  <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-md bg-primary-50 text-primary-600 group-hover:bg-primary-100">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">
                    {MODULE_LABELS[item.key]}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">{MODULE_DESCRIPTIONS[item.key]}</p>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
