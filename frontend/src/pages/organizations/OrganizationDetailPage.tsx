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
  useToast,
} from "@/components/ui";
import {
  addMember,
  createGroup,
  createGroupAdmin,
  createSchedule,
  createWebsite,
  deleteGroup,
  deleteSchedule,
  getWebsite,
  listAssignments,
  listMembers,
  listSchedules,
  removeMember,
  rescheduleSchedule,
  retrieveOrganization,
  updateGroup,
  updateMember,
  updateWebsite,
  type Group,
  type OrganizationMember,
  type UpdateMemberPayload,
} from "@/api/organizations";
import { listAssessments } from "@/api/assessment";
import { extractApiError } from "@/api/client";
import { BulkUploadModal } from "@/components/users/BulkUploadModal";
import { usePermissions } from "@/hooks/usePermissions";
import { ROLE_LABELS } from "@/lib/constants";
import { PortalLogo } from "@/pages/site/PortalLogo";

import {
  CourseSchedulesCard,
  LicensedContentCard,
  LicensedCoursesCard,
  MemberCounsellingCard,
} from "./LicensedContentCards";

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
    isGroupAdmin,
    canManageMembers: canManage,
    // Report 9 #23: a Group Admin adds/edits/deletes the sub-groups inside
    // his own group (each group's ``can_manage`` says which ones).
    canManageGroups: canManage,
    // Report 9 #21/#37/#4: the organization's admin (or CJ Admin) defines
    // Group Admins and their report permission; a Group Admin does not.
    canSetUpGroupAdmins:
      canManage && (isSuperAdmin || role === "corp_admin" || role === "corp_exclusive"),
    canSchedule: canManage,
    canCustomizeWebsite: canManage && !isGroupAdmin,
  };
}

/** Ids of ``groupId`` and every group nested below it (Report 9 #23). */
function subtreeIds(groups: Group[], groupId: number): Set<number> {
  const ids = new Set([groupId]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const g of groups) {
      if (g.parent !== null && ids.has(g.parent) && !ids.has(g.id)) {
        ids.add(g.id);
        grew = true;
      }
    }
  }
  return ids;
}

export default function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const orgId = Number(id);

  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [groupAdminModalOpen, setGroupAdminModalOpen] = useState(false);
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
            {access.canManageGroups && (!access.isGroupAdmin || org.groups.length > 0) && (
              <Button
                size="sm"
                onClick={() => {
                  setEditingGroup(null);
                  setGroupModalOpen(true);
                }}
              >
                {access.isGroupAdmin ? "Add sub-group" : "Add group"}
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
                  <TableHead>Parent group</TableHead>
                  <TableHead>Region / Division</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {org.groups.map((g) => (
                  <GroupRow
                    key={g.id}
                    orgId={orgId}
                    group={g}
                    canChange={access.canManageGroups && g.can_manage}
                    onEdit={() => {
                      setEditingGroup(g);
                      setGroupModalOpen(true);
                    }}
                  />
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
                {access.canSetUpGroupAdmins && org.type !== "channel_partner" && (
                  <Button size="sm" variant="outline" onClick={() => setGroupAdminModalOpen(true)}>
                    Add Group Admin
                  </Button>
                )}
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
                  <TableHead>Group Admin</TableHead>
                  <TableHead>Members&apos; reports</TableHead>
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
                    canEditAdmin={access.canManageMembers && !access.isGroupAdmin}
                    canSetUpGroupAdmins={
                      access.canSetUpGroupAdmins && org.type !== "channel_partner"
                    }
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Licensed content (CJ_UC030; Report 9 #98/#100-#103): members and
          managers see only the assessments and courses licensed here. */}
      <LicensedContentCard orgId={orgId} canLicense={access.isCJAdmin} />

      {/* Report 9 #15/#28/#59: assign licensed courses to members. */}
      <LicensedCoursesCard orgId={orgId} members={members} canAct={access.canSchedule} />

      {/* Schedule assessments for employees (CJ_UC053). */}
      <SchedulesCard orgId={orgId} groups={org.groups} canSchedule={access.canSchedule} />

      {/* Report 9 #16/#29/#60: schedule licensed courses for members. */}
      <CourseSchedulesCard orgId={orgId} groups={org.groups} canSchedule={access.canSchedule} />

      {/* Report 9 #18/#19/#30/#31/#61: counselling booked for members. */}
      <MemberCounsellingCard orgId={orgId} members={members} canAct={access.canSchedule} />

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

      <GroupModal
        key={editingGroup ? `edit-${editingGroup.id}` : "new"}
        orgId={orgId}
        open={groupModalOpen}
        group={editingGroup}
        groups={org.groups}
        requireParent={access.isGroupAdmin}
        onClose={() => {
          setGroupModalOpen(false);
          setEditingGroup(null);
        }}
      />
      <AddMemberModal
        orgId={orgId}
        open={memberModalOpen}
        onClose={() => setMemberModalOpen(false)}
      />
      <AddGroupAdminModal
        orgId={orgId}
        open={groupAdminModalOpen}
        groups={org.groups}
        onClose={() => setGroupAdminModalOpen(false)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group row with edit / delete
// ---------------------------------------------------------------------------

function GroupRow({
  orgId,
  group,
  canChange,
  onEdit,
}: {
  orgId: number;
  group: Group;
  canChange: boolean;
  onEdit: () => void;
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
      <TableCell className="text-slate-500">{group.parent_name || "—"}</TableCell>
      <TableCell className="text-slate-500">{group.region_division || "—"}</TableCell>
      <TableCell className="text-slate-500">{group.member_count}</TableCell>
      <TableCell className="text-slate-500">
        {new Date(group.created_at).toLocaleDateString()}
      </TableCell>
      <TableCell>
        <div className="flex items-center justify-end gap-2">
          {error && <span className="text-xs text-danger">{error}</span>}
          {canChange && (
            <>
              <Button variant="ghost" size="sm" onClick={onEdit}>
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger hover:bg-danger-50"
                loading={deleteMutation.isPending}
                onClick={() => {
                  if (
                    window.confirm(
                      `Delete group "${group.name}"? Its sub-groups are deleted too; members stay in the organization without a group.`,
                    )
                  ) {
                    deleteMutation.mutate();
                  }
                }}
              >
                Delete
              </Button>
            </>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Member row: group, admin, Group Admin + report permission, remove
// ---------------------------------------------------------------------------

function MemberRow({
  orgId,
  member,
  groups,
  canEdit,
  canEditAdmin,
  canSetUpGroupAdmins,
}: {
  orgId: number;
  member: OrganizationMember;
  groups: Group[];
  canEdit: boolean;
  canEditAdmin: boolean;
  canSetUpGroupAdmins: boolean;
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
    mutationFn: (payload: UpdateMemberPayload) => updateMember(orgId, member.id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "members"] });
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
    },
    onError: (err) => setError(extractApiError(err)),
  });

  const update = (payload: UpdateMemberPayload) => {
    setError(null);
    updateMutation.mutate(payload);
  };
  // Report 9 #37: only a corporate individual (or a Group Admin) can be
  // tagged/untagged as Group Admin of his group.
  const canToggleGroupAdmin =
    canSetUpGroupAdmins && (member.user.role === "individual" || member.is_group_admin);

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
          aria-label={`Group of ${member.user.email}`}
          className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={member.group ?? ""}
          onChange={(e) => update({ group_id: e.target.value ? Number(e.target.value) : null })}
          disabled={!canEdit || updateMutation.isPending}
        >
          <option value="">No group</option>
          {member.group !== null && !groups.some((g) => g.id === member.group) && (
            <option value={member.group}>{member.group_name ?? `#${member.group}`}</option>
          )}
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.parent_name ? `${g.parent_name} › ${g.name}` : g.name}
            </option>
          ))}
        </select>
      </TableCell>
      <TableCell>
        <input
          type="checkbox"
          aria-label={`Admin: ${member.user.email}`}
          checked={member.is_admin}
          onChange={(e) => update({ is_admin: e.target.checked })}
          disabled={!canEditAdmin || updateMutation.isPending}
          className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {member.is_group_admin && (
            <Badge variant="primary">
              Group Admin{member.group_name ? ` · ${member.group_name}` : ""}
            </Badge>
          )}
          {canToggleGroupAdmin && (
            <Button
              variant="ghost"
              size="sm"
              disabled={updateMutation.isPending || (!member.is_group_admin && !member.group)}
              title={
                !member.is_group_admin && !member.group
                  ? "Choose the member's group first."
                  : undefined
              }
              onClick={() => update({ is_group_admin: !member.is_group_admin })}
            >
              {member.is_group_admin ? "Remove Group Admin" : "Make Group Admin"}
            </Button>
          )}
          {!member.is_group_admin && !canToggleGroupAdmin && (
            <span className="text-slate-400">—</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        {member.is_group_admin ? (
          <label className="flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={member.can_view_member_reports}
              onChange={(e) => update({ can_view_member_reports: e.target.checked })}
              disabled={!canSetUpGroupAdmins || updateMutation.isPending}
              className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
            />
            Can view &amp; download
          </label>
        ) : (
          <span className="text-slate-400">—</span>
        )}
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
// Group Modal — add or edit a group / sub-group (Report 9 #23)
// ---------------------------------------------------------------------------

function GroupModal({
  orgId,
  open,
  group,
  groups,
  requireParent,
  onClose,
}: {
  orgId: number;
  open: boolean;
  /** The group being edited; null to add a new one. */
  group: Group | null;
  groups: Group[];
  /** A Group Admin only builds sub-groups inside his own group. */
  requireParent: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(group?.name ?? "");
  const [regionDivision, setRegionDivision] = useState(group?.region_division ?? "");
  const [description, setDescription] = useState(group?.description ?? "");
  const [parent, setParent] = useState(
    group?.parent ? String(group.parent) : requireParent && groups[0] ? String(groups[0].id) : "",
  );
  const [error, setError] = useState<string | null>(null);

  // A group cannot be placed under itself or one of its own sub-groups.
  const excluded = group ? subtreeIds(groups, group.id) : new Set<number>();
  const parentOptions = groups.filter((g) => !excluded.has(g.id));

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        name,
        region_division: regionDivision,
        description,
        parent: parent ? Number(parent) : null,
      };
      return group ? updateGroup(orgId, group.id, payload) : createGroup(orgId, payload);
    },
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

  const noun = requireParent ? "sub-group" : "group";
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={group ? `Edit ${noun}` : `Add ${noun}`}
      description={
        requireParent
          ? "Sub-groups are created within your own group."
          : group
            ? "Change the group's name, region/division or parent group."
            : "Create a new group within this organization. Choose a parent to make it a sub-group."
      }
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
          if (requireParent && !parent) {
            setError("Choose the group this sub-group belongs to.");
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
          <Label htmlFor="grp-parent" required={requireParent}>
            Parent group
          </Label>
          <select
            id="grp-parent"
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            value={parent}
            onChange={(e) => setParent(e.target.value)}
          >
            {!requireParent && <option value="">None (top-level group)</option>}
            {parentOptions.map((g) => (
              <option key={g.id} value={g.id}>
                {g.parent_name ? `${g.parent_name} › ${g.name}` : g.name}
              </option>
            ))}
          </select>
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
            {group ? "Save changes" : `Create ${noun}`}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Add Group Admin Modal (Report 9 #21; SRS p.18 "Group Admins by corporate
// Admin": Name, Email, Employee ID, Division/Region, Permissions)
// ---------------------------------------------------------------------------

function AddGroupAdminModal({
  orgId,
  open,
  groups,
  onClose,
}: {
  orgId: number;
  open: boolean;
  groups: Group[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [canViewReports, setCanViewReports] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedGroup = groups.find((g) => String(g.id) === groupId);

  const reset = () => {
    setFullName("");
    setEmail("");
    setEmployeeId("");
    setGroupId("");
    setCanViewReports(false);
    setError(null);
  };

  const mutation = useMutation({
    mutationFn: () =>
      createGroupAdmin(orgId, {
        full_name: fullName.trim(),
        email: email.trim(),
        employee_id: employeeId.trim(),
        group_id: Number(groupId),
        can_view_member_reports: canViewReports,
      }),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: [...ORG_KEY(orgId), "members"] });
      void queryClient.invalidateQueries({ queryKey: ORG_KEY(orgId) });
      if (created.invite_email_sent === false) {
        toast.warning(
          "Group Admin created, but the verification email could not be sent. Please try again later or contact CJ Admin.",
        );
      } else {
        toast.success("Group Admin created. A verification email has been sent.");
      }
      reset();
      onClose();
    },
    onError: (err) => setError(extractApiError(err)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add Group Admin"
      description="Create a Group Admin for one of this organization's groups. They receive an email to verify their account and set a password."
      size="sm"
    >
      {error && (
        <Alert variant="error" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {groups.length === 0 ? (
        <p className="text-sm text-slate-500">Add a group first — a Group Admin manages a group.</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            if (!fullName.trim() || !email.trim()) {
              setError("Name and official email are required.");
              return;
            }
            if (!groupId) {
              setError("Choose the group this Group Admin manages.");
              return;
            }
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="ga-name" required>
              Name
            </Label>
            <Input
              id="ga-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <Label htmlFor="ga-email" required>
              Official email
            </Label>
            <Input
              id="ga-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
            />
          </div>
          <div>
            <Label htmlFor="ga-empid">Employee ID</Label>
            <Input
              id="ga-empid"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              placeholder="e.g. EMP001"
            />
          </div>
          <div>
            <Label htmlFor="ga-group" required>
              Group
            </Label>
            <select
              id="ga-group"
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
            >
              <option value="">Select a group…</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.parent_name ? `${g.parent_name} › ${g.name}` : g.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Region / Division: {selectedGroup?.region_division || "—"}
            </p>
          </div>
          <fieldset>
            <legend className="mb-1 text-sm font-medium text-slate-700">Permissions</legend>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={canViewReports}
                onChange={(e) => setCanViewReports(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-600"
              />
              Can view &amp; download members&apos; reports
            </label>
            <p className="mt-1 text-xs text-slate-500">
              You can change this later from the member list.
            </p>
          </fieldset>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={mutation.isPending}>
              Create Group Admin
            </Button>
          </div>
        </form>
      )}
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
