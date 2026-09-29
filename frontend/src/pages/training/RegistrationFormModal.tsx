/**
 * Course registration form (Doc 7 §3/§4/§6: "System displays a registration
 * form" before payment). Report 8 #13: clicking Register used to register
 * immediately. Fields are prefilled from the profile and all are mandatory
 * for registration, even where sign-up left them optional; the backend saves
 * them back to the profile and snapshots them on the registration.
 */
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button, Input, Label, Modal } from "@/components/ui";
import { getMe } from "@/api/me";

export const REGISTRATION_FIELDS = [
  { key: "first_name", label: "First name" },
  { key: "last_name", label: "Last name" },
  { key: "gender", label: "Gender" },
  { key: "mobile", label: "Mobile number" },
  { key: "state_province", label: "State / Province" },
  { key: "city", label: "City" },
  { key: "occupation", label: "Occupation" },
  { key: "highest_education", label: "Highest education" },
  { key: "work_experience", label: "Work experience (years, 0 if none)" },
  { key: "institution_name", label: "Institution / Organization name" },
  { key: "place_of_institution", label: "Place of Institution / Organization" },
] as const;

export type RegistrationForm = Record<(typeof REGISTRATION_FIELDS)[number]["key"], string>;

const GENDERS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

export function RegistrationFormModal({
  open,
  courseTitle,
  submitting,
  onClose,
  onSubmit,
}: {
  open: boolean;
  courseTitle: string;
  submitting: boolean;
  onClose: () => void;
  onSubmit: (form: RegistrationForm) => void;
}) {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: getMe, enabled: open });
  const [form, setForm] = useState<RegistrationForm>(
    () => Object.fromEntries(REGISTRATION_FIELDS.map((f) => [f.key, ""])) as RegistrationForm,
  );

  useEffect(() => {
    if (!open || !me?.profile) return;
    const p = me.profile as unknown as Record<string, string | null>;
    setForm(
      (prev) =>
        Object.fromEntries(
          REGISTRATION_FIELDS.map((f) => [f.key, prev[f.key] || (p[f.key] ?? "")]),
        ) as RegistrationForm,
    );
  }, [open, me]);

  const missing = REGISTRATION_FIELDS.filter((f) => !String(form[f.key] ?? "").trim());
  const set = (key: keyof RegistrationForm, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Registration form"
      description={`Register for “${courseTitle}”. All fields are required.`}
      size="lg"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (missing.length === 0) onSubmit(form);
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {REGISTRATION_FIELDS.map((f) => (
            <div key={f.key}>
              <Label htmlFor={`reg-${f.key}`} required>
                {f.label}
              </Label>
              {f.key === "gender" ? (
                <select
                  id={`reg-${f.key}`}
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                  value={form.gender}
                  onChange={(e) => set("gender", e.target.value)}
                  required
                >
                  <option value="">Select…</option>
                  {GENDERS.map((g) => (
                    <option key={g.value} value={g.value}>
                      {g.label}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  id={`reg-${f.key}`}
                  type={f.key === "work_experience" ? "number" : "text"}
                  min={f.key === "work_experience" ? 0 : undefined}
                  value={form[f.key]}
                  onChange={(e) => set(f.key, e.target.value)}
                  required
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={submitting} disabled={missing.length > 0}>
            Submit &amp; continue
          </Button>
        </div>
      </form>
    </Modal>
  );
}
