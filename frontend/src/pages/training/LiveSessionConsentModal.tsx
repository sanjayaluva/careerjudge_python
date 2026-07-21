/**
 * Live Session Consent Modal — shown when a student opens a course page
 * with an upcoming live session (SRS §5).
 *
 * Per SRS: "When student opens course page, a popup notification about
 * upcoming event (Live Session) appears with meeting link. When student
 * clicks 'Consent' button, notification goes back to trainer about
 * student participation."
 */
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, AlertDescription, Badge, Button, Modal, useToast } from "@/components/ui";
import { consentToLiveSession, type LiveSession } from "@/api/training";
import { extractApiError } from "@/api/client";

export function LiveSessionConsentModal({
  liveSession,
  onClose,
}: {
  liveSession: LiveSession;
  onClose: () => void;
}) {
  const toast = useToast();
  const [dismissed, setDismissed] = useState(false);

  const consentMutation = useMutation({
    mutationFn: (status: "consented" | "declined") => consentToLiveSession(liveSession.id, status),
    onSuccess: (_data, status) => {
      toast.success(
        status === "consented"
          ? "You consented to attend. The trainer has been notified."
          : "You declined this session.",
      );
      setDismissed(true);
      setTimeout(onClose, 1500);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  if (dismissed) return null;

  const scheduled = new Date(liveSession.scheduled_at);
  const isOnline = liveSession.mode === "online";

  return (
    <Modal
      open
      onClose={onClose}
      title="Upcoming Live Session"
      description="You have a live session coming up."
      size="md"
    >
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">{liveSession.title}</h3>
          {liveSession.description && (
            <p className="mt-1 text-sm text-slate-600">{liveSession.description}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Scheduled
            </div>
            <div className="mt-1 text-sm font-semibold text-slate-900">
              {scheduled.toLocaleDateString()}{" "}
              {scheduled.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Duration
            </div>
            <div className="mt-1 text-sm font-semibold text-slate-900">
              {liveSession.duration_minutes} min
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={isOnline ? "primary" : "outline"}>
            {isOnline ? "Online (Zoom)" : "Offline (Classroom)"}
          </Badge>
          {isOnline && liveSession.meeting_url && (
            <a
              href={liveSession.meeting_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary-600 hover:underline"
            >
              Join Zoom meeting ↗
            </a>
          )}
          {!isOnline && liveSession.venue && (
            <span className="text-sm text-slate-600">Venue: {liveSession.venue}</span>
          )}
        </div>

        <Alert variant="default">
          <AlertDescription>
            Will you attend this session? The trainer will be notified of your response.
          </AlertDescription>
        </Alert>

        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button
            variant="outline"
            onClick={() => consentMutation.mutate("declined")}
            loading={consentMutation.isPending}
          >
            Decline
          </Button>
          <Button
            onClick={() => consentMutation.mutate("consented")}
            loading={consentMutation.isPending}
          >
            I&apos;ll attend
          </Button>
        </div>
      </div>
    </Modal>
  );
}
