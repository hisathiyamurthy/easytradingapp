// Portfolio page component.
import { useState, useEffect } from 'react';
import { Wallet, TrendingUp, TrendingDown, PieChart, ArrowUpDown, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';
import { portfolioApi, Position, PortfolioSummary, formatCurrency } from '@/services/portfolioApi';

export default function Portfolio() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  const fetchPortfolio = async () => {
    try {
      setRefreshing(true);
      const data = await portfolioApi.getPortfolio();
      setPositions(data.positions);
      setSummary(data.summary);
    } catch (error) {
      console.error('Failed to fetch portfolio:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const formatCurrencyValue = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Wallet className="w-6 h-6 text-primary" />
            <div>
              <h1 className="text-2xl font-bold">Portfolio</h1>
              <p className="text-sm text-muted-foreground">Track your positions and P&L</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wallet className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Portfolio</h1>
            <p className="text-sm text-muted-foreground">Track your positions and P&L</p>
          </div>
        </div>
        <Button 
          variant="outline"
          onClick={fetchPortfolio}
          disabled={refreshing}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Wallet className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Value</p>
                <p className="text-2xl font-bold">{formatCurrencyValue(summary?.total_value || 0)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <PieChart className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Invested</p>
                <p className="text-2xl font-bold">{formatCurrencyValue(summary?.total_invested || 0)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${(summary?.total_pnl || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                {(summary?.total_pnl || 0) >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-green-600" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-red-600" />
                )}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Unrealized P&L</p>
                <p className={`text-2xl font-bold ${(summary?.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrencyValue(summary?.total_pnl || 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${(summary?.total_pnl_percent || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                {(summary?.total_pnl_percent || 0) >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-green-600" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-red-600" />
                )}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">P&L %</p>
                <p className={`text-2xl font-bold ${(summary?.total_pnl_percent || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(summary?.total_pnl_percent || 0) >= 0 ? '+' : ''}{(summary?.total_pnl_percent || 0).toFixed(2)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Positions ({summary?.position_count || 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50 border-b border-surface-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">
                      <div className="flex items-center gap-1">
                        Symbol <ArrowUpDown className="w-4 h-4" />
                      </div>
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Qty</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Avg Price</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">LTP</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Value</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">P&L</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">P&L %</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position) => {
                    const value = (position.current_price || position.avg_price) * position.quantity;
                    const pnlPercent = ((position.current_price || position.avg_price) - position.avg_price) / position.avg_price * 100;
                    return (
                      <tr key={position.id} className="border-b border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium">{position.symbol}</p>
                            <p className="text-sm text-muted-foreground">{position.exchange}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">{position.quantity}</td>
                        <td className="px-4 py-3 text-right">{formatCurrencyValue(position.avg_price)}</td>
                        <td className="px-4 py-3 text-right">{formatCurrencyValue(position.current_price || position.avg_price)}</td>
                        <td className="px-4 py-3 text-right">{formatCurrencyValue(value)}</td>
                        <td className={`px-4 py-3 text-right font-medium ${position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrencyValue(position.unrealized_pnl)}
                        </td>
                        <td className={`px-4 py-3 text-right font-medium ${pnlPercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center">
              <Wallet className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium">No positions yet</h3>
              <p className="text-gray-500 mt-1">Open a position to start tracking your portfolio</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
