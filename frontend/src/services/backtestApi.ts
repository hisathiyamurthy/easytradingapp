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

export interface BacktestConfig {
  strategy_id?: string;
  symbol: string;
  exchange: string;
  from_date: string;
  to_date: string;
  initial_capital: number;
  strategy_type: string;
  parameters?: Record<string, any>;
}

export interface BacktestSummary {
  id: string;
  strategy_id?: string;
  strategy_name: string;
  created_at: string;
  summary: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    total_pnl: number;
    total_pnl_percent: number;
    avg_profit: number;
    avg_loss: number;
    max_drawdown: number;
    sharpe_ratio: number;
    profit_factor: number;
  };
}

export interface BacktestEquityPoint {
  date: string;
  value: number;
  pnl: number;
}

export interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
}

export interface BacktestResult {
  id: string;
  status: string;
  summary?: BacktestSummary;
  equity_curve?: BacktestEquityPoint[];
  trades?: BacktestTrade[];
  error?: string;
}

export const backtestApi = {
  // Run a new backtest
  runBacktest: async (config: BacktestConfig): Promise<{ backtest_id: string }> => {
    const { data } = await api.post('/backtest/run', config);
    return data;
  },

  // Get backtest status/result
  getBacktest: async (backtestId: string): Promise<BacktestResult> => {
    const { data } = await api.get(`/backtest/${backtestId}`);
    return data;
  },

  // Get backtest summary
  getSummary: async (backtestId: string): Promise<BacktestSummary> => {
    const { data } = await api.get(`/backtest/${backtestId}/summary`);
    return data;
  },

  // Get equity curve
  getEquityCurve: async (backtestId: string): Promise<{ equity_curve: BacktestEquityPoint[] }> => {
    const { data } = await api.get(`/backtest/${backtestId}/equity-curve`);
    return data;
  },

  // Get trades
  getTrades: async (backtestId: string): Promise<{ trades: BacktestTrade[] }> => {
    const { data } = await api.get(`/backtest/${backtestId}/trades`);
    return data;
  },

  // Export results
  exportResults: async (backtestId: string, format: 'csv' | 'json' | 'html' | 'pdf'): Promise<Blob> => {
    const { data } = await api.get(`/backtest/${backtestId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return data;
  },

  // List user's backtests
  listBacktests: async (): Promise<{ backtests: BacktestSummary[] }> => {
    const { data } = await api.get('/backtest');
    return data;
  },
};
