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

export interface BrokerAccount {
  id: string;
  broker_name: string;
  account_id: string;
  account_name?: string;
  is_paper_trading: boolean;
  is_active: boolean;
  last_sync_at?: string;
  health_status: string;
  created_at: string;
}

export interface BrokerFields {
  broker_name: string;
  name: string;
  fields: {
    name: string;
    label: string;
    type: string;
    required: boolean;
    placeholder?: string;
  }[];
}

export interface BrokerTestResult {
  success: boolean;
  message: string;
  account_id: string;
}

export const brokerApi = {
  // Get all broker accounts
  getAccounts: async (): Promise<BrokerAccount[]> => {
    const { data } = await api.get('/brokers');
    return data;
  },

  // Get broker credential fields
  getBrokerFields: async (): Promise<BrokerFields[]> => {
    const { data } = await api.get('/brokers/fields');
    return data;
  },

  // Get single broker account
  getAccount: async (accountId: string): Promise<BrokerAccount> => {
    const { data } = await api.get(`/brokers/${accountId}`);
    return data;
  },

  // Add new broker account
  addAccount: async (account: {
    broker_name: string;
    account_id: string;
    account_name?: string;
    encrypted_api_key: string;
    encrypted_api_secret: string;
    encrypted_api_passphrase?: string;
    webhook_url?: string;
    is_paper_trading: boolean;
  }): Promise<BrokerAccount> => {
    const { data } = await api.post('/brokers', account);
    return data;
  },

  // Delete broker account
  deleteAccount: async (accountId: string): Promise<void> => {
    await api.delete(`/brokers/${accountId}`);
  },

  // Test broker connection with timeout
  testConnection: async (testData: {
    broker_name: string;
    account_id: string;
    api_key: string;
    api_secret: string;
    api_passphrase?: string;
  }): Promise<BrokerTestResult> => {
    // AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
    
    try {
      const { data } = await api.post('/brokers/test-connection', testData, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return data;
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        throw new Error('Connection test timed out. Please try again.');
      }
      throw error;
    }
  },
};
