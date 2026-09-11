import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  PageCard,
} from "@/components/ui";
import { updateMe } from "@/api/me";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/auth";
import { ROLE_LABELS } from "@/lib/constants";
import { COMMON_FIELDS, getRoleSpecificFields, type ProfileFieldConfig } from "@/lib/profileFields";
import type { UpdateMePayload } from "@/api/types";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const basicSchema = z.object({
  full_name: z.string().min(1, "Full name is required").max(255),
  phone: z.string().max(20).optional().or(z.literal("")),
});

// Build a dynamic schema from the field configs
function buildProfileSchema(fields: ProfileFieldConfig[]) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const f of fields) {
    if (f.type === "textarea") {
      shape[f.name] = z
        .string()
        .max(f.max_length ?? 1000)
        .optional()
        .or(z.literal(""));
    } else {
      shape[f.name] = z
        .string()
        .max(f.max_length ?? 255)
        .optional()
        .or(z.literal(""));
    }
  }
  return z.object(shape);
}

type BasicValues = z.infer<typeof basicSchema>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ProfileValues = Record<string, any>;

// ---------------------------------------------------------------------------
// Profile Page
// ---------------------------------------------------------------------------

export default function ProfilePage() {
  const { me, isLoadingMe, meError, refresh } = useAuth();
  const setUser = useAuthStore((s) => s.setUser);

  const [serverError, setServerError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const basicForm = useForm<BasicValues>({
    resolver: zodResolver(basicSchema),
    defaultValues: { full_name: "", phone: "" },
  });

  const roleFields = getRoleSpecificFields(me?.role ?? null);
  const profileSchema = buildProfileSchema([...COMMON_FIELDS, ...roleFields]);
  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {},
  });

  // Sync form values when /me/ resolves.
  useEffect(() => {
    if (!me) return;
    basicForm.reset({
      full_name: me.full_name,
      phone: me.phone,
    });

    const p = me.profile;
    const defaults: Record<string, string> = {};
    for (const f of [...COMMON_FIELDS, ...roleFields]) {
      const val = p?.[f.name];
      defaults[f.name] = val === null || val === undefined ? "" : String(val);
    }
    profileForm.reset(defaults);
  }, [me, roleFields, basicForm, profileForm]);

  const onBasicSubmit = async (values: BasicValues) => {
    setServerError(null);
    try {
      const payload: UpdateMePayload = {
        full_name: values.full_name,
        phone: values.phone ?? "",
      };
      const updated = await updateMe(payload);
      setUser({
        id: updated.id,
        email: updated.email,
        full_name: updated.full_name,
        role: updated.role,
        is_email_verified: updated.is_email_verified,
        is_superuser: me?.is_superuser ?? false,
        is_staff: me?.is_staff ?? false,
      });
      setSavedAt(new Date().toLocaleTimeString());
      refresh();
    } catch (err) {
      setServerError(extractApiError(err));
    }
  };

  const onProfileSubmit = async (values: ProfileValues) => {
    setServerError(null);
    try {
      const payload: UpdateMePayload = {
        profile: values as Record<string, string>,
      };
      await updateMe(payload);
      setSavedAt(new Date().toLocaleTimeString());
      refresh();
    } catch (err) {
      setServerError(extractApiError(err));
    }
  };

  if (isLoadingMe && !me) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (meError && !me) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load your profile. {extractApiError(meError)}</AlertDescription>
      </Alert>
    );
  }

  const allProfileFields = [...COMMON_FIELDS, ...roleFields];

  return (
    <PageCard>
      {/* Account overview section */}
      <CardHeader>
        <CardTitle>Account overview</CardTitle>
        <CardDescription>Your role and account status in CareerJudge.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Role</dt>
            <dd className="mt-1">
              {me?.role ? (
                <Badge variant="primary">{ROLE_LABELS[me.role] ?? me.role}</Badge>
              ) : (
                <Badge variant="outline">No role assigned</Badge>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Account status
            </dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {me?.is_active ? (
                <Badge variant="success">Active</Badge>
              ) : (
                <Badge variant="warning">Inactive</Badge>
              )}
              {me?.is_email_verified && <Badge variant="default">Email verified</Badge>}
              {me?.is_trial_user && <Badge variant="outline">Trial</Badge>}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Member since
            </dt>
            <dd className="mt-1 text-sm text-slate-900">
              {me?.created_at ? new Date(me.created_at).toLocaleDateString() : "—"}
            </dd>
          </div>
        </dl>
      </CardContent>

      {/* Divider between account overview and profile form */}
      <div className="border-t border-slate-200" />

      {/* Profile form section */}
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>
          Update your personal information and contact details.
          {roleFields.length > 0 && (
            <span className="ml-1 text-primary-600">
              Fields shown are specific to your role ({ROLE_LABELS[me?.role ?? "individual"]}).
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {serverError && (
          <Alert variant="error" className="mb-4">
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        {savedAt && (
          <Alert variant="success" className="mb-4">
            <AlertDescription>Saved at {savedAt}.</AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="basic">
          <TabsList>
            <TabsTrigger value="basic">Basic info</TabsTrigger>
            <TabsTrigger value="details">Profile details</TabsTrigger>
          </TabsList>

          <TabsContent value="basic">
            <form onSubmit={basicForm.handleSubmit(onBasicSubmit)} className="space-y-4" noValidate>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="full_name" required>
                    Full name
                  </Label>
                  <Input
                    id="full_name"
                    hasError={Boolean(basicForm.formState.errors.full_name)}
                    {...basicForm.register("full_name")}
                  />
                  {basicForm.formState.errors.full_name && (
                    <p className="mt-1 text-xs text-danger">
                      {basicForm.formState.errors.full_name.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="phone">Phone</Label>
                  <Input id="phone" type="tel" {...basicForm.register("phone")} />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" value={me?.email ?? ""} disabled />
                  <p className="mt-1 text-xs text-slate-500">
                    Email cannot be changed. Contact an admin if needed.
                  </p>
                </div>
              </div>
              <div className="flex justify-end">
                <Button type="submit" loading={basicForm.formState.isSubmitting}>
                  Save changes
                </Button>
              </div>
            </form>
          </TabsContent>

          <TabsContent value="details">
            <form
              onSubmit={profileForm.handleSubmit(onProfileSubmit)}
              className="space-y-4"
              noValidate
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {allProfileFields.map((field) => (
                  <div
                    key={field.name}
                    className={field.type === "textarea" ? "sm:col-span-2" : ""}
                  >
                    <Label htmlFor={`pf-${field.name}`} required={field.required}>
                      {field.label}
                    </Label>
                    {field.type === "select" ? (
                      <select
                        id={`pf-${field.name}`}
                        className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                        {...profileForm.register(field.name)}
                      >
                        {field.options?.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : field.type === "textarea" ? (
                      <textarea
                        id={`pf-${field.name}`}
                        rows={3}
                        className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                        {...profileForm.register(field.name)}
                      />
                    ) : (
                      <Input
                        id={`pf-${field.name}`}
                        type={field.type === "date" ? "date" : "text"}
                        {...profileForm.register(field.name)}
                      />
                    )}
                  </div>
                ))}
              </div>
              <div className="flex justify-end">
                <Button type="submit" loading={profileForm.formState.isSubmitting}>
                  Save profile details
                </Button>
              </div>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </PageCard>
  );
}
