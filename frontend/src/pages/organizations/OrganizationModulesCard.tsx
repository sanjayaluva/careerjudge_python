/**
 * Report 9 #96: CJ Admin chooses which modules an organization's admins and
 * members may use. Unticking a module hides it for them and the server
 * refuses it; with every module ticked the organization has full access.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { extractApiError } from "@/api/client";
import { type Organization, setOrganizationModules } from "@/api/organizations";
import { Button, Card, CardContent, CardHeader, CardTitle, useToast } from "@/components/ui";

const SWITCHABLE: { code: string; label: string }[] = [
  { code: "assessment", label: "Assessments" },
  { code: "career_profiling", label: "Career Profiling" },
  { code: "reporting", label: "Reports" },
  { code: "training", label: "Training" },
  { code: "counseling", label: "Counselling" },
];
const ALL = SWITCHABLE.map((m) => m.code);

export function OrganizationModulesCard({ org }: { org: Organization }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [selected, setSelected] = useState<string[]>(org.enabled_modules ?? ALL);

  useEffect(() => {
    setSelected(org.enabled_modules ?? ALL);
  }, [org.enabled_modules]);

  const save = useMutation({
    mutationFn: () =>
      setOrganizationModules(org.id, selected.length === ALL.length ? null : selected),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["organizations", org.id] });
      toast.success("Modules updated.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const toggle = (code: string) =>
    setSelected((cur) => (cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modules for this organization</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-slate-500">
          Choose the modules this organization&apos;s admins and members may use. Unticked modules
          are hidden from them.
        </p>
        <div className="mb-4 flex flex-wrap gap-4">
          {SWITCHABLE.map((m) => (
            <label key={m.code} className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={selected.includes(m.code)}
                onChange={() => toggle(m.code)}
                className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
              />
              {m.label}
            </label>
          ))}
        </div>
        {/* The server reads an empty list as "every module", so at least one
            module must stay ticked. */}
        {selected.length === 0 && (
          <p className="mb-3 text-sm text-amber-700" role="status">
            Tick at least one module — an organization cannot have every module switched off.
          </p>
        )}
        <Button
          size="sm"
          loading={save.isPending}
          disabled={selected.length === 0}
          onClick={() => save.mutate()}
        >
          Save modules
        </Button>
      </CardContent>
    </Card>
  );
}
