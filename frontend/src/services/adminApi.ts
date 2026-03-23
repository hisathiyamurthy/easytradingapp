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

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_strategies: number;
  active_strategies: number;
  total_orders_today: number;
  total_trades_today: number;
  total_volume_today: number;
}

export interface BrokerStatus {
  name: string;
  broker_name: string;
  connected: boolean;
  last_sync: string;
  is_paper_trading: boolean;
}

export interface ActiveSession {
  id: string;
  user_id: string;
  user_email: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_activity_at: string;
  is_active: boolean;
}

export interface PendingUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  created_at: string;
}

export interface UserManagementItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  status: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

export const adminApi = {
  // Get admin dashboard stats
  getStats: async (): Promise<AdminStats> => {
    const { data } = await api.get('/admin/stats');
    return data;
  },

  // Get broker status
  getBrokers: async (): Promise<BrokerStatus[]> => {
    const { data } = await api.get('/admin/brokers');
    return data;
  },

  // Get active sessions
  getActiveSessions: async (): Promise<ActiveSession[]> => {
    const { data } = await api.get('/admin/active-users');
    return data;
  },

  // Get pending users
  getPendingUsers: async (): Promise<PendingUser[]> => {
    const { data } = await api.get('/auth/admin/pending-users');
    return data;
  },

  // Get all users
  getUsers: async (params?: {
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<{ users: UserManagementItem[]; total: number }> => {
    const { data } = await api.get('/auth/admin/users', { params });
    return data;
  },

  // Approve user
  approveUser: async (userId: string): Promise<{ message: string }> => {
    const { data } = await api.post(`/auth/admin/users/${userId}/approve`);
    return data;
  },

  // Reject user
  rejectUser: async (userId: string, reason?: string): Promise<{ message: string }> => {
    const { data } = await api.post(`/auth/admin/users/${userId}/reject`, { reason });
    return data;
  },

  // Suspend user
  suspendUser: async (userId: string, reason?: string): Promise<{ message: string }> => {
    const { data } = await api.post(`/auth/admin/users/${userId}/suspend`, { reason });
    return data;
  },

  // Reactivate user
  reactivateUser: async (userId: string): Promise<{ message: string }> => {
    const { data } = await api.post(`/auth/admin/users/${userId}/reactivate`);
    return data;
  },

  // Revoke session
  revokeSession: async (sessionId: string): Promise<{ message: string }> => {
    const { data } = await api.delete(`/admin/sessions/${sessionId}`);
    return data;
  },
};
