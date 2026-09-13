/**
 * H16/D8 §2.3 — live-delivery controls shared by the counselee (CounselingPage)
 * and counsellor (CounsellorDashboard) views: a countdown to the session's
 * scheduled start and a Join-Session button that's only enabled inside the
 * join window (see joinWindow.ts).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Input, useToast } from "@/components/ui";
import { joinSession, setSessionMeetingLink, type CounselingSession } from "@/api/counseling";
import { extractApiError } from "@/api/client";
import { useJoinWindow } from "./joinWindow";

/**
 * D8: shared "join" mutation — hits the backend's join-window-gated
 * redirect endpoint (the authoritative check; the countdown above it is a
 * UX affordance only) and opens the returned meeting_link in a new tab.
 */
function useJoinMutation(session: CounselingSession) {
  const toast = useToast();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => joinSession(session.id),
    onSuccess: (data) => {
      window.open(data.meeting_link, "_blank", "noopener,noreferrer");
      void queryClient.invalidateQueries({ queryKey: ["counseling", "sessions"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

/** Counselee-facing: countdown + Join button, linking to the counsellor's link. */
export function JoinSessionButton({ session }: { session: CounselingSession }) {
  const slot = session.timeslot_detail;
  const { canJoin, label } = useJoinWindow(slot?.start_time, slot?.end_time);
  const joinMutation = useJoinMutation(session);

  if (session.mode !== "online" || !slot) return null;

  return (
    <div className="flex items-center gap-2">
      <Badge variant={canJoin ? "success" : "outline"}>{label}</Badge>
      <Button
        size="sm"
        disabled={!canJoin || !session.meeting_link || joinMutation.isPending}
        loading={joinMutation.isPending}
        onClick={() => joinMutation.mutate()}
        title={!session.meeting_link ? "Counsellor hasn't shared a meeting link yet" : undefined}
      >
        Join Session
      </Button>
    </div>
  );
}

/** Counsellor-facing: same countdown + Join button, plus a way to set the link. */
export function MeetingLinkControl({ session }: { session: CounselingSession }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const slot = session.timeslot_detail;
  const { canJoin, label } = useJoinWindow(slot?.start_time, slot?.end_time);
  const joinMutation = useJoinMutation(session);
  const [editing, setEditing] = useState(false);
  const [link, setLink] = useState(session.meeting_link);

  const saveMut = useMutation({
    mutationFn: () => setSessionMeetingLink(session.id, link),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["counseling", "sessions"] });
      toast.success("Meeting link saved.");
      setEditing(false);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (session.mode !== "online" || !slot) return null;

  if (editing) {
    return (
      <div className="flex items-center gap-1">
        <Input
          value={link}
          onChange={(e) => setLink(e.target.value)}
          placeholder="https://zoom.us/j/…"
          className="h-8 w-40 text-xs"
        />
        <Button size="sm" onClick={() => saveMut.mutate()} loading={saveMut.isPending}>
          Save
        </Button>
        <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <Badge variant={canJoin ? "success" : "outline"}>{label}</Badge>
        <Button
          size="sm"
          disabled={!canJoin || !session.meeting_link || joinMutation.isPending}
          loading={joinMutation.isPending}
          onClick={() => joinMutation.mutate()}
        >
          Join Session
        </Button>
      </div>
      <button
        type="button"
        className="text-left text-xs text-primary-600 hover:underline"
        onClick={() => setEditing(true)}
      >
        {session.meeting_link ? "Edit meeting link" : "Set meeting link"}
      </button>
    </div>
  );
}
