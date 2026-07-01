import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, AlertDescription, Button, Input, Label } from "@/components/ui";
import { signup as apiSignup } from "@/api/auth";
import { extractApiError } from "@/api/client";
import { isEmail, isStrongPassword } from "@/lib/utils";

const schema = z
  .object({
    full_name: z.string().min(1, "Full name is required").max(255),
    email: z.string().min(1, "Email is required").refine(isEmail, "Enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .refine(isStrongPassword, "Password must contain a letter and a number"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
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
    defaultValues: { full_name: "", email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    setSubmitting(true);
    try {
      await apiSignup({
        email: values.email,
        password: values.password,
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
            email to complete registration.
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
              Use at least 8 characters with a letter and a number.
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

        <Button type="submit" className="w-full" loading={submitting}>
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
