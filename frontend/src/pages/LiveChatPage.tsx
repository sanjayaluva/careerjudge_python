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
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Live Chat</h1>
          <p className="mt-1 text-sm text-slate-500">
            Chat live with our support team. Replies appear here automatically.
          </p>
        </div>
      </PageCard>

      <Card className="mx-4 mb-6 sm:mx-6">
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            {contactsLoading ? (
              "Connecting…"
            ) : agent ? (
              <>
                <span
                  aria-hidden="true"
                  className="inline-block h-2.5 w-2.5 rounded-full bg-success-500 ring-2 ring-success-100"
                />
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
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : !agent ? (
            <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center text-sm text-slate-500">
              No support agent is available right now. Please try again later or use Contact Admin.
            </p>
          ) : (
            <>
              <div
                ref={scrollRef}
                className="mb-3 h-[50vh] min-h-[16rem] space-y-2 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3"
              >
                {threadLoading && !messages ? (
                  <div className="flex justify-center py-8">
                    <Spinner />
                  </div>
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
                          className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm sm:max-w-[75%] ${
                            mine
                              ? "rounded-br-sm bg-primary-600 text-white"
                              : "rounded-bl-sm bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
                          }`}
                        >
                          <div className="whitespace-pre-wrap break-words leading-relaxed">
                            {m.body}
                          </div>
                          <div
                            className={`mt-1 text-[11px] ${mine ? "text-primary-100" : "text-slate-400"}`}
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
                className="flex items-center gap-2"
              >
                <input
                  className="h-10 min-w-0 flex-1 rounded-full border border-slate-300 bg-white px-4 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 hover:border-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/25"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Type a message…"
                  autoFocus
                />
                <Button
                  type="submit"
                  className="rounded-full"
                  loading={sendMutation.isPending}
                  disabled={!body.trim()}
                >
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
