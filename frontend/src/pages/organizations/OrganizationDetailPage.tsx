import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Modal,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui";
import {
  addMember,
  createGroup,
  deleteGroup,
  listMembers,
  removeMember,
  retrieveOrganization,
  updateMember,
} from "@/api/organizations";
import { extractApiError } from "@/api/client";
import { ROLE_LABELS } from "@/lib/constants";

const ORG_KEY = (id: number) => ["organizations", id];

export default function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const orgId = Number(id);

  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [memberModalOpen, setMemberModalOpen] = useState(false);

  const {
    data: org,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ORG_KEY(orgId),
    queryFn: () => retrieveOrganization(orgId),
    enabled: !Number.isNaN(orgId),
  });

  const { data: members = [] } = useQuery({
    queryKey: [...ORG_KEY(orgId), "members"],
    queryFn: () => listMembers(orgId),
    enabled: !Number.isNaN(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !org) {
    return (
      <Alert variant="error">
        <AlertDescription>Failed to load organization. {extractApiError(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/organizations" className="text-sm text-primary-600 hover:underline">
          ← Back to organizations
        </Link>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{org.name}</h1>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge variant="default">{org.type}</Badge>
          <Badge variant={org.status === "active" ? "success" : "warning"}>{org.status}</Badge>
          <Badge variant="outline">{org.member_count} members</Badge>
          <Badge variant="outline">{org.group_count} groups</Badge>
        </div>
      </div>

      {/* Groups section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Groups</CardTitle>
            <Button size="sm" onClick={() => setGroupModalOpen(true)}>
              Add group
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {org.groups.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">No groups yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {org.groups.map((g) => (
                  <GroupRow key={g.id} orgId={orgId} group={g} />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Members section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Members</CardTitle>
            <Button size="sm" onClick={() => setMemberModalOpen(true)}>
              Add member
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {members.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">No members yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Group</TableHead>
                  <TableHead>Admin</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((m) => (
                  <MemberRow key={m.id} orgId={orgId} member={m} groups={org.groups} />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <CreateGroupModal
        orgId={orgId}
        open={groupModalOpen}
        onClose={() => setGroupModalOpen(false)}
      />
      <AddMemberModal
        orgId={orgId}
        open={memberModalOpen}
        onClose={() => setMemberModalOpen(false)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group row with delete
// ---------------------------------------------------------------------------

function GroupRow({
  orgId,
  group,
}: {
  orgId: number;
  group: { id: number; name: string; member_count: number; created_at: string };
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: () => deleteGroup(orgId, group.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <TableRow>
      <TableCell className="font-medium text-slate-900">{group.name}</TableCell>
      <TableCell className="text-slate-500">{group.member_count}</TableCell>
      <TableCell className="text-slate-500">
        {new Date(group.created_at).toLocaleDateString()}
      </TableCell>
      <TableCell>
        <div className="flex items-center justify-end gap-2">
          {error && <span className="text-xs text-danger">{error}</span>}
          <Button
            variant="ghost"
            size="sm"
            className="text-danger hover:bg-danger-50"
            loading={deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            Delete
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Member row with remove
// ---------------------------------------------------------------------------

function MemberRow({
  orgId,
  member,
  groups,
}: {
  orgId: number;
  member: {
    id: number;
    user: { id: number; email: string; full_name: string; role: string | null };
    group: number | null;
    is_admin: boolean;
    joined_at: string;
  };
  groups: { id: number; name: string }[];
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const removeMutation = useMutation({
    mutationFn: () => removeMember(orgId, member.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "members"] });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { group_id?: number | null; is_admin?: boolean }) =>
      updateMember(orgId, member.id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "members"] });
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <TableRow>
      <TableCell className="font-medium text-slate-900">{member.user.full_name || "—"}</TableCell>
      <TableCell>{member.user.email}</TableCell>
      <TableCell>
        {member.user.role ? (
          <Badge variant="default">
            {ROLE_LABELS[member.user.role as keyof typeof ROLE_LABELS] ?? member.user.role}
          </Badge>
        ) : (
          <Badge variant="outline">No role</Badge>
        )}
      </TableCell>
      <TableCell>
        <select
          className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={member.group ?? ""}
          onChange={(e) => {
            setError(null);
            updateMutation.mutate({
              group_id: e.target.value ? Number(e.target.value) : null,
            });
          }}
          disabled={updateMutation.isPending}
        >
          <option value="">No group</option>
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
      </TableCell>
      <TableCell>
        <input
          type="checkbox"
          checked={member.is_admin}
          onChange={(e) => {
            setError(null);
            updateMutation.mutate({ is_admin: e.target.checked });
          }}
          disabled={updateMutation.isPending}
          className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
        />
      </TableCell>
      <TableCell className="text-slate-500">
        {new Date(member.joined_at).toLocaleDateString()}
      </TableCell>
      <TableCell>
        <div className="flex items-center justify-end gap-2">
          {error && <span className="text-xs text-danger">{error}</span>}
          <Button
            variant="ghost"
            size="sm"
            className="text-danger hover:bg-danger-50"
            loading={removeMutation.isPending}
            onClick={() => removeMutation.mutate()}
          >
            Remove
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Create Group Modal
// ---------------------------------------------------------------------------

function CreateGroupModal({
  orgId,
  open,
  onClose,
}: {
  orgId: number;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createGroup(orgId, { name, description }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
      setName("");
      setDescription("");
      setError(null);
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add group"
      description="Create a new group within this organization."
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
          if (!name.trim()) {
            setError("Group name is required.");
            return;
          }
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="grp-name" required>
            Group name
          </Label>
          <Input id="grp-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
        <div>
          <Label htmlFor="grp-desc">Description</Label>
          <Input
            id="grp-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Create group
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Add Member Modal
// ---------------------------------------------------------------------------

function AddMemberModal({
  orgId,
  open,
  onClose,
}: {
  orgId: number;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => addMember(orgId, { user_email: email }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "members"] });
      setEmail("");
      setError(null);
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add member"
      description="Add an existing user to this organization by email."
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
          if (!email.trim()) {
            setError("Email is required.");
            return;
          }
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="mem-email" required>
            User email
          </Label>
          <Input
            id="mem-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            autoFocus
          />
          <p className="mt-1 text-xs text-slate-500">
            The user must already have a CareerJudge account.
          </p>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Add member
          </Button>
        </div>
      </form>
    </Modal>
  );
}
