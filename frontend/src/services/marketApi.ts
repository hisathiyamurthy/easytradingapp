import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  withCredentials: true,
});

export interface Quote {
  symbol: string;
  exchange: string;
  last_price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  bid: number;
  ask: number;
  timestamp: string;
}

export interface IndexQuote {
  symbol: string;
  last_price: number;
  open: number;
  high: number;
  low: number;
  previous_close: number;
  change: number;
  pct_change: number;
  timestamp: string;
}

export interface OHLCV {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
}

export interface CacheStats {
  total_entries: number;
  expired_entries: number;
  valid_entries: number;
  redis_enabled: boolean;
}

export const marketApi = {
  // Get single quote
  getQuote: async (symbol: string, exchange = 'NSE', useCache = true): Promise<Quote> => {
    const { data } = await api.get(`/market/quote/${symbol}`, {
      params: { exchange, use_cache: useCache },
    });
    return data;
  },

  // Get multiple quotes
  getQuotes: async (symbols: string[], exchange = 'NSE'): Promise<Quote[]> => {
    const { data } = await api.get('/market/quotes', {
      params: { symbols: symbols.join(','), exchange },
    });
    return data;
  },

  // Get index quote
  getIndex: async (index: string): Promise<IndexQuote> => {
    const { data } = await api.get(`/market/index/${index}`);
    return data;
  },

  // Get historical data
  getHistorical: async (
    symbol: string,
    options: {
      exchange?: string;
      interval?: string;
      fromDate?: string;
      toDate?: string;
    } = {}
  ): Promise<OHLCV[]> => {
    const { exchange = 'NSE', interval = '1d', fromDate, toDate } = options;
    const { data } = await api.get(`/market/historical/${symbol}`, {
      params: { exchange, interval, from_date: fromDate, to_date: toDate },
    });
    return data;
  },

  // Search symbols
  searchSymbols: async (query: string): Promise<SearchResult[]> => {
    const { data } = await api.get('/market/search', {
      params: { q: query },
    });
    return data;
  },

  // Cache management
  getCacheStats: async (): Promise<CacheStats> => {
    const { data } = await api.get('/market/cache/stats');
    return data;
  },

  clearCache: async (): Promise<{ status: string }> => {
    const { data } = await api.post('/market/cache/clear');
    return data;
  },
};

// Utility functions
export const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price);
};

export const formatVolume = (volume: number): string => {
  if (volume >= 10000000) {
    return `${(volume / 10000000).toFixed(2)} Cr`;
  }
  if (volume >= 100000) {
    return `${(volume / 100000).toFixed(2)} L`;
  }
  if (volume >= 1000) {
    return `${(volume / 1000).toFixed(2)} K`;
  }
  return volume.toString();
};

export const formatChange = (change: number, pctChange: number): string => {
  const sign = change >= 0 ? '+' : '';
  return `${sign}${change.toFixed(2)} (${sign}${pctChange.toFixed(2)}%)`;
};

export const getChangeColor = (change: number): string => {
  if (change > 0) return 'text-green-600';
  if (change < 0) return 'text-red-600';
  return 'text-gray-600';
};
