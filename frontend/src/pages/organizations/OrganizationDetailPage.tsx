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
  createAssignment,
  createGroup,
  deleteAssignment,
  deleteGroup,
  listAssignments,
  listMembers,
  removeMember,
  retrieveOrganization,
  updateMember,
} from "@/api/organizations";
import { listAssessments } from "@/api/assessment";
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
    <div className="space-y-6 p-6">
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
                  <TableHead>Region / Division</TableHead>
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
                  <TableHead>Employee ID</TableHead>
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

      {/* Assigned content section (CJ_UC030): corporate individuals see only
          the assessments assigned to their organization. */}
      <AssignmentsCard orgId={orgId} />

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
  group: {
    id: number;
    name: string;
    region_division?: string;
    member_count: number;
    created_at: string;
  };
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
      <TableCell className="text-slate-500">{group.region_division || "—"}</TableCell>
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
    employee_id?: string;
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
      <TableCell className="text-slate-500">{member.employee_id || "—"}</TableCell>
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
// Assigned content (CJ_UC030) — assign published assessments to the org
// ---------------------------------------------------------------------------

function AssignmentsCard({ orgId }: { orgId: number }) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<string | null>(null);
  const ASSIGN_KEY = [...ORG_KEY(orgId), "assignments"];

  const { data: assignments = [] } = useQuery({
    queryKey: ASSIGN_KEY,
    queryFn: () => listAssignments(orgId),
    enabled: !Number.isNaN(orgId),
  });

  const { data: assessmentsPage } = useQuery({
    queryKey: ["assessments", "published", "for-assign"],
    queryFn: () => listAssessments({ status: "published" }),
  });
  const assessments = assessmentsPage?.results ?? [];
  const titleFor = (id: number) => assessments.find((a) => a.id === id)?.title ?? `#${id}`;

  const assignMutation = useMutation({
    mutationFn: (assessmentId: number) =>
      createAssignment(orgId, { item_type: "assessment", item_id: assessmentId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ASSIGN_KEY });
      setSelected("");
      setError(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const removeMutation = useMutation({
    mutationFn: (assignmentId: number) => deleteAssignment(orgId, assignmentId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ASSIGN_KEY }),
    onError: (err) => setError(extractApiError(err)),
  });

  const assignedIds = new Set(
    assignments.filter((a) => a.item_type === "assessment").map((a) => a.item_id),
  );
  const available = assessments.filter((a) => !assignedIds.has(a.id));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assigned assessments</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-slate-500">
          Corporate individuals in this organization see only the assessments assigned here.
        </p>
        {error && (
          <Alert variant="error" className="mb-3">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="mb-4 flex items-center gap-2">
          <select
            className="h-10 flex-1 rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Select a published assessment…</option>
            {available.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            disabled={!selected || assignMutation.isPending}
            onClick={() => selected && assignMutation.mutate(Number(selected))}
          >
            Assign
          </Button>
        </div>
        {assignments.length === 0 ? (
          <p className="py-2 text-center text-sm text-slate-500">No assessments assigned yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Assessment</TableHead>
                <TableHead>Assigned by</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assignments.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium text-slate-900">
                    {titleFor(a.item_id)}
                  </TableCell>
                  <TableCell className="text-slate-500">{a.assigned_by_name || "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-danger hover:bg-danger-50"
                      loading={removeMutation.isPending}
                      onClick={() => removeMutation.mutate(a.id)}
                    >
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
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
  const [regionDivision, setRegionDivision] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createGroup(orgId, { name, region_division: regionDivision, description }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
      setName("");
      setRegionDivision("");
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
          <Label htmlFor="grp-region">Region / Division</Label>
          <Input
            id="grp-region"
            value={regionDivision}
            onChange={(e) => setRegionDivision(e.target.value)}
            placeholder="e.g. North Zone"
          />
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
  const [fullName, setFullName] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      addMember(orgId, {
        user_email: email,
        ...(fullName.trim() ? { full_name: fullName } : {}),
        ...(employeeId.trim() ? { employee_id: employeeId } : {}),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "members"] });
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
      setEmail("");
      setFullName("");
      setEmployeeId("");
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
      description="Add an existing user by email, or onboard a new corporate individual by also entering their name."
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
        </div>
        <div>
          <Label htmlFor="mem-name">Full name</Label>
          <Input
            id="mem-name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Leave blank to add an existing user"
          />
          <p className="mt-1 text-xs text-slate-500">
            Enter a name to onboard a NEW corporate individual (they'll get a signup email). Leave
            blank to add someone who already has an account.
          </p>
        </div>
        <div>
          <Label htmlFor="mem-empid">Employee ID</Label>
          <Input
            id="mem-empid"
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            placeholder="e.g. EMP001"
          />
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
