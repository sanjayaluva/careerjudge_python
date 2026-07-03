import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
} from "@/components/ui";
import { retrieveUser } from "@/api/users";
import { extractApiError } from "@/api/client";
import { ROLE_LABELS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";

export default function UserViewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const userId = Number(id);

  const {
    data: user,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["admin", "users", userId],
    queryFn: () => retrieveUser(userId),
    enabled: !Number.isNaN(userId),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !user) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load user. {extractApiError(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/admin/users" className="text-sm text-primary-600 hover:underline">
            ← Back to users
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">{user.full_name || "—"}</h1>
          <p className="text-sm text-slate-500">{user.email}</p>
        </div>
        <Button onClick={() => navigate(`/admin/users?edit=${user.id}`)}>Edit user</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account information</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Full name
              </dt>
              <dd className="mt-1 text-sm text-slate-900">{user.full_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Email</dt>
              <dd className="mt-1 text-sm text-slate-900">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Phone</dt>
              <dd className="mt-1 text-sm text-slate-900">{user.phone || "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Role</dt>
              <dd className="mt-1">
                {user.role ? (
                  <Badge variant="primary">{ROLE_LABELS[user.role]}</Badge>
                ) : (
                  <Badge variant="outline">No role</Badge>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</dt>
              <dd className="mt-1 flex flex-wrap gap-1">
                {user.is_active ? (
                  <Badge variant="success">Active</Badge>
                ) : (
                  <Badge variant="warning">Inactive</Badge>
                )}
                {user.is_email_verified && <Badge variant="default">Verified</Badge>}
                {user.is_trial_user && <Badge variant="outline">Trial</Badge>}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Joined</dt>
              <dd className="mt-1 text-sm text-slate-900">{formatDate(user.created_at)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {user.profile && (
        <Card>
          <CardHeader>
            <CardTitle>Profile details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Gender
                </dt>
                <dd className="mt-1 text-sm capitalize text-slate-900">
                  {user.profile.gender || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Mobile
                </dt>
                <dd className="mt-1 text-sm text-slate-900">{user.profile.mobile || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Date of birth
                </dt>
                <dd className="mt-1 text-sm text-slate-900">{user.profile.date_of_birth || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">City</dt>
                <dd className="mt-1 text-sm text-slate-900">{user.profile.city || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  State
                </dt>
                <dd className="mt-1 text-sm text-slate-900">
                  {user.profile.state_province || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Country
                </dt>
                <dd className="mt-1 text-sm text-slate-900">
                  {user.profile.country_of_origin || "—"}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Address
                </dt>
                <dd className="mt-1 text-sm text-slate-900">
                  {[user.profile.address_line1, user.profile.address_line2]
                    .filter(Boolean)
                    .join(", ") || "—"}
                </dd>
              </div>
              {user.profile.bio && (
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Bio
                  </dt>
                  <dd className="mt-1 text-sm text-slate-900">{user.profile.bio}</dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
