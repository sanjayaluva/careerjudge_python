import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, AlertDescription, Button, Input, Label } from "@/components/ui";
import { login as apiLogin } from "@/api/auth";
import { extractApiError } from "@/api/client";
import { getPublicSite } from "@/api/organizations";
import { PortalLogo, textOn } from "@/pages/site/PortalLogo";
import { useAuthStore } from "@/stores/auth";
import { isEmail } from "@/lib/utils";

const schema = z.object({
  email: z.string().min(1, "Email is required").refine(isEmail, "Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const login = useAuthStore((s) => s.login);

  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const sessionExpired = searchParams.get("reason") === "session_expired";
  const from = searchParams.get("from");
  // Report 9 #48/#51: arriving from a corporate portal (/site/<slug>) — show
  // the company's logo and name on the login card.
  const siteSlug = searchParams.get("site");
  const { data: site } = useQuery({
    queryKey: ["public-site", siteSlug],
    queryFn: () => getPublicSite(siteSlug as string),
    enabled: Boolean(siteSlug),
    retry: false,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    setSubmitting(true);
    try {
      const response = await apiLogin({
        email: values.email,
        password: values.password,
      });
      // Clear ALL cached queries from any previous session — prevents
      // the dashboard from showing the old user's data after login.
      queryClient.clear();
      login(response);
      navigate(from && from.startsWith("/") ? from : "/dashboard", { replace: true });
    } catch (err) {
      setServerError(extractApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title={site ? `Sign in to ${site.company_name}` : "Welcome back"}
      description={
        site
          ? "Use the account your organization gave you."
          : "Sign in to your CareerJudge account."
      }
      footer={
        site ? (
          <Link
            to={`/site/${encodeURIComponent(site.slug)}`}
            className="font-medium text-primary-600 hover:underline"
          >
            Back to the {site.company_name} portal
          </Link>
        ) : (
          <>
            Don&apos;t have an account?{" "}
            <Link to="/signup" className="font-medium text-primary-600 hover:underline">
              Sign up
            </Link>
          </>
        )
      }
    >
      {site && (
        <div
          className="mb-6 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4"
          style={{ borderTopColor: site.primary_color, borderTopWidth: 4 }}
          data-testid="portal-brand"
        >
          <PortalLogo src={site.logo_url} name={site.company_name} color={site.primary_color} />
          <span className="font-semibold text-slate-900">{site.company_name}</span>
        </div>
      )}

      {sessionExpired && (
        <Alert variant="warning" className="mb-4">
          <AlertDescription>
            Your session expired. Please sign in again to continue.
          </AlertDescription>
        </Alert>
      )}

      {serverError && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
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
            <p id="email-error" className="mt-1.5 text-xs text-danger-600">
              {errors.email.message}
            </p>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between gap-3">
            <Label htmlFor="password" required>
              Password
            </Label>
            <Link
              to="/forgot-password"
              className="mb-1.5 rounded text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            hasError={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
            {...register("password")}
          />
          {errors.password && (
            <p id="password-error" className="mt-1.5 text-xs text-danger-600">
              {errors.password.message}
            </p>
          )}
        </div>

        <Button
          type="submit"
          className="w-full"
          loading={submitting}
          style={
            site
              ? { backgroundColor: site.primary_color, color: textOn(site.primary_color) }
              : undefined
          }
        >
          Sign in
        </Button>
      </form>
    </AuthLayout>
  );
}
