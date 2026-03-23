import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  strategy_type: string;
  status: string;
  is_paper_trading: boolean;
  broker_account_id?: string;
  schedule_cron?: string;
  execution_mode: string;
  created_at: string;
  updated_at: string;
  stats?: {
    total_trades: number;
    win_rate: number;
    pnl: number;
  };
  last_run_at?: string;
}

function getToken(): string | null {
  return localStorage.getItem('token');
}

function getAuthHeaders(): HeadersInit {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export function useStrategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStrategies = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/strategies`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch strategies');
      }

      const data = await response.json();
      setStrategies(data.strategies || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setStrategies([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  return {
    data: strategies,
    strategies,
    loading,
    error,
    refetch: fetchStrategies,
  };
}

export function useActivateStrategy() {
  const [loading, setLoading] = useState(false);

  const mutateAsync = useCallback(async (strategyId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}/activate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to activate strategy');
      }

      return await response.json();
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mutateAsync,
    isPending: loading,
  };
}

export function useDeactivateStrategy() {
  const [loading, setLoading] = useState(false);

  const mutateAsync = useCallback(async (strategyId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}/deactivate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ reason: 'Manual deactivation' }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to deactivate strategy');
      }

      return await response.json();
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mutateAsync,
    isPending: loading,
  };
}

export function useDeleteStrategy() {
  const [loading, setLoading] = useState(false);

  const mutateAsync = useCallback(async (strategyId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete strategy');
      }

      return true;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mutateAsync,
    isPending: loading,
  };
}

export function useCreateStrategy() {
  const [loading, setLoading] = useState(false);

  const mutateAsync = useCallback(async (strategyData: Partial<Strategy>) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/strategies`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(strategyData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create strategy');
      }

      return await response.json();
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mutateAsync,
    isPending: loading,
  };
}

export function useStrategy(strategyId: string) {
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStrategy = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch strategy');
      }

      const data = await response.json();
      setStrategy(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [strategyId]);

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  return {
    data: strategy,
    strategy,
    loading,
    error,
    refetch: fetchStrategy,
  };
}
