import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Position {
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
}

export interface Order {
  order_id: string;
  status: string;
  symbol: string;
  quantity: number;
  filled_quantity: number;
  side: 'buy' | 'sell';
  price?: number;
  average_price?: number;
  order_timestamp: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  pnl?: number;
  timestamp: string;
}

export function usePositions() {
  const [data, setData] = useState<Position[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setData([]);
      setIsLoading(false);
      return;
    }
    
    fetch(`${API_URL}/api/v1/portfolio`, { 
      headers: { Authorization: `Bearer ${token}` } 
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch positions');
        return res.json();
      })
      .then(data => {
        setData(data.positions || []);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Positions error:', err);
        setError(err.message);
        setData([]);
        setIsLoading(false);
      });
  }, []);

  return { data, isLoading, error, refetch: () => setIsLoading(true) };
}

export function useOrders() {
  const [data, setData] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setData([]);
      setIsLoading(false);
      return;
    }
    
    fetch(`${API_URL}/api/v1/orders`, { 
      headers: { Authorization: `Bearer ${token}` } 
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch orders');
        return res.json();
      })
      .then(data => {
        setData(Array.isArray(data) ? data : (data.orders || []));
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Orders error:', err);
        setError(err.message);
        setData([]);
        setIsLoading(false);
      });
  }, []);

  return { data, isLoading, error };
}

export function useTradeHistory() {
  const [data, setData] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(false);
    setData([]);
  }, []);

  return { data, isLoading };
}

export interface PlaceOrderRequest {
  symbol: string;
  quantity: number;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit' | 'stop_loss' | 'stop_loss_limit';
  price?: number;
  trigger_price?: number;
  product_type?: string;
  validity?: string;
}

export interface PlaceOrderResponse {
  order_id: string;
  status: string;
  message: string;
}

export function usePlaceOrder() {
  const [isPending, setIsPending] = useState(false);
  
  return {
    isPending,
    mutateAsync: async (order: PlaceOrderRequest): Promise<any> => {
      setIsPending(true);
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/v1/orders`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}` 
          },
          body: JSON.stringify(order),
        });
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Order failed');
        }
        return response.json();
      } finally {
        setIsPending(false);
      }
    },
  };
}
