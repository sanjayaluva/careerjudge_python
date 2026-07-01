import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
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
} from "@/components/ui";
import { updateMe } from "@/api/me";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/auth";
import { ROLE_LABELS } from "@/lib/constants";
import type { UpdateMePayload, UserProfile } from "@/api/types";

const basicSchema = z.object({
  full_name: z.string().min(1, "Full name is required").max(255),
  phone: z.string().max(20).optional().or(z.literal("")),
});

const profileSchema = z.object({
  gender: z.enum(["", "male", "female", "other", "prefer_not_to_say"]).optional(),
  mobile: z.string().max(20).optional().or(z.literal("")),
  date_of_birth: z.string().optional().or(z.literal("")),
  address_line1: z.string().max(255).optional().or(z.literal("")),
  address_line2: z.string().max(255).optional().or(z.literal("")),
  city: z.string().max(100).optional().or(z.literal("")),
  state: z.string().max(100).optional().or(z.literal("")),
  country: z.string().max(100).optional().or(z.literal("")),
  postal_code: z.string().max(20).optional().or(z.literal("")),
  bio: z.string().max(1000).optional().or(z.literal("")),
});

type BasicValues = z.infer<typeof basicSchema>;
type ProfileValues = z.infer<typeof profileSchema>;

export default function ProfilePage() {
  const { me, isLoadingMe, meError, refresh } = useAuth();
  const setUser = useAuthStore((s) => s.setUser);

  const [serverError, setServerError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const basicForm = useForm<BasicValues>({
    resolver: zodResolver(basicSchema),
    defaultValues: { full_name: "", phone: "" },
  });

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
    const p: UserProfile = me.profile ?? {
      gender: "",
      date_of_birth: null,
      mobile: "",
      avatar: null,
      address_line1: "",
      address_line2: "",
      city: "",
      state: "",
      country: "",
      postal_code: "",
      bio: "",
    };
    profileForm.reset({
      gender: p.gender || "",
      mobile: p.mobile,
      date_of_birth: p.date_of_birth ?? "",
      address_line1: p.address_line1,
      address_line2: p.address_line2,
      city: p.city,
      state: p.state,
      country: p.country,
      postal_code: p.postal_code,
      bio: p.bio,
    });
  }, [me, basicForm, profileForm]);

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
        profile: {
          gender: (values.gender as UserProfile["gender"]) || "",
          mobile: values.mobile ?? "",
          date_of_birth: values.date_of_birth || null,
          address_line1: values.address_line1 ?? "",
          address_line2: values.address_line2 ?? "",
          city: values.city ?? "",
          state: values.state ?? "",
          country: values.country ?? "",
          postal_code: values.postal_code ?? "",
          bio: values.bio ?? "",
        },
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

  return (
    <div className="space-y-6">
      {/* Role information card — shows the user's role and account status */}
      <Card>
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
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Update your personal information and contact details.</CardDescription>
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
              <form
                onSubmit={basicForm.handleSubmit(onBasicSubmit)}
                className="space-y-4"
                noValidate
              >
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
                  <div>
                    <Label htmlFor="gender">Gender</Label>
                    <select
                      id="gender"
                      className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                      {...profileForm.register("gender")}
                    >
                      <option value="">Prefer not to say</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                      <option value="prefer_not_to_say">Prefer not to say</option>
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="mobile">Mobile</Label>
                    <Input id="mobile" type="tel" {...profileForm.register("mobile")} />
                  </div>
                  <div>
                    <Label htmlFor="date_of_birth">Date of birth</Label>
                    <Input
                      id="date_of_birth"
                      type="date"
                      {...profileForm.register("date_of_birth")}
                    />
                  </div>
                  <div>
                    <Label htmlFor="city">City</Label>
                    <Input id="city" {...profileForm.register("city")} />
                  </div>
                  <div>
                    <Label htmlFor="state">State / Province</Label>
                    <Input id="state" {...profileForm.register("state")} />
                  </div>
                  <div>
                    <Label htmlFor="country">Country</Label>
                    <Input id="country" {...profileForm.register("country")} />
                  </div>
                  <div>
                    <Label htmlFor="postal_code">Postal code</Label>
                    <Input id="postal_code" {...profileForm.register("postal_code")} />
                  </div>
                  <div className="sm:col-span-2">
                    <Label htmlFor="address_line1">Address line 1</Label>
                    <Input id="address_line1" {...profileForm.register("address_line1")} />
                  </div>
                  <div className="sm:col-span-2">
                    <Label htmlFor="address_line2">Address line 2</Label>
                    <Input id="address_line2" {...profileForm.register("address_line2")} />
                  </div>
                  <div className="sm:col-span-2">
                    <Label htmlFor="bio">Bio</Label>
                    <textarea
                      id="bio"
                      rows={4}
                      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                      {...profileForm.register("bio")}
                    />
                  </div>
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
      </Card>
    </div>
  );
}
