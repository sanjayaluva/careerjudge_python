import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, AlertDescription, Button, Input, Label } from "@/components/ui";
import { resendVerification, verifyEmail } from "@/api/auth";
import { extractApiError } from "@/api/client";
import { isEmail, isStrongPassword } from "@/lib/utils";

type Status = "form" | "success" | "error";

// Accounts audit gap (medium): a self-registered account no longer captures
// a password at signup — it's set here, once the candidate has proven they
// own the email by following this link. Admin-invited accounts (which
// already have a password) can skip straight to verifying.
const passwordSchema = z
  .object({
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .refine(isStrongPassword, "Needs a letter, a number, and a special character, and must not start with a number"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;

export default function VerifyEmailPage() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<Status>("form");
  const [message, setMessage] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [resendEmail, setResendEmail] = useState("");
  const [resendError, setResendError] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resending, setResending] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  const runVerify = async (password?: string) => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token was provided in the URL.");
      return;
    }
    setSubmitting(true);
    try {
      await verifyEmail(token, password);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setMessage(extractApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const onSetPassword = (values: PasswordFormValues) => void runVerify(values.password);
  const onSkip = () => void runVerify(undefined);

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
      {status === "form" && (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            You&apos;re verifying your email. Set a password now to finish setting up your account,
            or skip and set one later from the sign-in page.
          </p>
          <form onSubmit={handleSubmit(onSetPassword)} className="space-y-4" noValidate>
            <div>
              <Label htmlFor="password" required>
                Password
              </Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                placeholder="At least 8 characters"
                hasError={Boolean(errors.password)}
                aria-describedby={errors.password ? "password-error" : "password-hint"}
                {...register("password")}
              />
              {errors.password ? (
                <p id="password-error" className="mt-1 text-xs text-danger">
                  {errors.password.message}
                </p>
              ) : (
                <p id="password-hint" className="mt-1 text-xs text-slate-500">
                  Use 8+ characters with a letter, a number, and a special character. Don’t start with a number.
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="confirmPassword" required>
                Confirm password
              </Label>
              <Input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                placeholder="Re-enter your password"
                hasError={Boolean(errors.confirmPassword)}
                aria-describedby={errors.confirmPassword ? "confirmPassword-error" : undefined}
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p id="confirmPassword-error" className="mt-1 text-xs text-danger">
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Button type="submit" className="w-full" loading={submitting}>
                Set password &amp; verify
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                disabled={submitting}
                onClick={onSkip}
              >
                Skip — just verify my email
              </Button>
            </div>
          </form>
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
