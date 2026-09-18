/**
 * Messaging API client (PLT-1 "Send Message" + PLT-6b "Live Chat").
 *
 * The backend exposes role-scoped messaging between two users. The standard
 * Individual User can message CJ Admin / Helpdesk (User Details.pdf p.1).
 */
import { apiGet, apiGetPaged, apiPatch, apiPost } from "./client";

const BASE = "/messaging";

export interface Message {
  id: number;
  sender: number;
  sender_name: string;
  sender_role: string;
  recipient: number;
  recipient_name: string;
  recipient_role: string;
  subject: string;
  body: string;
  is_read: boolean;
  read_at: string | null;
  parent: number | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  user1: number;
  user1_name: string;
  user1_role: string;
  user2: number;
  user2_name: string;
  user2_role: string;
  last_message_at: string | null;
  last_message_preview: string;
  unread_count: number;
  created_at: string;
}

export interface Contact {
  id: number;
  email: string;
  full_name: string;
  role__name: string;
}

export function listConversations(): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: Conversation[];
}> {
  return apiGetPaged<Conversation>(`${BASE}/conversations/`);
}

export function listContacts(): Promise<Contact[]> {
  return apiGet<Contact[]>(`${BASE}/conversations/contacts/`);
}

export function getThread(conversationId: number): Promise<Message[]> {
  return apiGet<Message[]>(`${BASE}/conversations/${conversationId}/thread/`);
}

export function sendMessage(payload: {
  recipient: number;
  body: string;
  subject?: string;
}): Promise<Message> {
  return apiPost<Message>(`${BASE}/messages/`, payload);
}

export function replyToMessage(messageId: number, body: string): Promise<Message> {
  return apiPost<Message>(`${BASE}/messages/${messageId}/reply/`, { body });
}

export function markMessageRead(messageId: number): Promise<void> {
  return apiPatch<void>(`${BASE}/messages/${messageId}/mark_read/`, {});
}
