import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { TrendingUp, Wallet, Activity, BarChart3, ArrowUpRight, ArrowDownRight, Plus } from 'lucide-react';
import { Card, CardHeader, CardContent, CardTitle, Badge, Button } from '@/components/ui';
import { portfolioApi, DashboardStats, formatCurrency } from '@/services/portfolioApi';

const portfolioData = [
  { date: 'Jan', value: 100000 },
  { date: 'Feb', value: 105000 },
  { date: 'Mar', value: 102000 },
  { date: 'Apr', value: 108000 },
  { date: 'May', value: 115000 },
  { date: 'Jun', value: 112000 },
  { date: 'Jul', value: 118000 },
];

const marketData = [
  { symbol: 'NIFTY 50', price: 21567.45, change: 125.30, changePercent: 0.58 },
  { symbol: 'SENSEX', price: 71826.12, change: -45.28, changePercent: -0.06 },
  { symbol: 'BANKNIFTY', price: 48567.80, change: 234.50, changePercent: 0.49 },
  { symbol: 'RELIANCE', price: 2945.65, change: -12.40, changePercent: -0.42 },
  { symbol: 'TCS', price: 3892.30, change: 45.70, changePercent: 1.19 },
];

export function Dashboard() {
  const [timeRange, setTimeRange] = useState('1M');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const data = await portfolioApi.getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="animate-pulse">
                  <div className="h-12 w-12 bg-gray-200 rounded-lg mb-4"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const pnlPercent = stats && stats.portfolio_value > 0 
    ? (stats.today_pnl / (stats.portfolio_value - stats.today_pnl)) * 100 
    : 0;

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Portfolio Value"
          value={formatCurrency(stats?.portfolio_value || 0)}
          change={stats && stats.portfolio_value > 0 ? `${((stats.today_pnl / stats.portfolio_value) * 100).toFixed(1)}%` : '0%'}
          changeType={stats && stats.today_pnl >= 0 ? "positive" : "negative"}
          icon={<Wallet className="w-6 h-6" />}
        />
        <StatCard
          label="Today's P&L"
          value={formatCurrency(stats?.today_pnl || 0)}
          change={`${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(1)}%`}
          changeType={stats && stats.today_pnl >= 0 ? "positive" : "negative"}
          icon={<TrendingUp className="w-6 h-6" />}
        />
        <StatCard
          label="Open Positions"
          value={String(stats?.open_positions || 0)}
          change={`+${stats?.trades_today || 0} today`}
          changeType="neutral"
          icon={<Activity className="w-6 h-6" />}
        />
        <StatCard
          label="Today's Trades"
          value={String(stats?.trades_today || 0)}
          change={`${stats?.orders_today || 0} orders`}
          changeType="neutral"
          icon={<BarChart3 className="w-6 h-6" />}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Portfolio Chart */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-surface-900">Portfolio Performance</h3>
              <p className="text-sm text-surface-500">Track your portfolio value over time</p>
            </div>
            <div className="flex gap-2">
              {['1W', '1M', '3M', '1Y'].map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                    timeRange === range
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-surface-600 hover:bg-surface-100'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={portfolioData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} tickFormatter={(value) => `₹${value/1000}k`} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                    }}
                    formatter={(value: number) => [`₹${value.toLocaleString()}`, 'Value']}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorValue)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Market Overview */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-surface-900">Market Overview</h3>
            <p className="text-sm text-surface-500">Live market indices</p>
          </CardHeader>
          <CardContent className="space-y-4">
            {marketData.map((item) => (
              <div key={item.symbol} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                <div>
                  <p className="font-medium text-surface-900">{item.symbol}</p>
                  <p className="text-sm text-surface-500">₹{item.price.toLocaleString()}</p>
                </div>
                <div className={`flex items-center gap-1 ${item.change >= 0 ? 'text-accent-600' : 'text-danger'}`}>
                  {item.change >= 0 ? (
                    <ArrowUpRight className="w-4 h-4" />
                  ) : (
                    <ArrowDownRight className="w-4 h-4" />
                  )}
                  <span className="text-sm font-medium">
                    {item.change >= 0 ? '+' : ''}{item.change} ({item.changePercent}%)
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Orders & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Orders */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-surface-900">Recent Orders</h3>
              <p className="text-sm text-surface-500">Your latest trading activity</p>
            </div>
            <Button variant="ghost" size="sm">View All</Button>
          </CardHeader>
          <CardContent className="p-0">
            {stats?.recent_orders && stats.recent_orders.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-surface-50 border-b border-surface-200">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-surface-600">Symbol</th>
                      <th className="px-4 py-3 text-left font-medium text-surface-600">Type</th>
                      <th className="px-4 py-3 text-left font-medium text-surface-600">Qty</th>
                      <th className="px-4 py-3 text-left font-medium text-surface-600">Price</th>
                      <th className="px-4 py-3 text-left font-medium text-surface-600">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_orders.map((order) => (
                      <tr key={order.id} className="border-b border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3 font-medium text-surface-900">{order.symbol}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            order.side === 'buy' ? 'bg-accent-100 text-accent-700' : 'bg-danger-light text-red-700'
                          }`}>
                            {order.side.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-surface-700">{order.quantity}</td>
                        <td className="px-4 py-3 text-surface-700">₹{order.price || 'Market'}</td>
                        <td className="px-4 py-3">
                          {order.status === 'filled' && <Badge variant="success">Filled</Badge>}
                          {order.status === 'pending' && <Badge variant="warning">Pending</Badge>}
                          {order.status === 'rejected' && <Badge variant="danger">Rejected</Badge>}
                          {order.status === 'cancelled' && <Badge variant="danger">Cancelled</Badge>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-8 text-center text-surface-500">
                No recent orders. Place your first order to get started.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-surface-900">Quick Actions</h3>
            <p className="text-sm text-surface-500">Common trading operations</p>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              New Order
            </Button>
            <Button className="w-full justify-start" variant="secondary">
              <TrendingUp className="w-4 h-4 mr-2" />
              Quick Trade
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <BarChart3 className="w-4 h-4 mr-2" />
              Run Backtest
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <Wallet className="w-4 h-4 mr-2" />
              Add Funds
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ label, value, change, changeType, icon }: { label: string; value: string; change: string; changeType: string; icon: React.ReactNode }) {
  const changeColors = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-surface-500',
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center text-primary">
            {icon}
          </div>
        </div>
        <div className="mt-4">
          <p className="text-sm text-surface-500">{label}</p>
          <p className="text-2xl font-bold text-surface-900 mt-1">{value}</p>
          <p className={`text-sm mt-1 ${changeColors[changeType as keyof typeof changeColors]}`}>
            {change}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export default Dashboard;
