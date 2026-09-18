/**
 * Messages (PLT-1 "Send Message") — role-scoped messaging.
 *
 * A two-panel inbox: existing conversations on the left, the selected thread
 * on the right with a reply box. "New message" opens a contact picker (the
 * roles the current user is allowed to message, from the backend).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Label,
  Modal,
  PageCard,
  Select,
  Spinner,
  useToast,
} from "@/components/ui";
import {
  getThread,
  listContacts,
  listConversations,
  sendMessage,
  type Conversation,
} from "@/api/messaging";
import { extractApiError } from "@/api/client";
import { ROLE_LABELS } from "@/lib/constants";
import type { RoleName } from "@/lib/constants";
import { useAuth } from "@/hooks/useAuth";

function roleLabel(role: string): string {
  return ROLE_LABELS[role as RoleName] ?? role;
}

export default function MessagesPage() {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [composeOpen, setComposeOpen] = useState(false);

  const { data: conversations, isLoading } = useQuery({
    queryKey: ["messaging", "conversations"],
    queryFn: () => listConversations(),
    refetchInterval: 15000,
  });

  const list = conversations?.results ?? [];
  const active = list.find((c) => c.id === activeId) ?? null;

  const otherOf = (c: Conversation) =>
    c.user1 === user?.id
      ? { id: c.user2, name: c.user2_name, role: c.user2_role }
      : { id: c.user1, name: c.user1_name, role: c.user1_role };

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="flex items-center justify-between p-6">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Messages</h1>
            <p className="text-sm text-slate-500">
              {list.length} conversation{list.length !== 1 ? "s" : ""}
            </p>
          </div>
          <Button onClick={() => setComposeOpen(true)}>New message</Button>
        </div>
      </PageCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Conversations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {isLoading ? (
              <Spinner />
            ) : list.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-500">
                No conversations yet. Start one with “New message”.
              </p>
            ) : (
              list.map((c) => {
                const other = otherOf(c);
                return (
                  <button
                    key={c.id}
                    onClick={() => setActiveId(c.id)}
                    className={`flex w-full flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition ${
                      c.id === activeId
                        ? "border-primary-300 bg-primary-50"
                        : "border-transparent hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex w-full items-center justify-between">
                      <span className="text-sm font-medium text-slate-900">{other.name}</span>
                      {c.unread_count > 0 && (
                        <Badge variant="success">{c.unread_count}</Badge>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">{roleLabel(other.role)}</span>
                    {c.last_message_preview && (
                      <span className="line-clamp-1 text-xs text-slate-500">
                        {c.last_message_preview}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          {active ? (
            <ThreadPanel
              key={active.id}
              conversation={active}
              other={otherOf(active)}
            />
          ) : (
            <CardContent className="flex min-h-[300px] items-center justify-center text-sm text-slate-500">
              Select a conversation to read and reply.
            </CardContent>
          )}
        </Card>
      </div>

      {composeOpen && (
        <ComposeModal
          onClose={() => setComposeOpen(false)}
          onSent={(recipientId) => {
            setComposeOpen(false);
            void queryClient
              .invalidateQueries({ queryKey: ["messaging", "conversations"] })
              .then(() => {
                // Open the conversation with that recipient once the list refreshes.
                void queryClient
                  .fetchQuery({
                    queryKey: ["messaging", "conversations"],
                    queryFn: () => listConversations(),
                  })
                  .then((data) => {
                    const conv = data.results.find(
                      (c) => c.user1 === recipientId || c.user2 === recipientId,
                    );
                    if (conv) setActiveId(conv.id);
                  });
              });
            toast.success("Message sent.");
          }}
        />
      )}
    </div>
  );
}

function ThreadPanel({
  conversation,
  other,
}: {
  conversation: Conversation;
  other: { id: number; name: string; role: string };
}) {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");

  const { data: messages, isLoading } = useQuery({
    queryKey: ["messaging", "thread", conversation.id],
    queryFn: () => getThread(conversation.id),
    refetchInterval: 10000,
  });

  const sendMutation = useMutation({
    mutationFn: () => sendMessage({ recipient: other.id, body: body.trim() }),
    onSuccess: () => {
      setBody("");
      void queryClient.invalidateQueries({ queryKey: ["messaging", "thread", conversation.id] });
      void queryClient.invalidateQueries({ queryKey: ["messaging", "conversations"] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {other.name}
          <Badge variant="outline">{roleLabel(other.role)}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-3 max-h-[50vh] space-y-2 overflow-auto">
          {isLoading ? (
            <Spinner />
          ) : (messages ?? []).length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">No messages yet.</p>
          ) : (
            (messages ?? []).map((m) => {
              const mine = m.sender === user?.id;
              return (
                <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                      mine ? "bg-primary-600 text-white" : "bg-slate-100 text-slate-900"
                    }`}
                  >
                    {m.subject && <div className="mb-0.5 text-xs font-semibold opacity-80">{m.subject}</div>}
                    <div className="whitespace-pre-wrap">{m.body}</div>
                    <div className={`mt-1 text-[10px] ${mine ? "text-primary-100" : "text-slate-400"}`}>
                      {new Date(m.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (body.trim()) sendMutation.mutate();
          }}
          className="flex gap-2 border-t border-slate-100 pt-3"
        >
          <textarea
            rows={2}
            className="flex-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write a reply…"
          />
          <Button type="submit" loading={sendMutation.isPending} disabled={!body.trim()}>
            Send
          </Button>
        </form>
      </CardContent>
    </>
  );
}

function ComposeModal({
  onClose,
  onSent,
}: {
  onClose: () => void;
  onSent: (recipientId: number) => void;
}) {
  const toast = useToast();
  const [recipient, setRecipient] = useState("");
  const [body, setBody] = useState("");

  const { data: contacts, isLoading } = useQuery({
    queryKey: ["messaging", "contacts"],
    queryFn: () => listContacts(),
  });

  const grouped = useMemo(() => {
    const map = new Map<string, typeof contacts>();
    (contacts ?? []).forEach((c) => {
      const key = c.role__name;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    });
    return Array.from(map.entries());
  }, [contacts]);

  const sendMutation = useMutation({
    mutationFn: () => sendMessage({ recipient: Number(recipient), body: body.trim() }),
    onSuccess: () => onSent(Number(recipient)),
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Modal open onClose={onClose} title="New message" size="md">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (recipient && body.trim()) sendMutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="msg-to" required>
            To
          </Label>
          {isLoading ? (
            <Spinner />
          ) : (
            <Select
              id="msg-to"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              required
            >
              <option value="">Select a contact…</option>
              {grouped.map(([role, people]) => (
                <optgroup key={role} label={roleLabel(role)}>
                  {(people ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_name || p.email}
                    </option>
                  ))}
                </optgroup>
              ))}
            </Select>
          )}
          {!isLoading && (contacts ?? []).length === 0 && (
            <p className="mt-1 text-xs text-slate-500">No contacts available for your role.</p>
          )}
        </div>
        <div>
          <Label htmlFor="msg-body" required>
            Message
          </Label>
          <textarea
            id="msg-body"
            rows={4}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={sendMutation.isPending} disabled={!recipient || !body.trim()}>
            Send message
          </Button>
        </div>
      </form>
    </Modal>
  );
}
