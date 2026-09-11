import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, AlertDescription, Button, Input, Label } from "@/components/ui";
import { signup as apiSignup } from "@/api/auth";
import { extractApiError } from "@/api/client";
import { isEmail } from "@/lib/utils";

// Accounts audit gap (medium): self-signup no longer captures a password up
// front — the candidate sets one when they follow the emailed verification
// link (see VerifyEmailPage), i.e. only once email ownership is proven.
const schema = z.object({
  full_name: z.string().min(1, "Full name is required").max(255),
  email: z.string().min(1, "Email is required").refine(isEmail, "Enter a valid email address"),
});

type FormValues = z.infer<typeof schema>;

export default function SignupPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ email: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "" },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    setSubmitting(true);
    try {
      await apiSignup({
        email: values.email,
        full_name: values.full_name,
      });
      setSuccess({ email: values.email });
    } catch (err) {
      setServerError(extractApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <AuthLayout
        title="Check your email"
        description="We sent a verification link to your inbox."
        footer={
          <>
            Already verified?{" "}
            <Link to="/login" className="font-medium text-primary-600 hover:underline">
              Sign in
            </Link>
          </>
        }
      >
        <Alert variant="success" className="mb-4">
          <AlertDescription>
            Account created for <strong>{success.email}</strong>. Click the activation link in your
            email to verify it and set your password.
          </AlertDescription>
        </Alert>
        <div className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">
          <p className="mb-2 font-medium text-slate-700">Didn&apos;t get the email?</p>
          <Button variant="outline" size="sm" onClick={() => navigate("/login")}>
            Back to sign in
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Start your journey with CareerJudge."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary-600 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      {serverError && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div>
          <Label htmlFor="full_name" required>
            Full name
          </Label>
          <Input
            id="full_name"
            type="text"
            autoComplete="name"
            placeholder="Jane Doe"
            hasError={Boolean(errors.full_name)}
            aria-describedby={errors.full_name ? "full_name-error" : undefined}
            {...register("full_name")}
          />
          {errors.full_name && (
            <p id="full_name-error" className="mt-1 text-xs text-danger">
              {errors.full_name.message}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="email" required>
            Email
          </Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            hasError={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            {...register("email")}
          />
          {errors.email && (
            <p id="email-error" className="mt-1 text-xs text-danger">
              {errors.email.message}
            </p>
          )}
        </div>

        <p className="text-xs text-slate-500">
          You&apos;ll set your password after verifying your email — no need to choose one now.
        </p>

        <Button type="submit" className="w-full" loading={submitting}>
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
