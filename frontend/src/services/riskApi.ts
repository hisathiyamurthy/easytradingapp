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

export interface RiskRule {
  id: string;
  user_id: string;
  rule_type: string;
  rule_name: string;
  threshold_value: number;
  threshold_percentage?: number;
  action: string;
  is_enabled: boolean;
  is_hard: boolean;
  created_at: string;
}

export interface RiskStatus {
  active_rules: number;
  active_breaches: number;
  total_exposure: number;
  kill_switch_active: boolean;
  risk_level: 'low' | 'medium' | 'high';
}

export const riskApi = {
  // Get all risk rules
  getRules: async (): Promise<RiskRule[]> => {
    const { data } = await api.get('/risk/rules');
    return data;
  },

  // Create risk rule
  createRule: async (rule: {
    rule_type: string;
    rule_name: string;
    threshold_value: number;
    threshold_percentage?: number;
    action?: string;
    is_enabled?: boolean;
    is_hard?: boolean;
  }): Promise<RiskRule> => {
    const { data } = await api.post('/risk/rules', rule);
    return data;
  },

  // Delete risk rule
  deleteRule: async (ruleId: string): Promise<void> => {
    await api.delete(`/risk/rules/${ruleId}`);
  },

  // Get risk status
  getStatus: async (): Promise<RiskStatus> => {
    const { data } = await api.get('/risk/status');
    return data;
  },

  // Trigger kill switch
  triggerKillSwitch: async (reason?: string): Promise<{ success: boolean; message: string; results?: any }> => {
    const { data } = await api.post('/risk/kill-switch', null, {
      params: { reason: reason || 'Manual trigger' }
    });
    return data;
  },

  // Get kill switch status
  getKillSwitchStatus: async (): Promise<{ is_active: boolean; triggered_at?: string }> => {
    const { data } = await api.get('/risk/kill-switch');
    return data;
  },
};

export const RULE_TYPES = [
  { value: 'daily_loss_limit', label: 'Daily Loss Limit', description: 'Maximum loss per day' },
  { value: 'max_trades_per_day', label: 'Max Trades/Day', description: 'Maximum number of trades per day' },
  { value: 'max_position_size', label: 'Max Position Size', description: 'Maximum position value per trade' },
  { value: 'max_portfolio_exposure', label: 'Max Portfolio Exposure', description: 'Maximum total portfolio exposure' },
  { value: 'min_account_equity', label: 'Min Account Equity', description: 'Minimum account balance' },
];

export const ACTIONS = [
  { value: 'alert', label: 'Alert Only' },
  { value: 'pause_strategy', label: 'Pause Strategy' },
  { value: 'pause_all_trading', label: 'Pause All Trading' },
  { value: 'kill_switch', label: 'Kill Switch' },
];
