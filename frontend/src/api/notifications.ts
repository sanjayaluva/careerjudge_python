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

export function listNotifications(): Promise<AppNotification[]> {
  return apiGet<AppNotification[]>(`/notifications/`);
}

export function getUnreadCount(): Promise<number> {
  return apiGet<{ unread_count: number }>(`/notifications/unread_count/`).then(
    (r) => r.unread_count,
  );
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
