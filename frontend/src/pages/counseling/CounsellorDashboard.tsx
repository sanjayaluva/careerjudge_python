/**
 * Counsellor Dashboard — manages timeslots, sessions, summaries, follow-ups.
 *
 * Tabs:
 * - TimeSlots: create/delete available timeslots (SRS §3.1)
 * - Sessions: list pending/confirmed sessions, confirm/cancel/complete (SRS §3.2)
 * - Summaries: fill post-session summary form + propose follow-up (SRS §3.3)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "@/components/ui";
import {
  cancelSession,
  completeSession,
  confirmSession,
  createTimeSlot,
  deleteTimeSlot,
  getSessionSummary,
  listCounsellorTimeslots,
  listSessions,
  proposeFollowup,
  updateTimeSlot,
  saveSessionSummary,
  type CounselingSession,
  type SessionSummary,
} from "@/api/counseling";
import { extractApiError } from "@/api/client";

export function CounsellorDashboard({ counsellorId }: { counsellorId: number }) {
  return (
    <Tabs defaultValue="sessions">
      <TabsList>
        <TabsTrigger value="sessions">Sessions</TabsTrigger>
        <TabsTrigger value="timeslots">Time Slots</TabsTrigger>
      </TabsList>

      <TabsContent value="sessions">
        <SessionsTab counsellorId={counsellorId} />
      </TabsContent>
      <TabsContent value="timeslots">
        <TimeSlotsTab counsellorId={counsellorId} />
      </TabsContent>
    </Tabs>
  );
}

// ---------------------------------------------------------------------------
// Sessions Tab — list + confirm/cancel/complete + summary + follow-up
// ---------------------------------------------------------------------------

function SessionsTab({ counsellorId: _cid }: { counsellorId: number }) {
  // We can't directly list sessions by counsellor from the API, so we
  // use the counsellor's session data. In practice the API returns all
  // sessions for the authenticated counsellor via the sessions endpoint.
  // For now, we'll use a query that lists all sessions (the backend
  // filters by the counsellor's profile automatically).
  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ["counseling", "sessions"],
    queryFn: () => listSessions(),
  });

  if (isLoading) return <Spinner />;
  const sessions = sessionsData ?? [];

  const pending = sessions.filter((s) => s.status === "pending");
  const confirmed = sessions.filter((s) => s.status === "confirmed");
  const completed = sessions.filter((s) => s.status === "completed");

  return (
    <div className="space-y-4">
      {/* Pending sessions — need confirmation */}
      {pending.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Pending Appointments ({pending.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Counselee</TableHead>
                  <TableHead>Topic</TableHead>
                  <TableHead>Scheduled</TableHead>
                  <TableHead>Fee</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pending.map((s) => (
                  <SessionRow key={s.id} session={s} showConfirm />
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Confirmed sessions — can complete */}
      {confirmed.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Confirmed Sessions ({confirmed.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Counselee</TableHead>
                  <TableHead>Topic</TableHead>
                  <TableHead>Scheduled</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {confirmed.map((s) => (
                  <SessionRow key={s.id} session={s} showComplete />
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Completed sessions — can add summary */}
      {completed.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Completed Sessions ({completed.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Counselee</TableHead>
                  <TableHead>Topic</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {completed.map((s) => (
                  <SessionRow key={s.id} session={s} showSummary />
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {sessions.length === 0 && (
        <p className="py-8 text-center text-sm text-slate-500">
          No sessions yet. Students will appear here after booking.
        </p>
      )}
    </div>
  );
}

function SessionRow({
  session,
  showConfirm,
  showComplete,
  showSummary,
}: {
  session: CounselingSession;
  showConfirm?: boolean;
  showComplete?: boolean;
  showSummary?: boolean;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [summaryOpen, setSummaryOpen] = useState(false);

  const confirmMut = useMutation({
    mutationFn: () => confirmSession(session.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "sessions"] });
      toast.success("Session confirmed.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const cancelMut = useMutation({
    mutationFn: () => cancelSession(session.id, "counsellor"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "sessions"] });
      toast.success("Session cancelled.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const completeMut = useMutation({
    mutationFn: () => completeSession(session.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "sessions"] });
      toast.success("Session completed. Fill in the summary.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <TableRow>
      <TableCell className="font-medium text-slate-900">
        {session.counselee_name ?? session.counselee_email}
      </TableCell>
      <TableCell className="text-slate-700">{session.topic}</TableCell>
      <TableCell className="text-slate-500">
        {session.timeslot_detail
          ? new Date(session.timeslot_detail.start_time).toLocaleString()
          : "—"}
      </TableCell>
      {showConfirm && <TableCell className="text-slate-500">${session.fee}</TableCell>}
      {showComplete && (
        <TableCell>
          <Badge variant="outline">{session.mode}</Badge>
          {session.mode === "online" && session.timeslot_detail && (
            <span className="ml-1 text-xs text-primary-600">Online</span>
          )}
        </TableCell>
      )}
      {showSummary && (
        <TableCell className="text-slate-500">
          {session.completed_at ? new Date(session.completed_at).toLocaleDateString() : "—"}
        </TableCell>
      )}
      <TableCell>
        <div className="flex gap-1">
          {showConfirm && (
            <>
              <Button size="sm" onClick={() => confirmMut.mutate()} loading={confirmMut.isPending}>
                Confirm
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => cancelMut.mutate()}
                loading={cancelMut.isPending}
                className="text-danger-600"
              >
                Cancel
              </Button>
            </>
          )}
          {showComplete && (
            <>
              <Button
                size="sm"
                onClick={() => completeMut.mutate()}
                loading={completeMut.isPending}
              >
                Complete
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => cancelMut.mutate()}
                loading={cancelMut.isPending}
                className="text-danger-600"
              >
                Cancel
              </Button>
            </>
          )}
          {showSummary && (
            <Button size="sm" variant="outline" onClick={() => setSummaryOpen(true)}>
              Summary + Follow-up
            </Button>
          )}
        </div>
      </TableCell>
      {summaryOpen && <SummaryModal sessionId={session.id} onClose={() => setSummaryOpen(false)} />}
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Summary Modal — post-session summary + follow-up proposal (SRS §3.3)
// ---------------------------------------------------------------------------

function SummaryModal({ sessionId, onClose }: { sessionId: number; onClose: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  // Report 3 §2.4 — the 6 summary fields.
  const [clientDetails, setClientDetails] = useState("");
  const [summary, setSummary] = useState("");
  const [provisionalDiagnosis, setProvisionalDiagnosis] = useState("");
  const [casePrognosis, setCasePrognosis] = useState("");
  const [sessionSmoothly, setSessionSmoothly] = useState<SessionSummary["session_smoothly"]>("");
  const [smoothlyReason, setSmoothlyReason] = useState("");
  const [followupRecommended, setFollowupRecommended] = useState(false);
  const [followupTime, setFollowupTime] = useState("");
  const [showFollowupForm, setShowFollowupForm] = useState(false);

  const { data: existingSummary } = useQuery({
    queryKey: ["counseling", "summary", sessionId],
    queryFn: () => getSessionSummary(sessionId),
  });

  // Load existing summary if available
  useState(() => {
    if (existingSummary) {
      setClientDetails(existingSummary.client_details ?? "");
      setSummary(existingSummary.summary);
      setProvisionalDiagnosis(existingSummary.provisional_diagnosis ?? "");
      setCasePrognosis(existingSummary.case_prognosis ?? "");
      setSessionSmoothly(existingSummary.session_smoothly ?? "");
      setSmoothlyReason(existingSummary.smoothly_reason ?? "");
      setFollowupRecommended(existingSummary.followup_recommended);
    }
  });

  const saveMut = useMutation({
    mutationFn: () =>
      saveSessionSummary(sessionId, {
        client_details: clientDetails,
        summary,
        provisional_diagnosis: provisionalDiagnosis,
        case_prognosis: casePrognosis,
        session_smoothly: sessionSmoothly,
        smoothly_reason: smoothlyReason,
        followup_recommended: followupRecommended,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "summary", sessionId] });
      toast.success("Summary saved.");
      if (followupRecommended && !showFollowupForm) {
        setShowFollowupForm(true);
      } else {
        onClose();
      }
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const followupMut = useMutation({
    mutationFn: () => proposeFollowup(sessionId, followupTime),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "sessions"] });
      toast.success("Follow-up proposed. Counselee will be notified.");
      onClose();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const summaryValid = summary.trim() && clientDetails.trim() && sessionSmoothly;

  return (
    <Modal open onClose={onClose} title="Session Summary" size="md">
      <div className="space-y-4">
        {!showFollowupForm ? (
          <>
            {/* 1 — mandatory */}
            <div>
              <Label htmlFor="client-details" required>
                1. Client details &amp; problem description
              </Label>
              <textarea
                id="client-details"
                rows={3}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={clientDetails}
                onChange={(e) => setClientDetails(e.target.value)}
                placeholder="Client background and the problem presented…"
              />
            </div>
            {/* 2 — mandatory */}
            <div>
              <Label htmlFor="summary" required>
                2. Session summary
              </Label>
              <textarea
                id="summary"
                rows={4}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="What was discussed? Key observations?"
              />
            </div>
            {/* 3 — optional */}
            <div>
              <Label htmlFor="diagnosis">3. Provisional diagnosis (optional)</Label>
              <textarea
                id="diagnosis"
                rows={2}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={provisionalDiagnosis}
                onChange={(e) => setProvisionalDiagnosis(e.target.value)}
              />
            </div>
            {/* 4 — optional */}
            <div>
              <Label htmlFor="prognosis">4. Case prognosis (optional)</Label>
              <textarea
                id="prognosis"
                rows={2}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={casePrognosis}
                onChange={(e) => setCasePrognosis(e.target.value)}
              />
            </div>
            {/* 5 — choice + mandatory reason */}
            <div>
              <Label required>5. Did the session go smoothly?</Label>
              <select
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={sessionSmoothly}
                onChange={(e) =>
                  setSessionSmoothly(e.target.value as SessionSummary["session_smoothly"])
                }
              >
                <option value="">Select…</option>
                <option value="yes">Yes</option>
                <option value="somewhat">Somewhat</option>
                <option value="no">No</option>
              </select>
              {sessionSmoothly && (
                <textarea
                  rows={2}
                  className="mt-2 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                  value={smoothlyReason}
                  onChange={(e) => setSmoothlyReason(e.target.value)}
                  placeholder="Reason (required)…"
                />
              )}
            </div>
            {/* 6 — mandatory */}
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={followupRecommended}
                onChange={(e) => setFollowupRecommended(e.target.checked)}
                className="h-4 w-4"
              />
              6. Follow-up session needed?
            </label>
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={() => saveMut.mutate()}
                loading={saveMut.isPending}
                disabled={!summaryValid}
              >
                Save summary
              </Button>
            </div>
          </>
        ) : (
          <>
            <Alert>
              <AlertDescription>
                Propose a follow-up session. The counselee will see a countdown and can confirm with
                payment.
              </AlertDescription>
            </Alert>
            <div>
              <Label htmlFor="followup-time" required>
                Proposed date &amp; time
              </Label>
              <Input
                id="followup-time"
                type="datetime-local"
                value={followupTime}
                onChange={(e) => setFollowupTime(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
              <Button variant="outline" onClick={() => setShowFollowupForm(false)}>
                Back
              </Button>
              <Button
                onClick={() => followupMut.mutate()}
                loading={followupMut.isPending}
                disabled={!followupTime}
              >
                Propose follow-up
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// TimeSlots Tab — create/delete available timeslots (SRS §3.1)
// ---------------------------------------------------------------------------

function TimeSlotsTab({ counsellorId }: { counsellorId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [startTime, setStartTime] = useState("");

  const { data: timeslots, isLoading } = useQuery({
    queryKey: ["counseling", "timeslots", counsellorId],
    queryFn: () => listCounsellorTimeslots(counsellorId),
  });

  const createMut = useMutation({
    mutationFn: () => {
      const start = new Date(startTime);
      const end = new Date(start.getTime() + 60 * 60 * 1000); // 1 hour slot
      return createTimeSlot(counsellorId, start.toISOString(), end.toISOString());
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["counseling", "timeslots", counsellorId],
      });
      void queryClient.invalidateQueries({ queryKey: ["counseling", "counsellors"] });
      toast.success("Time slot created.");
      setStartTime("");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const slots = timeslots ?? [];
  const available = slots.filter((s) => s.status === "available");
  const booked = slots.filter((s) => s.status === "booked");

  // Report 3 §1.1: edit/delete existing slots.
  const [editingSlotId, setEditingSlotId] = useState<number | null>(null);
  const [editTime, setEditTime] = useState("");
  const [deleteSlotId, setDeleteSlotId] = useState<number | null>(null);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["counseling", "timeslots", counsellorId] });
    void queryClient.invalidateQueries({ queryKey: ["counseling", "counsellors"] });
  };

  const editMut = useMutation({
    mutationFn: (slotId: number) => {
      const start = new Date(editTime);
      const end = new Date(start.getTime() + 60 * 60 * 1000); // keep 1-hour slots
      return updateTimeSlot(slotId, {
        start_time: start.toISOString(),
        end_time: end.toISOString(),
      });
    },
    onSuccess: () => {
      invalidate();
      toast.success("Time slot updated.");
      setEditingSlotId(null);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const deleteMut = useMutation({
    mutationFn: (slotId: number) => {
      setDeleteSlotId(slotId);
      return deleteTimeSlot(slotId);
    },
    onSuccess: () => {
      invalidate();
      toast.success("Time slot deleted.");
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Add Available Time Slot</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMut.mutate();
            }}
            className="flex items-end gap-2"
          >
            <div className="flex-1">
              <Label htmlFor="ts-start" required>
                Start time
              </Label>
              <Input
                id="ts-start"
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required
              />
            </div>
            <Button type="submit" loading={createMut.isPending} disabled={!startTime}>
              Add 1-hour slot
            </Button>
          </form>
          <p className="mt-2 text-xs text-slate-500">
            Each slot is 1 hour. Add at least 1 week of availability (SRS §3.1).
          </p>
        </CardContent>
      </Card>

      {isLoading ? (
        <Spinner />
      ) : (
        <>
          {available.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Available Slots ({available.length})</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {available.map((s) => (
                  <div
                    key={s.id}
                    className="flex flex-wrap items-center gap-2 rounded-md border border-slate-100 p-2 text-sm"
                  >
                    {editingSlotId === s.id ? (
                      <>
                        <input
                          type="datetime-local"
                          className="h-8 rounded-md border border-slate-200 px-2 text-xs"
                          value={editTime}
                          onChange={(e) => setEditTime(e.target.value)}
                        />
                        <Button
                          size="sm"
                          onClick={() => editMut.mutate(s.id)}
                          loading={editMut.isPending}
                          disabled={!editTime}
                        >
                          Save
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingSlotId(null)}>
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <>
                        <Badge variant="success">{new Date(s.start_time).toLocaleString()}</Badge>
                        {/* Report 3 §1.1: counsellors can edit their slots */}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setEditingSlotId(s.id);
                            setEditTime(new Date(s.start_time).toISOString().slice(0, 16));
                          }}
                        >
                          Edit
                        </Button>
                        {/* Report 3 §1.1: …and delete unbooked slots */}
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => deleteMut.mutate(s.id)}
                          loading={deleteMut.isPending && deleteSlotId === s.id}
                        >
                          Delete
                        </Button>
                      </>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {booked.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Booked Slots ({booked.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {booked.map((s) => (
                    <Badge key={s.id} variant="warning">
                      {new Date(s.start_time).toLocaleString()}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {slots.length === 0 && (
            <p className="py-4 text-center text-sm text-slate-500">
              No time slots yet. Add your availability above.
            </p>
          )}
        </>
      )}
    </div>
  );
}
