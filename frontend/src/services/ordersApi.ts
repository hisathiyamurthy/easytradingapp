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

export type OrderStatus = 'pending' | 'submitted' | 'filled' | 'cancelled' | 'rejected' | 'partially_filled';
export type OrderSide = 'buy' | 'sell';
export type OrderType = 'market' | 'limit' | 'stop_loss' | 'stop_loss_limit';

export interface Order {
  id: string;
  order_id: string;
  client_order_id?: string;
  broker_order_id?: string;
  user_id: string;
  strategy_id?: string;
  broker_account_id?: string;
  symbol: string;
  exchange: string;
  side: OrderSide;
  order_type: OrderType;
  product_type: string;
  validity: string;
  quantity: number;
  filled_quantity: number;
  remaining_quantity: number;
  cancelled_quantity: number;
  price?: number;
  trigger_price?: number;
  avg_fill_price?: number;
  status: OrderStatus;
  error_message?: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  filled_at?: string;
  cancelled_at?: string;
}

export interface OrderCreate {
  symbol: string;
  exchange: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  price?: number;
  trigger_price?: number;
  product_type?: string;
  validity?: string;
}

export interface OrderListResponse {
  orders: Order[];
  total: number;
  page: number;
  page_size: number;
}

export const ordersApi = {
  // Get all orders with optional filters
  getOrders: async (params?: {
    status?: string;
    symbol?: string;
    from_date?: string;
    to_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<OrderListResponse> => {
    const { data } = await api.get('/orders', { params });
    return data;
  },

  // Get single order
  getOrder: async (orderId: string): Promise<Order> => {
    const { data } = await api.get(`/orders/${orderId}`);
    return data;
  },

  // Create new order
  createOrder: async (order: OrderCreate): Promise<Order> => {
    const { data } = await api.post('/orders', order);
    return data;
  },

  // Cancel order
  cancelOrder: async (orderId: string): Promise<Order> => {
    const { data } = await api.post(`/orders/${orderId}/cancel`);
    return data;
  },

  // Modify order
  modifyOrder: async (orderId: string, modifications: {
    quantity?: number;
    price?: number;
    trigger_price?: string;
  }): Promise<Order> => {
    const { data } = await api.patch(`/orders/${orderId}`, modifications);
    return data;
  },

  // Get order history
  getOrderHistory: async (orderId: string): Promise<any[]> => {
    const { data } = await api.get(`/orders/${orderId}/history`);
    return data;
  },
};

export const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '-';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
  }).format(value);
};

export const getStatusColor = (status: OrderStatus): string => {
  const colors: Record<OrderStatus, string> = {
    filled: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    submitted: 'bg-blue-100 text-blue-800',
    partially_filled: 'bg-blue-100 text-blue-800',
    cancelled: 'bg-red-100 text-red-800',
    rejected: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
};

export const getSideColor = (side: OrderSide): string => {
  return side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
};
