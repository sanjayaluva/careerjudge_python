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
  createSchedule,
  createWebsite,
  deleteAssignment,
  deleteGroup,
  deleteSchedule,
  getWebsite,
  listAssignments,
  listMembers,
  listSchedules,
  removeMember,
  rescheduleSchedule,
  retrieveOrganization,
  updateMember,
  updateWebsite,
} from "@/api/organizations";
import { listAssessments } from "@/api/assessment";
import { extractApiError } from "@/api/client";
import { BulkUploadModal } from "@/components/users/BulkUploadModal";
import { usePermissions } from "@/hooks/usePermissions";
import { ROLE_LABELS } from "@/lib/constants";
import { PortalLogo } from "@/pages/site/PortalLogo";

const ORG_KEY = (id: number) => ["organizations", id];

/** What the viewer may do on this page (Report 9 #10/#22): CJ Admin does
 * everything; an organization's own admin manages its members, schedules and
 * website; a Group Admin works inside his group only. */
function useOrgAccess() {
  const { isSuperAdmin, canPerform, role } = usePermissions();
  const canManage = canPerform("organizations", "change");
  const isGroupAdmin = role === "group_admin";
  return {
    isCJAdmin: isSuperAdmin,
    canManageMembers: canManage,
    canManageGroups: canManage && !isGroupAdmin,
    canSchedule: canManage,
    canCustomizeWebsite: canManage && !isGroupAdmin,
  };
}

export default function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const orgId = Number(id);

  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const access = useOrgAccess();

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
            {access.canManageGroups && (
              <Button size="sm" onClick={() => setGroupModalOpen(true)}>
                Add group
              </Button>
            )}
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
                  <GroupRow key={g.id} orgId={orgId} group={g} canDelete={access.canManageGroups} />
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
            {access.canManageMembers && (
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setBulkOpen(true)}>
                  Bulk upload
                </Button>
                <Button size="sm" onClick={() => setMemberModalOpen(true)}>
                  Add member
                </Button>
              </div>
            )}
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
                  <MemberRow
                    key={m.id}
                    orgId={orgId}
                    member={m}
                    groups={org.groups}
                    canEdit={access.canManageMembers}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Assigned content section (CJ_UC030): corporate individuals see only
          the assessments assigned to their organization. */}
      <AssignmentsCard orgId={orgId} canAssign={access.isCJAdmin} />

      {/* Schedule assessments for employees (CJ_UC053). */}
      <SchedulesCard orgId={orgId} groups={org.groups} canSchedule={access.canSchedule} />

      {/* Branded portal / website (CJ_UC054 + CJ_UC055). */}
      <WebsiteCard
        orgId={orgId}
        defaultName={org.name}
        canCreate={access.isCJAdmin}
        canCustomize={access.canCustomizeWebsite}
      />

      <BulkUploadModal
        open={bulkOpen}
        onClose={() => setBulkOpen(false)}
        organizationId={orgId}
        groups={org.groups}
        invalidateKeys={[[...ORG_KEY(orgId), "members"], [...ORG_KEY(orgId)]]}
      />

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
  canDelete,
}: {
  orgId: number;
  canDelete: boolean;
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
          {canDelete && (
            <Button
              variant="ghost"
              size="sm"
              className="text-danger hover:bg-danger-50"
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Delete
            </Button>
          )}
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
  canEdit,
}: {
  orgId: number;
  canEdit: boolean;
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
          disabled={!canEdit || updateMutation.isPending}
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
          disabled={!canEdit || updateMutation.isPending}
          className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
        />
      </TableCell>
      <TableCell className="text-slate-500">
        {new Date(member.joined_at).toLocaleDateString()}
      </TableCell>
      <TableCell>
        <div className="flex items-center justify-end gap-2">
          {error && <span className="text-xs text-danger">{error}</span>}
          {canEdit && (
            <Button
              variant="ghost"
              size="sm"
              className="text-danger hover:bg-danger-50"
              loading={removeMutation.isPending}
              onClick={() => removeMutation.mutate()}
            >
              Remove
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Assigned content (CJ_UC030) — assign published assessments to the org
// ---------------------------------------------------------------------------

function AssignmentsCard({ orgId, canAssign }: { orgId: number; canAssign: boolean }) {
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
          {canAssign
            ? "Corporate individuals in this organization see only the assessments assigned here."
            : "The assessments CJ Admin has assigned to your organization. You can schedule these for your members."}
        </p>
        {error && (
          <Alert variant="error" className="mb-3">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {canAssign && (
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
        )}
        {assignments.length === 0 ? (
          <p className="py-2 text-center text-sm text-slate-500">No assessments assigned yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Assessment</TableHead>
                <TableHead>Assigned by</TableHead>
                {canAssign && <TableHead className="text-right">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {assignments.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium text-slate-900">
                    {titleFor(a.item_id)}
                  </TableCell>
                  <TableCell className="text-slate-500">{a.assigned_by_name || "—"}</TableCell>
                  {canAssign && (
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
                  )}
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
// Schedule assessments for employees (CJ_UC053)
// ---------------------------------------------------------------------------

function SchedulesCard({
  orgId,
  groups,
  canSchedule,
}: {
  orgId: number;
  groups: { id: number; name: string }[];
  canSchedule: boolean;
}) {
  const queryClient = useQueryClient();
  const [assessmentId, setAssessmentId] = useState("");
  const [when, setWhen] = useState("");
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [moving, setMoving] = useState<{ id: number; when: string } | null>(null);
  const KEY = [...ORG_KEY(orgId), "schedules"];

  const { data: schedules = [] } = useQuery({
    queryKey: KEY,
    queryFn: () => listSchedules(orgId),
    enabled: !Number.isNaN(orgId),
  });
  const { data: assessmentsPage } = useQuery({
    queryKey: ["assessments", "published", "for-assign"],
    queryFn: () => listAssessments({ status: "published" }),
  });
  // Only assessments CJ Admin assigned to this organization can be scheduled
  // (Report 9 #8).
  const { data: assignments = [] } = useQuery({
    queryKey: [...ORG_KEY(orgId), "assignments"],
    queryFn: () => listAssignments(orgId),
    enabled: !Number.isNaN(orgId),
  });
  const assignedIds = new Set(
    assignments.filter((a) => a.item_type === "assessment").map((a) => a.item_id),
  );
  const assessments = (assessmentsPage?.results ?? []).filter((a) => assignedIds.has(a.id));

  const rescheduleMutation = useMutation({
    mutationFn: (m: { id: number; when: string }) =>
      rescheduleSchedule(orgId, m.id, { scheduled_at: new Date(m.when).toISOString() }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEY });
      setMoving(null);
      setError(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createSchedule(orgId, {
        assessment: Number(assessmentId),
        scheduled_at: new Date(when).toISOString(),
        ...(groupId ? { group: Number(groupId) } : {}),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEY });
      setAssessmentId("");
      setWhen("");
      setGroupId("");
      setError(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => deleteSchedule(orgId, id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: KEY }),
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scheduled assessments</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-slate-500">
          Schedule an assessment for employees — the targeted members are notified.
        </p>
        {error && (
          <Alert variant="error" className="mb-3">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {canSchedule && assessments.length === 0 && (
          <p className="mb-3 text-sm text-slate-500">
            No assessments have been assigned to this organization yet, so none can be scheduled.
          </p>
        )}
        {canSchedule && (
          <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-4">
            <select
              className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={assessmentId}
              onChange={(e) => setAssessmentId(e.target.value)}
            >
              <option value="">Assessment…</option>
              {assessments.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
            <input
              type="datetime-local"
              className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={when}
              onChange={(e) => setWhen(e.target.value)}
            />
            <select
              className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
            >
              <option value="">All members</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={!assessmentId || !when || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              Schedule
            </Button>
          </div>
        )}
        {schedules.length === 0 ? (
          <p className="py-2 text-center text-sm text-slate-500">Nothing scheduled yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Assessment</TableHead>
                <TableHead>When</TableHead>
                <TableHead>Target</TableHead>
                {canSchedule && <TableHead className="text-right">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {schedules.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium text-slate-900">{s.assessment_title}</TableCell>
                  <TableCell className="text-slate-500">
                    {moving?.id === s.id ? (
                      <input
                        type="datetime-local"
                        aria-label="New date and time"
                        className="h-8 rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                        value={moving.when}
                        onChange={(e) => setMoving({ id: s.id, when: e.target.value })}
                      />
                    ) : (
                      new Date(s.scheduled_at).toLocaleString()
                    )}
                  </TableCell>
                  <TableCell className="text-slate-500">{s.group_name || "All members"}</TableCell>
                  {canSchedule && (
                    <TableCell className="text-right">
                      {moving?.id === s.id ? (
                        <>
                          <Button
                            size="sm"
                            disabled={!moving.when}
                            loading={rescheduleMutation.isPending}
                            onClick={() => rescheduleMutation.mutate(moving)}
                          >
                            Save
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setMoving(null)}>
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setMoving({ id: s.id, when: "" })}
                          >
                            Reschedule
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-danger hover:bg-danger-50"
                            loading={removeMutation.isPending}
                            onClick={() => removeMutation.mutate(s.id)}
                          >
                            Cancel schedule
                          </Button>
                        </>
                      )}
                    </TableCell>
                  )}
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
// Branded portal / website (CJ_UC054 customization + CJ_UC055 create)
// ---------------------------------------------------------------------------

const LOGO_ACCEPT = "image/png,image/jpeg,image/gif,image/webp";
const LOGO_MAX_BYTES = 2 * 1024 * 1024;

/** Report 9 #49: client-side check matching the server's (PNG/JPG/GIF/WebP, 2 MB). */
function logoFileError(file: File): string | null {
  if (!/\.(png|jpe?g|gif|webp)$/i.test(file.name)) return "Upload a PNG, JPG, GIF or WebP image.";
  if (file.size > LOGO_MAX_BYTES) return "The logo must be 2 MB or smaller.";
  return null;
}

function WebsiteCard({
  orgId,
  defaultName,
  canCreate,
  canCustomize,
}: {
  orgId: number;
  defaultName: string;
  canCreate: boolean;
  canCustomize: boolean;
}) {
  const queryClient = useQueryClient();
  const KEY = [...ORG_KEY(orgId), "website"];
  const [companyName, setCompanyName] = useState(defaultName);
  const [layout, setLayout] = useState("classic");
  const [color, setColor] = useState("#4f46e5");
  const [logoUrl, setLogoUrl] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [adminEmail, setAdminEmail] = useState("");
  const [creds, setCreds] = useState<{ email: string; temporary_password: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data: website } = useQuery({
    queryKey: KEY,
    queryFn: () => getWebsite(orgId),
    enabled: !Number.isNaN(orgId),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createWebsite(orgId, {
        company_name: companyName,
        layout,
        primary_color: color,
        ...(logoFile ? { logo: logoFile } : { logo_url: logoUrl }),
        ...(adminEmail ? { admin_email: adminEmail } : {}),
      }),
    onSuccess: (w) => {
      if (w.generated_credentials) setCreds(w.generated_credentials);
      void queryClient.invalidateQueries({ queryKey: KEY });
      setError(null);
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateWebsite>[1]) => updateWebsite(orgId, payload),
    onSuccess: (w) => {
      queryClient.setQueryData(KEY, w);
      setError(null);
      setSaved(true);
    },
    onError: (err) => {
      setSaved(false);
      setError(extractApiError(err));
    },
  });

  // Report 9 #48: the portal's full address, to share and demo.
  const link = website ? `${window.location.origin}/site/${website.slug}` : "";
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy the link — select it and copy it manually.");
    }
  };

  const uploadLogo = (file: File | undefined) => {
    if (!file) return;
    const problem = logoFileError(file);
    if (problem) {
      setError(problem);
      return;
    }
    updateMutation.mutate({ logo: file });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Corporate website</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="error" className="mb-3">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {creds && (
          <Alert variant="success" className="mb-3">
            <AlertDescription>
              Website created. Admin login (shown once): <strong>{creds.email}</strong> / temporary
              password <strong>{creds.temporary_password}</strong> — copy it now.
            </AlertDescription>
          </Alert>
        )}
        {website ? (
          <div className="space-y-4">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <Label htmlFor="w-link">Portal link</Label>
              <div className="mt-1 flex flex-col gap-2 sm:flex-row">
                <Input
                  id="w-link"
                  readOnly
                  value={link}
                  onFocus={(e) => e.target.select()}
                  className="bg-white"
                />
                <div className="flex shrink-0 gap-2">
                  <Button variant="outline" onClick={() => void copyLink()}>
                    {copied ? "Copied" : "Copy"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => window.open(link, "_blank", "noopener,noreferrer")}
                  >
                    Open
                  </Button>
                </div>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Employees open this link and sign in to take their assessments and training.
                {website.admin_email ? ` Portal admin: ${website.admin_email}.` : ""}
                {website.is_active ? "" : " The portal is currently switched off."}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <Label htmlFor="w-company">Company name</Label>
                <Input
                  key={`name-${website.company_name}`}
                  id="w-company"
                  defaultValue={website.company_name}
                  disabled={!canCustomize}
                  onBlur={(e) => {
                    const value = e.target.value.trim();
                    if (!value) {
                      e.target.value = website.company_name;
                      setError("Company name is required.");
                    } else if (value !== website.company_name) {
                      updateMutation.mutate({ company_name: value });
                    }
                  }}
                />
              </div>
              <div>
                <Label htmlFor="w-layout">Layout</Label>
                <select
                  id="w-layout"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                  value={website.layout}
                  disabled={!canCustomize}
                  onChange={(e) => updateMutation.mutate({ layout: e.target.value })}
                >
                  <option value="classic">Classic</option>
                  <option value="modern">Modern</option>
                  <option value="minimal">Minimal</option>
                </select>
              </div>
              <div>
                <Label htmlFor="w-color">Primary color</Label>
                <input
                  key={`color-${website.primary_color}`}
                  id="w-color"
                  type="color"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-1"
                  defaultValue={website.primary_color}
                  disabled={!canCustomize}
                  onBlur={(e) => {
                    if (e.target.value !== website.primary_color) {
                      updateMutation.mutate({ primary_color: e.target.value });
                    }
                  }}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="w-logo-file">Logo</Label>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <span className="flex h-14 min-w-[3.5rem] items-center justify-center rounded-md border border-slate-200 bg-white p-1">
                  <PortalLogo
                    src={website.logo_src}
                    name={website.company_name}
                    color={website.primary_color}
                    size={44}
                  />
                </span>
                {canCustomize && (
                  <>
                    <input
                      id="w-logo-file"
                      type="file"
                      accept={LOGO_ACCEPT}
                      className="max-w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-slate-200"
                      onChange={(e) => {
                        uploadLogo(e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                    {website.logo_src && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => updateMutation.mutate({ logo_url: "" })}
                      >
                        Remove logo
                      </Button>
                    )}
                  </>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">PNG, JPG, GIF or WebP, up to 2 MB.</p>
              {canCustomize && (
                <div className="mt-2 max-w-xl">
                  <Label htmlFor="w-logo">…or use a logo link</Label>
                  <Input
                    key={`logo-${website.logo_url}`}
                    id="w-logo"
                    defaultValue={website.logo_url}
                    onBlur={(e) => {
                      const value = e.target.value.trim();
                      if (value && value !== website.logo_url) {
                        updateMutation.mutate({ logo_url: value });
                      }
                    }}
                    placeholder="https://…/logo.png"
                  />
                </div>
              )}
            </div>

            {canCustomize && (
              <p className="text-xs text-slate-500" aria-live="polite">
                {updateMutation.isPending
                  ? "Saving…"
                  : saved
                    ? "Changes saved — open the portal link to see them."
                    : "Changes save as you make them."}
              </p>
            )}
          </div>
        ) : !canCreate ? (
          <p className="text-sm text-slate-500">
            No website has been set up for this organization yet. CJ Admin sets it up; you can then
            customize it here.
          </p>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">
              Create a branded portal for this corporate — its own web address, branding, and a
              generated admin login.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="w-name" required>
                  Company name
                </Label>
                <Input
                  id="w-name"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="w-admin">Admin email (optional)</Label>
                <Input
                  id="w-admin"
                  type="email"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  placeholder="auto-generated if blank"
                />
              </div>
              <div>
                <Label htmlFor="w-new-layout">Layout</Label>
                <select
                  id="w-new-layout"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                  value={layout}
                  onChange={(e) => setLayout(e.target.value)}
                >
                  <option value="classic">Classic</option>
                  <option value="modern">Modern</option>
                  <option value="minimal">Minimal</option>
                </select>
              </div>
              <div>
                <Label htmlFor="w-new-color">Primary color</Label>
                <input
                  id="w-new-color"
                  type="color"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-1"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="w-new-logo-file">Logo (optional)</Label>
                <input
                  id="w-new-logo-file"
                  type="file"
                  accept={LOGO_ACCEPT}
                  className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-slate-200"
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null;
                    const problem = file ? logoFileError(file) : null;
                    setError(problem);
                    setLogoFile(problem ? null : file);
                    if (problem) e.target.value = "";
                  }}
                />
              </div>
              <div>
                <Label htmlFor="w-new-logo">…or a logo link</Label>
                <Input
                  id="w-new-logo"
                  value={logoUrl}
                  disabled={Boolean(logoFile)}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://…/logo.png"
                />
              </div>
            </div>
            <Button
              disabled={!companyName.trim() || createMutation.isPending}
              loading={createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              Create website
            </Button>
          </div>
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
