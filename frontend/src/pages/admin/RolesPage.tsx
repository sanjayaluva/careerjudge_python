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
  Input,
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
import {
  assignPermission as apiAssignPermission,
  createCustomRole as apiCreateCustomRole,
  deleteCustomRole as apiDeleteCustomRole,
  listRoles,
  PERMISSION_CATALOG,
  removePermission as apiRemovePermission,
} from "@/api/roles";
import { extractApiError } from "@/api/client";
import { ROLE_LABELS } from "@/lib/constants";
import type { ModuleRight, Role } from "@/api/types";

const ROLES_KEY = ["admin", "roles"];

export default function RolesPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [permissionsRoleId, setPermissionsRoleId] = useState<number | null>(null);
  const [deleteRole, setDeleteRole] = useState<Role | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const {
    data: roles = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ROLES_KEY,
    queryFn: listRoles,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDeleteCustomRole(id),
    onSuccess: () => {
      setDeleteRole(null);
      void queryClient.invalidateQueries({ queryKey: ROLES_KEY });
    },
    onError: (err) => setDeleteError(extractApiError(err)),
  });

  return (
    <div className="space-y-6">
      <Card className="border-l-0 border-r-0 border-t-0">
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Roles & Permissions</CardTitle>
              <CardDescription>
                {roles.length} role{roles.length === 1 ? "" : "s"} total. System roles are frozen;
                custom roles can be modified.
              </CardDescription>
            </div>
            <Button onClick={() => setCreateOpen(true)}>Create custom role</Button>
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
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Base role</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.length === 0 ? (
                  <TableEmpty colSpan={6}>No roles found.</TableEmpty>
                ) : (
                  roles.map((r) => {
                    // Human-readable name: system roles use ROLE_LABELS, custom roles use name
                    const displayName =
                      r.is_system && r.name in ROLE_LABELS
                        ? ROLE_LABELS[r.name as keyof typeof ROLE_LABELS]
                        : r.name;
                    // Base role: system roles ARE the base, so show "—"
                    const baseRoleDisplay = r.is_system
                      ? "—"
                      : r.base_role_name
                        ? (ROLE_LABELS[r.base_role_name as keyof typeof ROLE_LABELS] ??
                          r.base_role_name)
                        : "None (fully custom)";
                    return (
                      <TableRow key={r.id}>
                        <TableCell className="font-medium text-slate-900">{displayName}</TableCell>
                        <TableCell>
                          {r.is_system ? (
                            <Badge variant="default">System (Frozen)</Badge>
                          ) : (
                            <Badge variant="primary">Custom</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-slate-500">{baseRoleDisplay}</TableCell>
                        <TableCell className="text-slate-500">
                          {r.effective_rights?.length ?? r.rights?.length ?? 0} permission
                          {(r.effective_rights?.length ?? r.rights?.length ?? 0) === 1 ? "" : "s"}
                        </TableCell>
                        <TableCell className="text-slate-500">{r.user_count}</TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            {r.is_system ? (
                              <span className="inline-flex items-center px-3 py-1.5 text-xs text-slate-400">
                                Immutable
                              </span>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setPermissionsRoleId(r.id)}
                              >
                                Permissions
                              </Button>
                            )}
                            {!r.is_system && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-danger hover:bg-danger-50"
                                onClick={() => {
                                  setDeleteError(null);
                                  setDeleteRole(r);
                                }}
                                disabled={r.user_count > 0}
                                title={
                                  r.user_count > 0
                                    ? "Reassign users before deleting"
                                    : "Delete role"
                                }
                              >
                                Delete
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          )}

          <div className="mt-4 flex justify-end">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      <CreateCustomRoleModal open={createOpen} onClose={() => setCreateOpen(false)} roles={roles} />
      <PermissionsModal roleId={permissionsRoleId} onClose={() => setPermissionsRoleId(null)} />
      <DeleteRoleModal
        role={deleteRole}
        error={deleteError}
        loading={deleteMutation.isPending}
        onClose={() => setDeleteRole(null)}
        onConfirm={() => deleteRole && deleteMutation.mutate(deleteRole.id)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create custom role modal — with base role + permission selector
// ---------------------------------------------------------------------------

interface CreateCustomRoleModalProps {
  open: boolean;
  onClose: () => void;
  roles: Role[];
}

function CreateCustomRoleModal({ open, onClose, roles }: CreateCustomRoleModalProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [baseRoleId, setBaseRoleId] = useState<number | "">("");
  const [selectedPerms, setSelectedPerms] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const systemRoles = roles.filter((r) => r.is_system);

  const togglePerm = (module: string, action: string) => {
    const key = `${module}.${action}`;
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const resetForm = () => {
    setName("");
    setDescription("");
    setBaseRoleId("");
    setSelectedPerms(new Set());
    setError(null);
  };

  const mutation = useMutation({
    mutationFn: () => {
      // The backend CreateCustomRoleSerializer only accepts name, description, base_role.
      // Custom permissions are added after creation via assign-permission endpoint.
      return apiCreateCustomRole({
        name,
        description,
        base_role: baseRoleId === "" ? null : baseRoleId,
      });
    },
    onSuccess: async (createdRole) => {
      // Add any selected custom permissions (not inherited from base_role)
      const inheritedKeys = new Set(
        (createdRole.effective_rights ?? []).map((r: ModuleRight) => `${r.module}.${r.action}`),
      );
      const customPerms = Array.from(selectedPerms).filter((k) => !inheritedKeys.has(k));
      for (const key of customPerms) {
        const [module, action] = key.split(".");
        try {
          await apiAssignPermission(createdRole.id, { module, action: action as never });
        } catch {
          // continue even if one fails
        }
      }
      void queryClient.invalidateQueries({ queryKey: ROLES_KEY });
      resetForm();
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Role name is required.");
      return;
    }
    mutation.mutate();
  };

  return (
    <Modal
      open={open}
      onClose={() => {
        resetForm();
        onClose();
      }}
      title="Create custom role"
      description="Custom roles inherit permissions from a base system role and can have additional custom permissions."
      size="xl"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="cr-name" required>
              Role name
            </Label>
            <Input
              id="cr-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Senior Reviewer"
              autoFocus
            />
            <p className="mt-1 text-xs text-slate-500">
              Must be unique. Cannot use a system role name.
            </p>
          </div>
          <div>
            <Label htmlFor="cr-base">Base role (optional)</Label>
            <select
              id="cr-base"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={baseRoleId}
              onChange={(e) => setBaseRoleId(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">No base role (start from scratch)</option>
              {systemRoles.map((r) => (
                <option key={r.id} value={r.id}>
                  {ROLE_LABELS[r.name as keyof typeof ROLE_LABELS] ?? r.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Base role permissions are inherited and cannot be removed.
            </p>
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="cr-desc">Description</Label>
            <Input
              id="cr-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this role for?"
            />
          </div>
        </div>

        <div>
          <Label>Custom permissions (optional)</Label>
          <p className="mb-2 text-xs text-slate-500">
            These can be added/removed later via the Permissions button on the roles table.
          </p>
          <div className="max-h-60 overflow-y-auto rounded-md border border-slate-200 p-3">
            <div className="space-y-3">
              {PERMISSION_CATALOG.map((cat) => (
                <div key={cat.module}>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                    {cat.label}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {cat.actions.map((action) => {
                      const key = `${cat.module}.${action}`;
                      const isSelected = selectedPerms.has(key);
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => togglePerm(cat.module, action)}
                          className={`rounded-md border px-2 py-1 text-xs font-medium transition-colors ${
                            isSelected
                              ? "border-primary-600 bg-primary-50 text-primary-700"
                              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                          }`}
                        >
                          {action}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
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
// Permissions modal — reusable permission selector for editing custom roles
// Uses fresh data from the roles query so toggles update immediately.
// ---------------------------------------------------------------------------

interface PermissionsModalProps {
  roleId: number | null;
  onClose: () => void;
}

function PermissionsModal({ roleId, onClose }: PermissionsModalProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  // Get fresh role data from the query cache — this ensures the modal
  // re-renders with updated permissions after each assign/remove mutation.
  const { data: roles = [] } = useQuery({
    queryKey: ROLES_KEY,
    queryFn: listRoles,
    enabled: roleId !== null,
  });
  const role = roles.find((r) => r.id === roleId) ?? null;

  const assignMutation = useMutation({
    mutationFn: (payload: { module: string; action: string }) =>
      apiAssignPermission(role!.id, {
        module: payload.module,
        action: payload.action as never,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ROLES_KEY });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const removeMutation = useMutation({
    mutationFn: (payload: { module: string; action: string }) =>
      apiRemovePermission(role!.id, {
        module: payload.module,
        action: payload.action as never,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ROLES_KEY });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  if (!role) return null;

  // Build a map of (module.action) → right for quick lookup
  const rightMap = new Map<string, ModuleRight>();
  for (const r of role.effective_rights ?? role.rights ?? []) {
    rightMap.set(`${r.module}.${r.action}`, r);
  }

  const togglePerm = (module: string, action: string) => {
    setError(null);
    const key = `${module}.${action}`;
    const existing = rightMap.get(key);
    if (existing) {
      if (existing.is_inherited) {
        setError("Cannot remove inherited permission (from base role).");
        return;
      }
      removeMutation.mutate({ module, action });
    } else {
      assignMutation.mutate({ module, action });
    }
  };

  return (
    <Modal
      open={Boolean(role)}
      onClose={onClose}
      title={`Permissions: ${role.name}`}
      description={
        role.base_role_name
          ? `Inherits from ${ROLE_LABELS[role.base_role_name as keyof typeof ROLE_LABELS] ?? role.base_role_name}. Inherited permissions cannot be removed.`
          : "Toggle permissions on/off. Changes apply immediately."
      }
      size="xl"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="max-h-[60vh] space-y-4 overflow-y-auto">
        {PERMISSION_CATALOG.map((cat) => (
          <div key={cat.module} className="rounded-md border border-slate-200 p-3">
            <p className="mb-2 text-sm font-semibold text-slate-900">{cat.label}</p>
            <div className="flex flex-wrap gap-2">
              {cat.actions.map((action) => {
                const key = `${cat.module}.${action}`;
                const right = rightMap.get(key);
                const isAssigned = Boolean(right);
                const isInherited = Boolean(right?.is_inherited);
                const isAssigning =
                  assignMutation.isPending &&
                  assignMutation.variables?.module === cat.module &&
                  assignMutation.variables?.action === action;
                const isRemoving =
                  removeMutation.isPending &&
                  removeMutation.variables?.module === cat.module &&
                  removeMutation.variables?.action === action;
                const isLoading = isAssigning || isRemoving;
                return (
                  <button
                    key={key}
                    type="button"
                    disabled={isInherited || isLoading}
                    onClick={() => togglePerm(cat.module, action)}
                    className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed ${
                      isAssigned
                        ? isInherited
                          ? "border-slate-300 bg-slate-100 text-slate-500"
                          : "border-primary-600 bg-primary-50 text-primary-700 hover:bg-primary-100"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                    title={
                      isInherited
                        ? "Inherited from base role — cannot remove"
                        : isAssigned
                          ? "Click to remove"
                          : "Click to add"
                    }
                  >
                    {isLoading ? "..." : action}
                    {isInherited && " (inherited)"}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex justify-end border-t border-slate-100 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Done
        </Button>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Delete role modal
// ---------------------------------------------------------------------------

interface DeleteRoleModalProps {
  role: Role | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

function DeleteRoleModal({ role, error, loading, onClose, onConfirm }: DeleteRoleModalProps) {
  if (!role) return null;
  return (
    <Modal
      open={Boolean(role)}
      onClose={onClose}
      title="Delete custom role"
      description="This action cannot be undone."
      size="sm"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <p className="text-sm text-slate-600">
        Are you sure you want to delete <strong>{role.name}</strong>?
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" loading={loading} onClick={onConfirm}>
          Delete role
        </Button>
      </div>
    </Modal>
  );
}
