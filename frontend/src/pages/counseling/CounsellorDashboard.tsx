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
  getSessionSummary,
  listCounsellorTimeslots,
  listSessions,
  proposeFollowup,
  saveSessionSummary,
  type CounselingSession,
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
  const [summary, setSummary] = useState("");
  const [recommendations, setRecommendations] = useState("");
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
      setSummary(existingSummary.summary);
      setRecommendations(existingSummary.recommendations);
      setFollowupRecommended(existingSummary.followup_recommended);
    }
  });

  const saveMut = useMutation({
    mutationFn: () =>
      saveSessionSummary(sessionId, {
        summary,
        recommendations,
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

  return (
    <Modal open onClose={onClose} title="Session Summary" size="md">
      <div className="space-y-4">
        {!showFollowupForm ? (
          <>
            <div>
              <Label htmlFor="summary" required>
                Session Summary
              </Label>
              <textarea
                id="summary"
                rows={4}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="What was discussed? Key observations?"
                required
              />
            </div>
            <div>
              <Label htmlFor="recs">Recommendations</Label>
              <textarea
                id="recs"
                rows={2}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={recommendations}
                onChange={(e) => setRecommendations(e.target.value)}
                placeholder="Recommendations for the counselee..."
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={followupRecommended}
                onChange={(e) => setFollowupRecommended(e.target.checked)}
                className="h-4 w-4"
              />
              Recommend a follow-up session
            </label>
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={() => saveMut.mutate()}
                loading={saveMut.isPending}
                disabled={!summary}
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
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {available.map((s) => (
                    <Badge key={s.id} variant="success">
                      {new Date(s.start_time).toLocaleString()}
                    </Badge>
                  ))}
                </div>
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
