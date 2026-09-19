/**
 * Concerns / Contact Admin (ADM-2 / D9 §4) — system-management concern routing.
 *
 * Any signed-in user can raise a concern (routed to the CJ Admin + Helpdesk).
 * Admins get an inbox of all concerns and can mark them resolved.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  PageCard,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
  useToast,
} from "@/components/ui";
import { concernsApi } from "@/api/tasks";
import { extractApiError } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

export default function ConcernsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const isAdmin = user?.role === "cj_admin";

  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");

  const { data: concerns, isLoading } = useQuery({
    queryKey: ["concerns"],
    queryFn: () => concernsApi.list(),
  });

  const raiseMutation = useMutation({
    mutationFn: () => concernsApi.create({ subject: subject.trim(), message: message.trim() }),
    onSuccess: () => {
      toast.success("Concern raised — the admin and helpdesk have been notified.");
      setSubject("");
      setMessage("");
      void queryClient.invalidateQueries({ queryKey: ["concerns"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const resolveMutation = useMutation({
    mutationFn: (v: { id: number; comment: string }) => concernsApi.resolve(v.id, v.comment),
    onSuccess: () => {
      toast.success("Concern resolved.");
      void queryClient.invalidateQueries({ queryKey: ["concerns"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const rows = concerns?.results ?? [];

  return (
    <PageCard>
      <div className="mb-4">
        <h1 className="text-xl font-semibold text-slate-900">
          {isAdmin ? "Concerns" : "Contact Admin"}
        </h1>
        <p className="text-sm text-slate-500">
          {isAdmin
            ? "Concerns raised by users, routed to the admin and helpdesk (D9 §4)."
            : "Raise an issue, request, or feedback — it is routed to the admin and helpdesk."}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Raise a concern</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              raiseMutation.mutate();
            }}
            className="space-y-3"
          >
            <div>
              <Label htmlFor="c-subject" required>
                Subject
              </Label>
              <Input
                id="c-subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Short summary"
                required
              />
            </div>
            <div>
              <Label htmlFor="c-message" required>
                Message
              </Label>
              <textarea
                id="c-message"
                rows={3}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Describe your issue, request, or feedback…"
                required
              />
            </div>
            <div className="flex justify-end">
              <Button
                type="submit"
                loading={raiseMutation.isPending}
                disabled={!subject.trim() || !message.trim()}
              >
                Submit
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>{isAdmin ? "Inbox" : "My concerns"}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subject</TableHead>
                  {isAdmin && <TableHead>Raised by</TableHead>}
                  <TableHead>Status</TableHead>
                  <TableHead>Raised</TableHead>
                  {isAdmin && <TableHead className="text-right">Action</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 ? (
                  <TableEmpty colSpan={isAdmin ? 5 : 3}>No concerns yet.</TableEmpty>
                ) : (
                  rows.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell>
                        <div className="font-medium text-slate-900">{c.subject}</div>
                        <div className="max-w-md truncate text-xs text-slate-500">{c.message}</div>
                        {c.status === "resolved" && c.resolution_comment && (
                          <div className="mt-1 text-xs text-green-700">
                            Resolved: {c.resolution_comment}
                          </div>
                        )}
                      </TableCell>
                      {isAdmin && (
                        <TableCell className="text-slate-500">{c.raised_by_name}</TableCell>
                      )}
                      <TableCell>
                        <Badge variant={c.status === "open" ? "warning" : "success"}>
                          {c.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">
                        {new Date(c.created_at).toLocaleDateString()}
                      </TableCell>
                      {isAdmin && (
                        <TableCell className="text-right">
                          {c.status === "open" && (
                            <Button
                              size="sm"
                              variant="outline"
                              loading={resolveMutation.isPending}
                              onClick={() => {
                                const comment =
                                  window.prompt("Resolution comment (optional):") ?? "";
                                resolveMutation.mutate({ id: c.id, comment });
                              }}
                            >
                              Resolve
                            </Button>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </PageCard>
  );
}
