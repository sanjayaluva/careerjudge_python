import {
  Badge,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  PageCard,
} from "@/components/ui";
import { PERMISSION_CATALOG } from "@/api/roles";

export default function PermissionsPage() {
  return (
    <div className="space-y-6">
      <PageCard>
        <CardHeader>
          <CardTitle className="text-xl">Permissions catalog</CardTitle>
          <CardDescription className="mt-1">
            All module/action combinations known to the system. Read-only view.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {PERMISSION_CATALOG.map((entry) => (
              <div
                key={entry.module}
                className="rounded-lg border border-slate-200 bg-slate-50 p-4"
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">{entry.label}</h3>
                  <Badge variant="outline" className="text-xs">
                    {entry.module}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-1">
                  {entry.actions.map((a) => (
                    <Badge key={a} variant="default" className="text-xs">
                      {a}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </PageCard>
    </div>
  );
}
