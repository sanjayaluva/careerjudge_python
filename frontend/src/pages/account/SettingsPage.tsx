import { useState } from "react";

import {
  Alert,
  AlertDescription,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  PageCard,
} from "@/components/ui";
import { changePassword } from "@/api/me";
import { extractApiError } from "@/api/client";
import { isStrongPassword } from "@/lib/utils";

export default function SettingsPage() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{
    old?: string;
    new?: string;
    confirm?: string;
  }>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const validate = (): boolean => {
    const next: typeof errors = {};
    if (!oldPassword) next.old = "Current password is required.";
    if (!isStrongPassword(newPassword)) {
      next.new = "Password must be at least 8 characters with a letter and a number.";
    }
    if (newPassword !== confirm) next.confirm = "Passwords do not match.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setSuccess(false);
    if (!validate()) return;
    setSubmitting(true);
    try {
      await changePassword({ old_password: oldPassword, new_password: newPassword });
      setSuccess(true);
      setOldPassword("");
      setNewPassword("");
      setConfirm("");
    } catch (err) {
      setServerError(extractApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageCard>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
          <CardDescription>Update the password used to sign in.</CardDescription>
        </CardHeader>
        <CardContent>
          {serverError && (
            <Alert variant="error" className="mb-4">
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert variant="success" className="mb-4">
              <AlertDescription>Password updated successfully.</AlertDescription>
            </Alert>
          )}

          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div>
              <Label htmlFor="old_password" required>
                Current password
              </Label>
              <Input
                id="old_password"
                type="password"
                autoComplete="current-password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                hasError={Boolean(errors.old)}
              />
              {errors.old && <p className="mt-1 text-xs text-danger">{errors.old}</p>}
            </div>
            <div>
              <Label htmlFor="new_password" required>
                New password
              </Label>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                hasError={Boolean(errors.new)}
              />
              {errors.new && <p className="mt-1 text-xs text-danger">{errors.new}</p>}
            </div>
            <div>
              <Label htmlFor="confirm_password" required>
                Confirm new password
              </Label>
              <Input
                id="confirm_password"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                hasError={Boolean(errors.confirm)}
              />
              {errors.confirm && <p className="mt-1 text-xs text-danger">{errors.confirm}</p>}
            </div>
            <div className="flex justify-end">
              <Button type="submit" loading={submitting}>
                Update password
              </Button>
            </div>
          </form>
        </CardContent>
      </PageCard>

      <Card>
        <CardHeader>
          <CardTitle>Email preferences</CardTitle>
          <CardDescription>Manage which emails you receive (coming soon).</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">
            Email preference toggles will be available in a future release.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
