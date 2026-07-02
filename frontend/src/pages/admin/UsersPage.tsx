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
import { extractApiError, apiClient } from "@/api/client";
import { ROLE_LABELS, ROLE_NAME_CHOICES, type RoleName } from "@/lib/constants";
import type { AdminCreateUserPayload, AdminUpdateUserPayload, Role, User } from "@/api/types";
import { formatDate } from "@/lib/utils";

const USERS_KEY = ["admin", "users"];

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<string>(""); // "" = all roles

  const [createOpen, setCreateOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
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
                {count > 0
                  ? `${count} user${count === 1 ? "" : "s"} total`
                  : "Manage user accounts"}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setBulkUploadOpen(true)}>
                Bulk upload
              </Button>
              <Button onClick={() => setCreateOpen(true)}>Create user</Button>
            </div>
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
            <Button variant="outline" size="md" onClick={() => refetch()} aria-label="Refresh list">
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
                          {u.is_email_verified && <Badge variant="default">Verified</Badge>}
                          {u.is_trial_user && <Badge variant="outline">Trial</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-500">{formatDate(u.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setAssignTarget(u)}>
                            Role
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setEditUser(u)}>
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
      <BulkUploadModal open={bulkUploadOpen} onClose={() => setBulkUploadOpen(false)} />
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
              Password{" "}
              {isEdit && <span className="text-slate-400">(leave blank to keep current)</span>}
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
                  {r.is_system ? (ROLE_LABELS[r.name as RoleName] ?? r.name) : r.name}
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
    <Modal
      open={Boolean(user)}
      onClose={onClose}
      title="Assign role"
      description={user.email}
      size="sm"
    >
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

// ---------------------------------------------------------------------------
// Bulk Upload Modal — CSV upload with template download + results display
// ---------------------------------------------------------------------------

interface BulkResult {
  created_count: number;
  skipped_count: number;
  error_count: number;
  created: { row: number; email: string; full_name: string }[];
  skipped: { row: number; email: string; reason: string }[];
  errors: { row: number; email: string; error: string }[];
}

function BulkUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkResult | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async (uploadedFile: File) => {
      const formData = new FormData();
      formData.append("file", uploadedFile);
      const resp = await apiClient.post("/accounts/users/bulk-upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return resp.data as { message: string; data: BulkResult };
    },
    onSuccess: (resp) => {
      setResult(resp.data);
      void queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const handleDownloadTemplate = async () => {
    try {
      const resp = await apiClient.get("/accounts/users/bulk-upload/template/", {
        responseType: "blob",
      });
      // Create a download link from the blob
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "careerjudge_bulk_users_template.csv");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(extractApiError(err));
    }
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!file) {
      setError("Please select a CSV file.");
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleClose = () => {
    setFile(null);
    setError(null);
    setResult(null);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Bulk upload users"
      description="Upload a CSV file to create multiple users at once."
      size="lg"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result ? (
        <div className="space-y-4">
          <Alert variant="success" className="mb-4">
            <AlertDescription>
              Upload complete: {result.created_count} created, {result.skipped_count} skipped,{" "}
              {result.error_count} errors.
            </AlertDescription>
          </Alert>

          {result.created.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-900">
                Created ({result.created_count})
              </p>
              <div className="max-h-32 overflow-y-auto rounded-md border border-slate-200">
                {result.created.map((c, i) => (
                  <div key={i} className="border-b border-slate-100 px-3 py-1.5 text-xs">
                    <span className="font-medium text-slate-900">{c.full_name}</span>
                    <span className="mx-2 text-slate-400">—</span>
                    <span className="text-slate-500">{c.email}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.skipped.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">
                Skipped ({result.skipped_count})
              </p>
              <div className="max-h-32 overflow-y-auto rounded-md border border-slate-200">
                {result.skipped.map((s, i) => (
                  <div key={i} className="border-b border-slate-100 px-3 py-1.5 text-xs">
                    <span className="text-slate-600">{s.email}</span>
                    <span className="ml-2 text-slate-400">— {s.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-danger">
                Errors ({result.error_count})
              </p>
              <div className="max-h-32 overflow-y-auto rounded-md border border-danger-200">
                {result.errors.map((er, i) => (
                  <div key={i} className="border-b border-danger-100 px-3 py-1.5 text-xs">
                    <span className="text-slate-600">
                      Row {er.row}: {er.email}
                    </span>
                    <span className="ml-2 text-danger">— {er.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end border-t border-slate-100 pt-4">
            <Button type="button" onClick={handleClose}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <p className="mb-2 text-sm font-medium text-slate-700">Instructions</p>
            <ol className="ml-4 list-decimal space-y-1 text-xs text-slate-600">
              <li>Download the CSV template using the button below</li>
              <li>Fill in user details (full_name and email are required)</li>
              <li>
                Optional columns: phone, role_name (e.g., individual, corp_admin, sme, reviewer)
              </li>
              <li>Upload the filled CSV file below</li>
              <li>Users will be created with a random password and signup email sent</li>
            </ol>
            <Button
              type="button"
              variant="link"
              size="sm"
              className="mt-2 p-0"
              onClick={handleDownloadTemplate}
            >
              Download CSV template
            </Button>
          </div>

          <div>
            <Label htmlFor="bulk-file">CSV file</Label>
            <input
              id="bulk-file"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-slate-500 file:mr-4 file:rounded-md file:border-0 file:bg-primary-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-700"
            />
            {file && (
              <p className="mt-1 text-xs text-slate-500">
                Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={uploadMutation.isPending} disabled={!file}>
              Upload & create users
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
