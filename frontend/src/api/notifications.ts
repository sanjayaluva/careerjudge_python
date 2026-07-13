/**
 * Notifications API client.
 */
import { apiDelete, apiGet, apiPost } from "./client";

export interface AppNotification {
  id: number;
  notification_type: string;
  notification_type_label: string;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

/**
 * List my notifications.
 * The backend wraps the response in {message, data: {count, results}} when
 * paginated, or {message, data: [...]} when not. Handle both shapes.
 */
export async function listNotifications(): Promise<AppNotification[]> {
  const data = await apiGet<unknown>("/notifications/");
  // Paginated: {count, next, previous, results: [...]}
  if (data && typeof data === "object" && "results" in (data as Record<string, unknown>)) {
    return (data as { results: AppNotification[] }).results;
  }
  // Flat array
  return data as AppNotification[];
}

export async function getUnreadCount(): Promise<number> {
  const data = await apiGet<{ unread_count: number }>("/notifications/unread_count/");
  return data.unread_count;
}

export function markNotificationRead(id: number): Promise<void> {
  return apiPost(`/notifications/${id}/mark_read/`).then(() => undefined);
}

export function markAllNotificationsRead(): Promise<void> {
  return apiPost(`/notifications/mark_all_read/`).then(() => undefined);
}

export function deleteNotification(id: number): Promise<void> {
  return apiDelete(`/notifications/${id}/`);
}
