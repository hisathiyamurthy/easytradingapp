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

export interface Position {
  id: string;
  symbol: string;
  exchange: string;
  quantity: number;
  avg_price: number;
  current_price?: number;
  unrealized_pnl: number;
  realized_pnl: number;
  market_value?: number;
  is_active: boolean;
}

export interface PortfolioSummary {
  total_value: number;
  total_invested: number;
  total_pnl: number;
  total_pnl_percent: number;
  position_count: number;
}

export interface PortfolioResponse {
  positions: Position[];
  summary: PortfolioSummary;
}

export interface DashboardStats {
  portfolio_value: number;
  today_pnl: number;
  open_positions: number;
  orders_today: number;
  trades_today: number;
  recent_orders: {
    id: string;
    symbol: string;
    side: string;
    quantity: number;
    price?: number;
    status: string;
    created_at: string;
  }[];
}

export const portfolioApi = {
  // Get full portfolio
  getPortfolio: async (): Promise<PortfolioResponse> => {
    const { data } = await api.get('/portfolio');
    return data;
  },

  // Get positions only
  getPositions: async (): Promise<Position[]> => {
    const { data } = await api.get('/portfolio/positions');
    return data;
  },

  // Get portfolio summary
  getSummary: async (): Promise<PortfolioSummary> => {
    const { data } = await api.get('/portfolio/summary');
    return data;
  },

  // Get position by symbol
  getPosition: async (symbol: string): Promise<Position> => {
    const { data } = await api.get(`/portfolio/positions/${symbol}`);
    return data;
  },

  // Get dashboard stats
  getDashboardStats: async (): Promise<DashboardStats> => {
    const { data } = await api.get('/portfolio/dashboard-stats');
    return data;
  },
};

export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
  }).format(value);
};

export const formatPercent = (value: number): string => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};
