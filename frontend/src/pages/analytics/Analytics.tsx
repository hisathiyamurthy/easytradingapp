import { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Percent, Activity, Target, Loader2, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PortfolioMetrics {
  totalValue: number;
  dailyPnL: number;
  dailyPnLPercent: number;
  totalPnL: number;
  totalPnLPercent: number;
  winRate: number;
  sharpeRatio: number;
  maxDrawdown: number;
  totalTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  expectancy: number;
}

interface ChartDataPoint {
  date: string;
  value: number;
  pnl: number;
  cumulative_pnl: number;
}

interface Trade {
  id: string;
  symbol: string;
  side: string;
  pnl: number | null;
  entry_time: string;
  exit_time: string | null;
}

interface MonthlyReturn {
  month: string;
  return: number;
}

interface SymbolDistribution {
  name: string;
  value: number;
  color: string;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<ChartDataPoint[]>([]);
  const [monthlyReturns, setMonthlyReturns] = useState<MonthlyReturn[]>([]);
  const [symbolDistribution, setSymbolDistribution] = useState<SymbolDistribution[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();
      
      const [paperRes, liveRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/paper-trading/instances`, { headers }),
        fetch(`${API_URL}/api/v1/live-trading/instances`, { headers }),
      ]);

      const paperInstances = paperRes.ok ? await paperRes.json() : [];
      const liveInstances = liveRes.ok ? await liveRes.json() : [];
      const allInstances = [...paperInstances, ...liveInstances];

      let allTrades: Trade[] = [];
      let totalPnL = 0;
      let realizedPnL = 0;
      let unrealizedPnL = 0;
      let winningTrades = 0;
      let losingTrades = 0;
      let totalWinAmount = 0;
      let totalLossAmount = 0;
      let maxValue = 0;
      let peakValue = 0;
      let maxDrawdown = 0;
      const symbolCounts: Record<string, number> = {};

      for (const instance of allInstances) {
        const tradesRes = await fetch(
          `${API_URL}/api/v1/${instance.mode === 'live' ? 'live' : 'paper'}-trading/instances/${instance.id}/trades?limit=1000`,
          { headers }
        );
        if (tradesRes.ok) {
          const instanceTrades = await tradesRes.json();
          allTrades = [...allTrades, ...instanceTrades];
          
          for (const trade of instanceTrades) {
            // Count symbols for distribution chart
            const symbol = trade.symbol || 'UNKNOWN';
            symbolCounts[symbol] = (symbolCounts[symbol] || 0) + 1;
            
            if (trade.pnl !== null) {
              totalPnL += trade.pnl;
              if (trade.pnl > 0) {
                winningTrades++;
                totalWinAmount += trade.pnl;
              } else if (trade.pnl < 0) {
                losingTrades++;
                totalLossAmount += Math.abs(trade.pnl);
              }
            }
            realizedPnL += instance.realized_pnl || 0;
            unrealizedPnL += instance.unrealized_pnl || 0;
          }
        }

        if (instance.capital > maxValue) maxValue = instance.capital;
        const currentValue = instance.capital + (instance.current_pnl || 0);
        if (currentValue > peakValue) peakValue = currentValue;
        const drawdown = ((peakValue - currentValue) / peakValue) * 100;
        if (drawdown > maxDrawdown) maxDrawdown = drawdown;
      }

      const totalTradesCount = winningTrades + losingTrades;
      const winRate = totalTradesCount > 0 ? (winningTrades / totalTradesCount) * 100 : 0;
      const avgWin = winningTrades > 0 ? totalWinAmount / winningTrades : 0;
      const avgLoss = losingTrades > 0 ? totalLossAmount / losingTrades : 0;
      const profitFactor = totalLossAmount > 0 ? totalWinAmount / totalLossAmount : 0;
      const expectancy = totalTradesCount > 0 ? totalPnL / totalTradesCount : 0;
      
      const returns = totalPnL > 0 ? (totalPnL / (maxValue || 1)) * 100 : 0;

      const sharpeRatio = totalTradesCount > 10 ? (expectancy * Math.sqrt(totalTradesCount)) / (avgLoss || 1) : 0;

      setMetrics({
        totalValue: maxValue + totalPnL,
        dailyPnL: unrealizedPnL,
        dailyPnLPercent: maxValue > 0 ? (unrealizedPnL / maxValue) * 100 : 0,
        totalPnL,
        totalPnLPercent: returns,
        winRate,
        sharpeRatio: Math.max(0, sharpeRatio),
        maxDrawdown: -maxDrawdown,
        totalTrades: totalTradesCount,
        avgWin,
        avgLoss,
        profitFactor,
        expectancy,
      });

      const equityData = generateEquityCurve(allTrades, maxValue);
      setEquityCurve(equityData);

      const monthlyData = generateMonthlyReturns(allTrades);
      setMonthlyReturns(monthlyData);

      const symbolData = Object.entries(symbolCounts).map(([name, value], index) => ({
        name,
        value,
        color: COLORS[index % COLORS.length],
      }));
      if (symbolData.length === 0) {
        symbolData.push({ name: 'No Trades', value: 1, color: '#e5e7eb' });
      }
      setSymbolDistribution(symbolData);

      setTrades(allTrades);

    } catch (error) {
      console.error('Error fetching analytics data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const generateEquityCurve = (trades: Trade[], startingCapital: number): ChartDataPoint[] => {
    if (trades.length === 0) {
      const today = new Date();
      const data = [];
      for (let i = 29; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        data.push({
          date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          value: startingCapital,
          pnl: 0,
          cumulative_pnl: 0,
        });
      }
      return data;
    }

    const sortedTrades = [...trades].sort((a, b) => 
      new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime()
    );

    const dataByDate: Record<string, number> = {};
    let cumulative = startingCapital;

    for (const trade of sortedTrades) {
      const date = new Date(trade.entry_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (trade.pnl !== null) {
        cumulative += trade.pnl;
        dataByDate[date] = cumulative;
      }
    }

    const today = new Date();
    const result: ChartDataPoint[] = [];
    let runningValue = startingCapital;

    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      
      if (dataByDate[dateStr]) {
        runningValue = dataByDate[dateStr];
      }

      result.push({
        date: dateStr,
        value: runningValue,
        pnl: runningValue - startingCapital,
        cumulative_pnl: runningValue - startingCapital,
      });
    }

    return result;
  };

  const generateMonthlyReturns = (trades: Trade[]): MonthlyReturn[] => {
    const months: Record<string, { wins: number; losses: number }> = {};
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    for (const trade of trades) {
      if (trade.pnl === null) continue;
      const date = new Date(trade.entry_time);
      const monthKey = `${monthNames[date.getMonth()]}`;
      
      if (!months[monthKey]) {
        months[monthKey] = { wins: 0, losses: 0 };
      }
      if (trade.pnl > 0) {
        months[monthKey].wins += trade.pnl;
      } else {
        months[monthKey].losses += Math.abs(trade.pnl);
      }
    }

    return monthNames.slice(0, 6).map(month => ({
      month,
      return: months[month] ? (months[month].wins - months[month].losses) : 0,
    }));
  };

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const StatCard = ({ title, value, subtitle, icon: Icon, positive }: {
    title: string;
    value: string;
    subtitle?: string;
    icon: React.ElementType;
    positive?: boolean | null;
  }) => (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className={`text-2xl font-bold mt-1 ${positive === true ? 'text-green-600' : positive === false ? 'text-red-600' : ''}`}>
              {value}
            </p>
            {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className={`h-12 w-12 rounded-full flex items-center justify-center ${positive === true ? 'bg-green-100' : positive === false ? 'bg-red-100' : 'bg-blue-100'}`}>
            <Icon className={`h-6 w-6 ${positive === true ? 'text-green-600' : positive === false ? 'text-red-600' : 'text-blue-600'}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Analytics</h1>
            <p className="text-sm text-muted-foreground">Performance metrics and charts</p>
          </div>
        </div>
        <div className="flex gap-2">
          {(['7d', '30d', '90d', 'all'] as const).map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimeRange(range)}
            >
              {range === 'all' ? 'All Time' : range}
            </Button>
          ))}
          <Button variant="outline" size="sm" onClick={fetchAllData}>
            <Activity className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {metrics && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Portfolio Value"
              value={formatCurrency(metrics.totalValue)}
              icon={DollarSign}
            />
            <StatCard
              title="Total P&L"
              value={formatCurrency(metrics.totalPnL)}
              subtitle={`${metrics.totalPnLPercent >= 0 ? '+' : ''}${metrics.totalPnLPercent.toFixed(1)}%`}
              icon={metrics.totalPnL >= 0 ? TrendingUp : TrendingDown}
              positive={metrics.totalPnL >= 0 ? true : metrics.totalPnL < 0 ? false : null}
            />
            <StatCard
              title="Daily P&L"
              value={formatCurrency(metrics.dailyPnL)}
              subtitle={`${metrics.dailyPnLPercent >= 0 ? '+' : ''}${metrics.dailyPnLPercent.toFixed(2)}%`}
              icon={metrics.dailyPnL >= 0 ? TrendingUp : TrendingDown}
              positive={metrics.dailyPnL >= 0 ? true : metrics.dailyPnL < 0 ? false : null}
            />
            <StatCard
              title="Win Rate"
              value={`${metrics.winRate.toFixed(1)}%`}
              subtitle={`${metrics.totalTrades} trades`}
              icon={Target}
              positive={metrics.winRate >= 50 ? true : false}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Sharpe Ratio"
              value={metrics.sharpeRatio.toFixed(2)}
              subtitle="Risk-adjusted return"
              icon={Activity}
            />
            <StatCard
              title="Max Drawdown"
              value={`${metrics.maxDrawdown.toFixed(1)}%`}
              subtitle="Largest peak-to-trough"
              icon={TrendingDown}
              positive={false}
            />
            <StatCard
              title="Profit Factor"
              value={metrics.profitFactor.toFixed(2)}
              subtitle="Win/Loss ratio"
              icon={metrics.profitFactor >= 1 ? TrendingUp : TrendingDown}
              positive={metrics.profitFactor >= 1 ? true : false}
            />
            <StatCard
              title="Expectancy"
              value={formatCurrency(metrics.expectancy)}
              subtitle="Per trade average"
              icon={metrics.expectancy >= 0 ? TrendingUp : TrendingDown}
              positive={metrics.expectancy >= 0 ? true : false}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Equity Curve</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={equityCurve}>
                    <defs>
                      <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={12} />
                    <YAxis fontSize={12} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      labelFormatter={(label) => `Date: ${label}`}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#3b82f6"
                      fillOpacity={1}
                      fill="url(#colorValue)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Monthly Returns</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={monthlyReturns}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" fontSize={12} />
                    <YAxis fontSize={12} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Bar dataKey="return" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                      {monthlyReturns.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.return >= 0 ? '#10b981' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Trade Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={symbolDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {symbolDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Win/Loss Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Winning Trades</span>
                  <span className="text-green-600 font-medium">
                    {metrics.winRate.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-600 h-2 rounded-full"
                    style={{ width: `${metrics.winRate}%` }}
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Losing Trades</span>
                  <span className="text-red-600 font-medium">
                    {(100 - metrics.winRate).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-red-600 h-2 rounded-full"
                    style={{ width: `${100 - metrics.winRate}%` }}
                  />
                </div>
                <hr className="my-4" />
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Avg Win</span>
                  <span className="text-green-600 font-medium">{formatCurrency(metrics.avgWin)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Avg Loss</span>
                  <span className="text-red-600 font-medium">{formatCurrency(metrics.avgLoss)}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Trades</CardTitle>
              </CardHeader>
              <CardContent>
                {trades.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No trades yet</p>
                ) : (
                  <div className="space-y-3 max-h-[250px] overflow-y-auto">
                    {trades.slice(0, 10).map((trade) => (
                      <div key={trade.id} className="flex items-center justify-between text-sm">
                        <div>
                          <span className="font-medium">{trade.symbol}</span>
                          <span className={`ml-2 text-xs px-2 py-0.5 rounded ${
                            trade.side === 'BUY' ? 'bg-blue-100 text-blue-800' : 'bg-orange-100 text-orange-800'
                          }`}>
                            {trade.side}
                          </span>
                        </div>
                        <span className={trade.pnl !== null && trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {trade.pnl !== null ? `${trade.pnl >= 0 ? '+' : ''}${formatCurrency(trade.pnl)}` : '-'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {!metrics && (
        <Card>
          <CardContent className="py-12 text-center">
            <Activity className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium">No Trading Data</h3>
            <p className="text-gray-500 mt-1">
              Start paper trading or live trading to see analytics
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
