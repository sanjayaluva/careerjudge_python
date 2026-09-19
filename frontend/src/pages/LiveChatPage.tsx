/**
 * Live Chat (PLT-6b) — a real-time support chat for the standard Individual
 * User (User Details.pdf p.1). Built on the messaging backend: the page opens
 * a single conversation with a support agent (CJ Admin, else Helpdesk) and
 * polls the thread on a short interval so replies appear live.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageCard,
  Spinner,
} from "@/components/ui";
import {
  getThread,
  listContacts,
  listConversations,
  sendMessage,
  type Contact,
} from "@/api/messaging";
import { extractApiError } from "@/api/client";
import { ROLE_LABELS } from "@/lib/constants";
import type { RoleName } from "@/lib/constants";
import { useAuth } from "@/hooks/useAuth";

function pickAgent(contacts: Contact[]): Contact | null {
  return (
    contacts.find((c) => c.role__name === "cj_admin") ??
    contacts.find((c) => c.role__name === "helpdesk") ??
    contacts[0] ??
    null
  );
}

export default function LiveChatPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: contacts, isLoading: contactsLoading } = useQuery({
    queryKey: ["messaging", "contacts"],
    queryFn: () => listContacts(),
  });
  const agent = useMemo(() => pickAgent(contacts ?? []), [contacts]);

  const { data: conversations } = useQuery({
    queryKey: ["messaging", "conversations"],
    queryFn: () => listConversations(),
    refetchInterval: 8000,
  });

  const activeConv = useMemo(() => {
    if (!agent) return null;
    return (
      (conversations?.results ?? []).find((c) => c.user1 === agent.id || c.user2 === agent.id) ??
      null
    );
  }, [conversations, agent]);

  const { data: messages, isLoading: threadLoading } = useQuery({
    queryKey: ["messaging", "thread", activeConv?.id],
    queryFn: () => getThread(activeConv!.id),
    enabled: !!activeConv,
    refetchInterval: 4000,
  });

  const sendMutation = useMutation({
    mutationFn: () => sendMessage({ recipient: agent!.id, body: body.trim() }),
    onSuccess: () => {
      setBody("");
      void queryClient.invalidateQueries({ queryKey: ["messaging", "conversations"] });
      if (activeConv) {
        void queryClient.invalidateQueries({ queryKey: ["messaging", "thread", activeConv.id] });
      }
    },
  });

  // Keep the transcript scrolled to the newest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  return (
    <div className="space-y-6">
      <PageCard>
        <div className="p-6">
          <h1 className="text-lg font-bold text-slate-900">Live Chat</h1>
          <p className="text-sm text-slate-500">
            Chat live with our support team. Replies appear here automatically.
          </p>
        </div>
      </PageCard>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {contactsLoading ? (
              "Connecting…"
            ) : agent ? (
              <>
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
                {agent.full_name || agent.email}
                <Badge variant="outline">
                  {ROLE_LABELS[agent.role__name as RoleName] ?? agent.role__name}
                </Badge>
              </>
            ) : (
              "Support"
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {contactsLoading ? (
            <Spinner />
          ) : !agent ? (
            <p className="py-8 text-center text-sm text-slate-500">
              No support agent is available right now. Please try again later or use Contact Admin.
            </p>
          ) : (
            <>
              <div
                ref={scrollRef}
                className="mb-3 h-[50vh] space-y-2 overflow-auto rounded-md bg-slate-50 p-3"
              >
                {threadLoading && !messages ? (
                  <Spinner />
                ) : (messages ?? []).length === 0 ? (
                  <p className="py-8 text-center text-sm text-slate-500">
                    Say hello 👋 — send a message to start the chat.
                  </p>
                ) : (
                  (messages ?? []).map((m) => {
                    const mine = m.sender === user?.id;
                    return (
                      <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[75%] rounded-2xl px-3 py-2 text-sm ${
                            mine
                              ? "rounded-br-sm bg-primary-600 text-white"
                              : "rounded-bl-sm bg-white text-slate-900 shadow-sm"
                          }`}
                        >
                          <div className="whitespace-pre-wrap">{m.body}</div>
                          <div
                            className={`mt-1 text-[10px] ${mine ? "text-primary-100" : "text-slate-400"}`}
                          >
                            {new Date(m.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
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
                className="flex gap-2"
              >
                <input
                  className="flex-1 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Type a message…"
                  autoFocus
                />
                <Button type="submit" loading={sendMutation.isPending} disabled={!body.trim()}>
                  Send
                </Button>
              </form>
              {sendMutation.isError && (
                <p className="mt-2 text-xs text-danger-600">
                  {extractApiError(sendMutation.error)}
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
