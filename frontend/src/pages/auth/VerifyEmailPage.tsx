import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, AlertDescription, Button, Input, Label, Spinner } from "@/components/ui";
import { resendVerification, verifyEmail } from "@/api/auth";
import { extractApiError } from "@/api/client";
import { isEmail } from "@/lib/utils";

type Status = "verifying" | "success" | "error";

export default function VerifyEmailPage() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<Status>("verifying");
  const [message, setMessage] = useState<string>("");
  const [resendEmail, setResendEmail] = useState("");
  const [resendError, setResendError] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!token) {
        if (!cancelled) {
          setStatus("error");
          setMessage("No verification token was provided in the URL.");
        }
        return;
      }
      try {
        await verifyEmail(token);
        if (!cancelled) setStatus("success");
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setMessage(extractApiError(err));
        }
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    setResendError(null);
    setResendSuccess(false);
    if (!isEmail(resendEmail)) {
      setResendError("Enter a valid email address.");
      return;
    }
    setResending(true);
    try {
      await resendVerification(resendEmail);
      setResendSuccess(true);
    } catch (err) {
      setResendError(extractApiError(err));
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthLayout
      title="Email verification"
      description="Confirming your email address."
      footer={
        <Link to="/login" className="font-medium text-primary-600 hover:underline">
          Back to sign in
        </Link>
      }
    >
      {status === "verifying" && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Spinner size="lg" />
          <p className="text-sm text-slate-500">Verifying your email...</p>
        </div>
      )}

      {status === "success" && (
        <Alert variant="success">
          <AlertDescription>
            Your email has been verified. You can now{" "}
            <Link to="/login" className="font-medium text-primary-700 hover:underline">
              sign in
            </Link>{" "}
            to your account.
          </AlertDescription>
        </Alert>
      )}

      {status === "error" && (
        <div className="space-y-4">
          <Alert variant="error">
            <AlertDescription>{message}</AlertDescription>
          </Alert>

          <div className="rounded-md border border-slate-200 bg-white p-4">
            <p className="mb-3 text-sm font-medium text-slate-700">Need a new verification link?</p>
            <form onSubmit={handleResend} className="space-y-3">
              <div>
                <Label htmlFor="resendEmail">Email</Label>
                <Input
                  id="resendEmail"
                  type="email"
                  placeholder="you@example.com"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  hasError={Boolean(resendError)}
                />
                {resendError && <p className="mt-1 text-xs text-danger">{resendError}</p>}
                {resendSuccess && (
                  <p className="mt-1 text-xs text-success-700">
                    If an account exists, a new link has been sent.
                  </p>
                )}
              </div>
              <Button type="submit" size="sm" loading={resending}>
                Resend verification
              </Button>
            </form>
          </div>
        </div>
      )}
    </AuthLayout>
  );
}
