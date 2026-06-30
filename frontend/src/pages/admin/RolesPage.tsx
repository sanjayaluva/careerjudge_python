import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

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
  Label,
  Modal,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import { assignPermission, createRole, listRoles, PERMISSION_CATALOG } from "@/api/roles";
import { extractApiError } from "@/api/client";
import { ROLE_LABELS, ROLE_NAME_CHOICES, type RoleName } from "@/lib/constants";
import type { CreateRolePayload, Role } from "@/api/types";

const ROLES_KEY = ["admin", "roles"];

export default function RolesPage() {
  const { data: roles = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ROLES_KEY,
    queryFn: listRoles,
  });

  const [createOpen, setCreateOpen] = useState(false);
  const [permissionTarget, setPermissionTarget] = useState<Role | null>(null);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Roles & Permissions</CardTitle>
              <CardDescription>
                Roles group module-specific rights. Frozen roles accept additive grants only.
              </CardDescription>
            </div>
            <Button onClick={() => setCreateOpen(true)}>Create role</Button>
          </div>
        </CardHeader>
        <CardContent>
          {isError && (
            <Alert variant="error" className="mb-4">
              <AlertDescription>{extractApiError(error)}</AlertDescription>
            </Alert>
          )}
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead>Rights</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.length === 0 ? (
                  <TableEmpty colSpan={6}>No roles found.</TableEmpty>
                ) : (
                  roles.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium text-slate-900">
                        {ROLE_LABELS[r.name] ?? r.name}
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {r.description || "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="default">{r.user_count}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{r.rights.length} rights</Badge>
                      </TableCell>
                      <TableCell>
                        {r.is_frozen ? (
                          <Badge variant="warning">Frozen</Badge>
                        ) : (
                          <Badge variant="default">Mutable</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setPermissionTarget(r)}
                          >
                            Permissions
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
          <div className="mt-4 flex justify-end">
            <Button variant="outline" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      <CreateRoleModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <AssignPermissionModal role={permissionTarget} onClose={() => setPermissionTarget(null)} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create role modal
// ---------------------------------------------------------------------------

function CreateRoleModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState<RoleName>("individual");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: CreateRolePayload) => createRole(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ROLES_KEY });
      setName("individual");
      setDescription("");
      setError(null);
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Create role" size="sm">
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate({ name, description });
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="cr-name" required>
            Role name
          </Label>
          <select
            id="cr-name"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={name}
            onChange={(e) => setName(e.target.value as RoleName)}
          >
            {ROLE_NAME_CHOICES.map((n) => (
              <option key={n} value={n}>
                {ROLE_LABELS[n]}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">
            Role names are constrained to the predefined set above.
          </p>
        </div>
        <div>
          <Label htmlFor="cr-desc">Description</Label>
          <textarea
            id="cr-desc"
            rows={3}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Create role
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Assign permission modal
// ---------------------------------------------------------------------------

function AssignPermissionModal({
  role,
  onClose,
}: {
  role: Role | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [module, setModule] = useState(PERMISSION_CATALOG[0]!.module);
  const [action, setAction] = useState(PERMISSION_CATALOG[0]!.actions[0] ?? "view");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Reset on open.
  if (role && !module) {
    setModule(PERMISSION_CATALOG[0]!.module);
    setAction(PERMISSION_CATALOG[0]!.actions[0] ?? "view");
  }

  const mutation = useMutation({
    mutationFn: (payload: { module: string; action: string }) =>
      assignPermission(role!.id, payload as Parameters<typeof assignPermission>[1]),
    onSuccess: () => {
      setSuccess("Permission granted.");
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ROLES_KEY });
    },
    onError: (err) => {
      setError(extractApiError(err));
      setSuccess(null);
    },
  });

  if (!role) return null;

  const currentModuleEntry =
    PERMISSION_CATALOG.find((m) => m.module === module) ?? PERMISSION_CATALOG[0]!;

  return (
    <Modal
      open={Boolean(role)}
      onClose={onClose}
      title="Assign permission"
      description={ROLE_LABELS[role.name] ?? role.name}
      size="md"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert variant="success" className="mb-4">
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Existing rights */}
      <div className="mb-4">
        <p className="mb-2 text-sm font-medium text-slate-700">Existing rights</p>
        <div className="max-h-32 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 p-3">
          {role.rights.length === 0 ? (
            <p className="text-xs text-slate-500">No rights assigned yet.</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              {role.rights.map((r) => (
                <Badge key={r.id} variant="outline" className="text-xs">
                  {r.module}.{r.action}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          setSuccess(null);
          mutation.mutate({ module, action });
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="ap-module">Module</Label>
            <select
              id="ap-module"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={module}
              onChange={(e) => {
                const m = e.target.value;
                setModule(m);
                const entry = PERMISSION_CATALOG.find((p) => p.module === m);
                if (entry && entry.actions.length > 0) setAction(entry.actions[0]!);
              }}
            >
              {PERMISSION_CATALOG.map((m) => (
                <option key={m.module} value={m.module}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="ap-action">Action</Label>
            <select
              id="ap-action"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            >
              {currentModuleEntry.actions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Grant permission
          </Button>
        </div>
      </form>
    </Modal>
  );
}
