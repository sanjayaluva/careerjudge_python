import { Card, CardContent, CardDescription, CardHeader, CardTitle, Badge } from "@/components/ui";
import { PERMISSION_CATALOG } from "@/api/roles";

export default function PermissionsPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Permissions catalog</CardTitle>
          <CardDescription>
            All module/action combinations known to the system. Read-only view.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {PERMISSION_CATALOG.map((entry) => (
              <div
                key={entry.module}
                className="rounded-md border border-slate-200 bg-slate-50 p-4"
              >
                <div className="mb-2 flex items-center justify-between">
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
      </Card>
    </div>
  );
}
