// API client for notifications.
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  withCredentials: true,
});

export interface Notification {
  id: string;
  notification_type: string;
  priority: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  push_enabled: boolean;
  webhook_enabled: boolean;
  webhook_url: string | null;
  trade_notifications: boolean;
  risk_notifications: boolean;
  strategy_notifications: boolean;
  daily_summary: boolean;
}

export const notificationsApi = {
  getAll: async (unreadOnly = false): Promise<Notification[]> => {
    const { data } = await api.get(`/notifications?unread_only=${unreadOnly}`);
    return data;
  },

  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const { data } = await api.get('/notifications/unread-count');
    return data;
  },

  markAsRead: async (notificationIds: string[]): Promise<{ marked_read: number }> => {
    const { data } = await api.post('/notifications/mark-read', { notification_ids: notificationIds });
    return data;
  },

  markAllAsRead: async (): Promise<{ marked_read: number }> => {
    const { data } = await api.post('/notifications/mark-all-read');
    return data;
  },

  getPreferences: async (): Promise<NotificationPreferences> => {
    const { data } = await api.get('/notifications/preferences');
    return data;
  },

  updatePreferences: async (preferences: Partial<NotificationPreferences>): Promise<NotificationPreferences> => {
    const { data } = await api.put('/notifications/preferences', preferences);
    return data;
  },
};
