import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

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
  assignRole as apiAssignRole,
  createUser as apiCreateUser,
  deleteUser as apiDeleteUser,
  listUsers,
  updateUser as apiUpdateUser,
} from "@/api/users";
import { listRoles } from "@/api/roles";
import { extractApiError } from "@/api/client";
import {
  ROLE_LABELS,
  ROLE_NAME_CHOICES,
  type RoleName,
} from "@/lib/constants";
import type {
  AdminCreateUserPayload,
  AdminUpdateUserPayload,
  Role,
  User,
} from "@/api/types";
import { formatDate } from "@/lib/utils";

const USERS_KEY = ["admin", "users"];

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<string>(""); // "" = all roles

  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [deleteUser, setDeleteUser] = useState<User | null>(null);
  const [assignTarget, setAssignTarget] = useState<User | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Debounce search input.
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [search]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: [...USERS_KEY, page, debouncedSearch, roleFilter],
    queryFn: () =>
      listUsers({
        page,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
      }),
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["admin", "roles"],
    queryFn: listRoles,
    staleTime: 5 * 60_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDeleteUser(id),
    onSuccess: () => {
      setDeleteUser(null);
      void queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
    onError: (err) => {
      setDeleteError(extractApiError(err));
    },
  });

  // Client-side role filter (backend doesn't filter by role yet — additive TODO)
  const users = useMemo(() => {
    const all = data?.results ?? [];
    if (!roleFilter) return all;
    return all.filter((u) => u.role === roleFilter);
  }, [data?.results, roleFilter]);

  const count = data?.count ?? 0;
  const hasNext = Boolean(data?.next);
  const hasPrev = Boolean(data?.previous);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Users</CardTitle>
              <CardDescription>
                {count > 0 ? `${count} user${count === 1 ? "" : "s"} total` : "Manage user accounts"}
              </CardDescription>
            </div>
            <Button onClick={() => setCreateOpen(true)}>Create user</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Input
              type="search"
              placeholder="Search by email or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
              aria-label="Search users"
            />
            <select
              aria-label="Filter by role"
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All roles</option>
              {ROLE_NAME_CHOICES.map((name) => (
                <option key={name} value={name}>
                  {ROLE_LABELS[name]}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="md"
              onClick={() => refetch()}
              aria-label="Refresh list"
            >
              Refresh
            </Button>
          </div>

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
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableEmpty colSpan={6}>
                    {debouncedSearch || roleFilter
                      ? "No users match your filters."
                      : "No users yet. Create one to get started."}
                  </TableEmpty>
                ) : (
                  users.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell className="font-medium text-slate-900">
                        <Link
                          to={`/admin/users/${u.id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {u.full_name || "—"}
                        </Link>
                      </TableCell>
                      <TableCell>{u.email}</TableCell>
                      <TableCell>
                        {u.role ? (
                          <Badge variant="primary">{ROLE_LABELS[u.role]}</Badge>
                        ) : (
                          <Badge variant="outline">No role</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {u.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="warning">Inactive</Badge>
                          )}
                          {u.is_email_verified && (
                            <Badge variant="default">Verified</Badge>
                          )}
                          {u.is_trial_user && <Badge variant="outline">Trial</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-500">{formatDate(u.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setAssignTarget(u)}
                          >
                            Role
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditUser(u)}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-danger hover:bg-danger-50"
                            onClick={() => {
                              setDeleteError(null);
                              setDeleteUser(u);
                            }}
                          >
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}

          {(hasPrev || hasNext) && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-slate-500">Page {page}</p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasPrev}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasNext}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <UserFormModal
        mode="create"
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        roles={roles}
      />
      <UserFormModal
        mode="edit"
        user={editUser}
        open={Boolean(editUser)}
        onClose={() => setEditUser(null)}
        roles={roles}
      />
      <AssignRoleModal user={assignTarget} onClose={() => setAssignTarget(null)} />
      <DeleteUserModal
        user={deleteUser}
        error={deleteError}
        loading={deleteMutation.isPending}
        onClose={() => setDeleteUser(null)}
        onConfirm={() => deleteUser && deleteMutation.mutate(deleteUser.id)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Unified User Form Modal — used for both create and edit
// Wide horizontal layout, 2-column grid, fits within viewport.
// ---------------------------------------------------------------------------

interface UserFormModalProps {
  mode: "create" | "edit";
  open: boolean;
  user?: User | null;
  onClose: () => void;
  roles: Role[];
}

function UserFormModal({ mode, open, user, onClose, roles }: UserFormModalProps) {
  const queryClient = useQueryClient();
  const isEdit = mode === "edit";

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState<number | "">("");
  const [isActive, setIsActive] = useState(true);
  const [isVerified, setIsVerified] = useState(false);
  const [isTrial, setIsTrial] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Load user data when editing
  useEffect(() => {
    if (isEdit && user) {
      setEmail(user.email);
      setFullName(user.full_name);
      setPhone(user.phone);
      const match = roles.find((r) => r.name === user.role);
      setRoleId(match?.id ?? "");
      setIsActive(user.is_active);
      setIsVerified(user.is_email_verified);
      setIsTrial(user.is_trial_user);
      setPassword("");
      setError(null);
      setSuccess(null);
    } else if (!isEdit) {
      // Reset form for create mode
      setEmail("");
      setFullName("");
      setPhone("");
      setPassword("");
      setRoleId("");
      setIsActive(true);
      setIsVerified(false);
      setIsTrial(false);
      setError(null);
      setSuccess(null);
    }
  }, [isEdit, user, roles, open]);

  const createMutation = useMutation({
    mutationFn: (payload: AdminCreateUserPayload) => apiCreateUser(payload),
    onSuccess: () => {
      setSuccess("User created successfully.");
      void queryClient.invalidateQueries({ queryKey: USERS_KEY });
      setTimeout(() => onClose(), 800);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: AdminUpdateUserPayload) => apiUpdateUser(user!.id, payload),
    onSuccess: () => {
      setSuccess("User updated successfully.");
      void queryClient.invalidateQueries({ queryKey: USERS_KEY });
      setTimeout(() => onClose(), 800);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (!fullName) {
      setError("Full name is required.");
      return;
    }
    if (roleId === "") {
      setError("Select a role.");
      return;
    }

    const payload = {
      email,
      full_name: fullName,
      phone,
      is_active: isActive,
      is_email_verified: isVerified,
      is_trial_user: isTrial,
      role: roleId as number,
    };

    if (isEdit) {
      // Only send password if provided
      updateMutation.mutate({
        ...payload,
        ...(password ? { password } : {}),
      });
    } else {
      createMutation.mutate(payload);
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit user" : "Create user"}
      description={isEdit ? user?.email : "Create a new account and assign a role."}
      size="lg"
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
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {/* 2-column grid for wider forms — fits within viewport */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="uf-name" required>
              Full name
            </Label>
            <Input
              id="uf-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <Label htmlFor="uf-email" required>
              Email
            </Label>
            <Input
              id="uf-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="uf-phone">Phone</Label>
            <Input
              id="uf-phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="uf-password">
              Password {isEdit && <span className="text-slate-400">(leave blank to keep current)</span>}
            </Label>
            <Input
              id="uf-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isEdit ? "••••••••" : "Set initial password"}
              autoComplete="new-password"
            />
            {!isEdit && (
              <p className="mt-1 text-xs text-slate-500">
                Leave blank to auto-generate and email the user.
              </p>
            )}
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="uf-role" required>
              Role
            </Label>
            <select
              id="uf-role"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={roleId}
              onChange={(e) => setRoleId(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">Select a role...</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {ROLE_LABELS[r.name]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 rounded-md border border-slate-200 bg-slate-50 p-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
            />
            Active
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isVerified}
              onChange={(e) => setIsVerified(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
            />
            Email verified
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isTrial}
              onChange={(e) => setIsTrial(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
            />
            Trial account
          </label>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isLoading}>
            {isEdit ? "Save changes" : "Create user"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Assign role modal
// ---------------------------------------------------------------------------

interface AssignRoleModalProps {
  user: User | null;
  onClose: () => void;
}

function AssignRoleModal({ user, onClose }: AssignRoleModalProps) {
  const queryClient = useQueryClient();
  const [roleName, setRoleName] = useState<RoleName>("individual");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setRoleName(user.role ?? "individual");
      setError(null);
    }
  }, [user]);

  const mutation = useMutation({
    mutationFn: (name: RoleName) => apiAssignRole(user!.id, { role_name: name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_KEY });
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  if (!user) return null;

  return (
    <Modal open={Boolean(user)} onClose={onClose} title="Assign role" description={user.email} size="sm">
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate(roleName);
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="ar-role">Role</Label>
          <select
            id="ar-role"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={roleName}
            onChange={(e) => setRoleName(e.target.value as RoleName)}
          >
            {ROLE_NAME_CHOICES.map((name) => (
              <option key={name} value={name}>
                {ROLE_LABELS[name]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Assign role
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Delete user modal
// ---------------------------------------------------------------------------

interface DeleteUserModalProps {
  user: User | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

function DeleteUserModal({ user, error, loading, onClose, onConfirm }: DeleteUserModalProps) {
  if (!user) return null;
  return (
    <Modal
      open={Boolean(user)}
      onClose={onClose}
      title="Delete user"
      description="This action cannot be undone."
      size="sm"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <p className="text-sm text-slate-600">
        Are you sure you want to delete <strong>{user.email}</strong>? Their data will be
        permanently removed.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" loading={loading} onClick={onConfirm}>
          Delete user
        </Button>
      </div>
    </Modal>
  );
}
