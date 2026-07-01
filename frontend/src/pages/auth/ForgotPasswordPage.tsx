import { useState } from "react";
import { Link } from "react-router-dom";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, AlertDescription, Button, Input, Label } from "@/components/ui";
import { forgotPassword } from "@/api/auth";
import { extractApiError } from "@/api/client";
import { isEmail } from "@/lib/utils";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!isEmail(email)) {
      setError("Enter a valid email address.");
      return;
    }
    setSubmitting(true);
    try {
      // Backend always returns 200 to avoid leaking which emails exist.
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      // Even on error we show the same success message to avoid leaking.
      setSent(true);
      console.warn("Forgot-password error:", extractApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Forgot password"
      description="We'll send a reset link to your email."
      footer={
        <Link to="/login" className="font-medium text-primary-600 hover:underline">
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <Alert variant="success">
          <AlertDescription>
            If an account with <strong>{email}</strong> exists, you&apos;ll receive an email with a
            password reset link shortly.
          </AlertDescription>
        </Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {error && (
            <Alert variant="error">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div>
            <Label htmlFor="email" required>
              Email
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              hasError={Boolean(error)}
            />
          </div>
          <Button type="submit" className="w-full" loading={submitting}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
