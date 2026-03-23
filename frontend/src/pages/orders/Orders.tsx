// Orders page component.
import { useState, useEffect } from 'react';
import { ShoppingCart, Clock, CheckCircle, XCircle, FileText, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';
import { ordersApi, Order, OrderStatus, formatCurrency, getStatusColor, getSideColor } from '@/services/ordersApi';

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [refreshing, setRefreshing] = useState(false);

  const fetchOrders = async () => {
    try {
      setRefreshing(true);
      const params: any = {};
      if (filter !== 'all') {
        params.status = filter;
      }
      const response = await ordersApi.getOrders(params);
      setOrders(response.orders);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [filter]);

  const getStatusIcon = (status: OrderStatus) => {
    switch (status) {
      case 'filled': return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'cancelled': return <XCircle className="w-5 h-5 text-red-600" />;
      case 'rejected': return <XCircle className="w-5 h-5 text-red-600" />;
      case 'pending': return <Clock className="w-5 h-5 text-yellow-600" />;
      default: return <FileText className="w-5 h-5 text-blue-600" />;
    }
  };

  const filters = [
    { value: 'all', label: 'All Orders' },
    { value: 'filled', label: 'Filled' },
    { value: 'pending', label: 'Pending' },
    { value: 'cancelled', label: 'Cancelled' },
    { value: 'rejected', label: 'Rejected' },
  ];

  if (loading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center gap-3">
          <ShoppingCart className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Orders</h1>
            <p className="text-sm text-muted-foreground">View and manage your orders</p>
          </div>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading orders...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShoppingCart className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Orders</h1>
            <p className="text-sm text-muted-foreground">View and manage your orders</p>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm"
          onClick={fetchOrders}
          disabled={refreshing}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="flex gap-2">
        {filters.map(f => (
          <Button
            key={f.value}
            variant={filter === f.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </Button>
        ))}
      </div>

      {orders.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <ShoppingCart className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium">No orders found</h3>
            <p className="text-gray-500 mt-1">
              {filter !== 'all' ? 'Try changing your filter' : 'Place your first order to get started'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50 border-b border-surface-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Order ID</th>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Symbol</th>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Side</th>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Type</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Qty</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Filled</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Price</th>
                    <th className="px-4 py-3 text-center font-medium text-surface-600">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b border-surface-100 hover:bg-surface-50">
                      <td className="px-4 py-3 font-mono text-sm text-surface-600">{order.order_id?.slice(0, 8)}</td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-surface-900">{order.symbol}</p>
                          <p className="text-sm text-surface-500">{order.exchange}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getSideColor(order.side)}`}>
                          {order.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-surface-700 capitalize">{order.order_type}</td>
                      <td className="px-4 py-3 text-right text-surface-700">{order.quantity}</td>
                      <td className="px-4 py-3 text-right text-surface-700">{order.filled_quantity}</td>
                      <td className="px-4 py-3 text-right text-surface-700">
                        {order.price ? formatCurrency(order.price) : 'Market'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          {getStatusIcon(order.status)}
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(order.status)}`}>
                            {order.status.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-surface-500">
                        {new Date(order.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
