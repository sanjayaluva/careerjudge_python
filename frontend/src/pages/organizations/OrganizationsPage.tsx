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
  createOrganization,
  deleteOrganization,
  listOrganizations,
  type CreateOrganizationPayload,
  type OrganizationListItem,
} from "@/api/organizations";
import { extractApiError } from "@/api/client";
import { Link } from "react-router-dom";

const ORGS_KEY = ["organizations"];

const TYPE_LABELS: Record<string, string> = {
  corporate: "Corporate",
  corp_exclusive: "Corporate Exclusive",
  channel_partner: "Channel Partner",
};

const STATUS_VARIANTS: Record<string, "success" | "warning" | "default"> = {
  active: "success",
  inactive: "warning",
  suspended: "default",
};

export default function OrganizationsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteOrg, setDeleteOrg] = useState<OrganizationListItem | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  // Debounce search
  useState(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  });

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: [...ORGS_KEY, page, debouncedSearch],
    queryFn: () =>
      listOrganizations({
        page,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteOrganization(id),
    onSuccess: () => {
      setDeleteOrg(null);
      void queryClient.invalidateQueries({ queryKey: ORGS_KEY });
    },
    onError: (err) => setDeleteError(extractApiError(err)),
  });

  const orgs = (data?.results ?? []).filter((o) => !typeFilter || o.type === typeFilter);
  const count = data?.count ?? 0;
  const hasNext = Boolean(data?.next);
  const hasPrev = Boolean(data?.previous);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Organizations</CardTitle>
              <CardDescription>
                {count > 0
                  ? `${count} organization${count === 1 ? "" : "s"} total`
                  : "Manage corporate entities"}
              </CardDescription>
            </div>
            <Button onClick={() => setCreateOpen(true)}>Create organization</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Input
              type="search"
              placeholder="Search by name, email, city..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="max-w-sm"
              aria-label="Search organizations"
            />
            <select
              aria-label="Filter by type"
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="">All types</option>
              <option value="corporate">Corporate</option>
              <option value="corp_exclusive">Corporate Exclusive</option>
              <option value="channel_partner">Channel Partner</option>
            </select>
            <Button variant="outline" size="md" onClick={() => refetch()}>
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
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead>Groups</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orgs.length === 0 ? (
                  <TableEmpty colSpan={7}>
                    {debouncedSearch || typeFilter
                      ? "No organizations match your filters."
                      : "No organizations yet. Create one to get started."}
                  </TableEmpty>
                ) : (
                  orgs.map((org) => (
                    <TableRow key={org.id}>
                      <TableCell className="font-medium text-slate-900">
                        <Link
                          to={`/organizations/${org.id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {org.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="default">{TYPE_LABELS[org.type] ?? org.type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANTS[org.status] ?? "default"}>
                          {org.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">{org.member_count}</TableCell>
                      <TableCell className="text-slate-500">{org.group_count}</TableCell>
                      <TableCell className="text-slate-500">
                        {new Date(org.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setDeleteOrg(org)}>
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

      <CreateOrganizationModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <DeleteOrganizationModal
        org={deleteOrg}
        error={deleteError}
        loading={deleteMutation.isPending}
        onClose={() => setDeleteOrg(null)}
        onConfirm={() => deleteOrg && deleteMutation.mutate(deleteOrg.id)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create Organization Modal
// ---------------------------------------------------------------------------

function CreateOrganizationModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState("corporate");
  const [contactEmail, setContactEmail] = useState("");
  const [description, setDescription] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: CreateOrganizationPayload) => createOrganization(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ORGS_KEY });
      resetForm();
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  function resetForm() {
    setName("");
    setType("corporate");
    setContactEmail("");
    setDescription("");
    setCity("");
    setCountry("");
    setError(null);
  }

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Organization name is required.");
      return;
    }
    mutation.mutate({
      name,
      type,
      contact_email: contactEmail,
      description,
      city,
      country,
    });
  };

  return (
    <Modal
      open={open}
      onClose={() => {
        resetForm();
        onClose();
      }}
      title="Create organization"
      description="Create a new corporate entity."
      size="lg"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="org-name" required>
              Organization name
            </Label>
            <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div>
            <Label htmlFor="org-type" required>
              Type
            </Label>
            <select
              id="org-type"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="corporate">Corporate</option>
              <option value="corp_exclusive">Corporate Exclusive</option>
              <option value="channel_partner">Channel Partner</option>
            </select>
          </div>
          <div>
            <Label htmlFor="org-email">Contact email</Label>
            <Input
              id="org-email"
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="org-city">City</Label>
            <Input id="org-city" value={city} onChange={(e) => setCity(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="org-country">Country</Label>
            <Input id="org-country" value={country} onChange={(e) => setCountry(e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="org-desc">Description</Label>
            <Input
              id="org-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Create organization
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Delete Organization Modal
// ---------------------------------------------------------------------------

function DeleteOrganizationModal({
  org,
  error,
  loading,
  onClose,
  onConfirm,
}: {
  org: OrganizationListItem | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!org) return null;
  return (
    <Modal
      open={Boolean(org)}
      onClose={onClose}
      title="Delete organization"
      description="This action cannot be undone."
      size="sm"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <p className="text-sm text-slate-600">
        Are you sure you want to delete <strong>{org.name}</strong>? All groups and member
        associations will be removed.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" loading={loading} onClick={onConfirm}>
          Delete organization
        </Button>
      </div>
    </Modal>
  );
}
