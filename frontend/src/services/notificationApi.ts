import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getToken = () => localStorage.getItem('token');

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
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
  telegram_enabled: boolean;
  telegram_chat_id: string | null;
  telegram_bot_token: string | null;
  whatsapp_enabled: boolean;
  whatsapp_phone: string | null;
  whatsapp_webhook_url: string | null;
  trade_notifications: boolean;
  risk_notifications: boolean;
  strategy_notifications: boolean;
  daily_summary: boolean;
}

export const notificationApi = {
  getNotifications: async (unreadOnly = false, limit = 50, offset = 0): Promise<Notification[]> => {
    const params = new URLSearchParams({
      unread_only: String(unreadOnly),
      limit: String(limit),
      offset: String(offset),
    });
    const response = await api.get(`/notifications?${params}`);
    return response.data;
  },

  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const response = await api.get('/notifications/unread-count');
    return response.data;
  },

  markAsRead: async (notificationIds: string[]): Promise<{ marked_read: number }> => {
    const response = await api.post('/notifications/mark-read', {
      notification_ids: notificationIds,
    });
    return response.data;
  },

  markAllAsRead: async (): Promise<{ marked_read: number }> => {
    const response = await api.post('/notifications/mark-all-read');
    return response.data;
  },

  getPreferences: async (): Promise<NotificationPreferences> => {
    const response = await api.get('/notifications/preferences');
    return response.data;
  },

  updatePreferences: async (preferences: Partial<NotificationPreferences>): Promise<NotificationPreferences> => {
    const response = await api.put('/notifications/preferences', preferences);
    return response.data;
  },
};
