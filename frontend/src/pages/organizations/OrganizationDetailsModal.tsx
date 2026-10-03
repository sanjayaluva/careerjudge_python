/**
 * Edit an organization's details — name, contact and address (Report 9
 * #34/#53). Open to CJ Admin and to the organization's own Corporate Exclusive
 * Admin / Channel Partner; its type, status and modules stay CJ Admin's.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  updateOrganization,
  type CreateOrganizationPayload,
  type Organization,
} from "@/api/organizations";
import { extractApiError } from "@/api/client";
import { Alert, AlertDescription, Button, Input, Label, Modal } from "@/components/ui";

const FIELDS: { key: keyof CreateOrganizationPayload; label: string; type?: string }[] = [
  { key: "name", label: "Organization name" },
  { key: "manager_name", label: "Manager (primary contact)" },
  { key: "tax_id", label: "PAN / TAN" },
  { key: "contact_email", label: "Contact email", type: "email" },
  { key: "contact_phone", label: "Contact phone" },
  { key: "website", label: "Website", type: "url" },
  { key: "address_line1", label: "Address" },
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "country", label: "Country" },
  { key: "postal_code", label: "Postal code" },
  { key: "description", label: "Description" },
];

export function OrganizationDetailsModal({
  org,
  onClose,
}: {
  org: Organization;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      FIELDS.map((f) => [f.key, String((org as unknown as Record<string, unknown>)[f.key] ?? "")]),
    ),
  );
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => updateOrganization(org.id, values as Partial<CreateOrganizationPayload>),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["organizations"] });
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal open onClose={onClose} title="Edit organization details" size="lg">
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form
        className="space-y-4"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (!values.name?.trim()) {
            setError("Organization name is required.");
            return;
          }
          setError(null);
          mutation.mutate();
        }}
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {FIELDS.map((f) => (
            <div key={f.key}>
              <Label htmlFor={`org-edit-${f.key}`} required={f.key === "name"}>
                {f.label}
              </Label>
              <Input
                id={`org-edit-${f.key}`}
                type={f.type ?? "text"}
                value={values[f.key] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 pt-4 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Save details
          </Button>
        </div>
      </form>
    </Modal>
  );
}
