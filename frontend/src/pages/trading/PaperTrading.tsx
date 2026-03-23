import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Play, Pause, Square, RefreshCw, TrendingUp, TrendingDown,
  Loader2, Plus, Trash2, Eye, DollarSign, BarChart3
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, Button, Badge, Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PaperTradingInstance {
  id: string;
  strategy_id: string;
  name: string;
  capital: number;
  allocated_capital: number;
  status: string;
  mode: string;
  current_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
  started_at: string;
  created_at: string;
}

interface Position {
  id: string;
  symbol: string;
  exchange: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  is_open: boolean;
  opened_at: string;
}

interface Trade {
  id: string;
  symbol: string;
  exchange: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  pnl: number | null;
  commission: number;
  entry_time: string;
  exit_time: string | null;
  entry_signal: string;
  exit_reason: string | null;
}

export default function PaperTrading() {
  const navigate = useNavigate();
  const { instanceId } = useParams();
  
  const [instances, setInstances] = useState<PaperTradingInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<PaperTradingInstance | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  const fetchInstances = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/paper-trading/instances`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setInstances(data);
        if (data.length > 0 && !selectedInstance) {
          setSelectedInstance(data[0]);
        }
      }
    } catch (error) {
      console.error('Error fetching instances:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedInstance]);

  const fetchInstanceDetails = useCallback(async (instanceId: string) => {
    try {
      const token = localStorage.getItem('token');
      
      const [instRes, posRes, tradeRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/paper-trading/instances/${instanceId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/paper-trading/instances/${instanceId}/positions`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/paper-trading/instances/${instanceId}/trades?limit=50`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);
      
      if (instRes.ok) {
        const inst = await instRes.json();
        setSelectedInstance(inst);
      }
      
      if (posRes.ok) {
        setPositions(await posRes.json());
      }
      
      if (tradeRes.ok) {
        setTrades(await tradeRes.json());
      }
    } catch (error) {
      console.error('Error fetching instance details:', error);
    }
  }, []);

  useEffect(() => {
    fetchInstances();
  }, [fetchInstances]);

  useEffect(() => {
    if (instanceId) {
      fetchInstanceDetails(instanceId);
    } else if (selectedInstance) {
      fetchInstanceDetails(selectedInstance.id);
    }
  }, [instanceId, selectedInstance, fetchInstanceDetails]);

  const handleRunTick = async () => {
    if (!selectedInstance) return;
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/paper-trading/instances/${selectedInstance.id}/tick`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchInstanceDetails(selectedInstance.id);
    } catch (error) {
      console.error('Error running tick:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    if (!selectedInstance) return;
    setActionLoading(true);
    try {
      await fetch(`${API_URL}/api/v1/paper-trading/instances/${selectedInstance.id}/pause`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error pausing:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    if (!selectedInstance) return;
    setActionLoading(true);
    try {
      await fetch(`${API_URL}/api/v1/paper-trading/instances/${selectedInstance.id}/resume`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error resuming:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    if (!selectedInstance) return;
    setActionLoading(true);
    try {
      await fetch(`${API_URL}/api/v1/paper-trading/instances/${selectedInstance.id}/stop`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error stopping:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-green-100 text-green-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      case 'stopped': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

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
        <div>
          <h1 className="text-2xl font-bold">Paper Trading</h1>
          <p className="text-muted-foreground">Simulated trading with real market conditions</p>
        </div>
        <Button onClick={() => navigate('/strategies')}>
          <Plus className="w-4 h-4 mr-2" />
          New Strategy
        </Button>
      </div>

      {instances.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <BarChart3 className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium">No Paper Trading Instances</h3>
            <p className="text-gray-500 mt-1">
              Create a backtested strategy to start paper trading
            </p>
            <Button className="mt-4" onClick={() => navigate('/strategies')}>
              Go to Strategies
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Instance Selector */}
          <div className="flex gap-2 overflow-x-auto pb-2">
            {instances.map((inst) => (
              <button
                key={inst.id}
                onClick={() => setSelectedInstance(inst)}
                className={`px-4 py-2 rounded-lg border whitespace-nowrap ${
                  selectedInstance?.id === inst.id
                    ? 'border-primary bg-primary/10'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-sm font-medium">{inst.name}</div>
                <div className="text-xs text-muted-foreground">
                  {formatCurrency(inst.capital)} • {inst.status}
                </div>
              </button>
            ))}
          </div>

          {selectedInstance && (
            <>
              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Capital</p>
                        <p className="text-2xl font-bold">{formatCurrency(selectedInstance.capital)}</p>
                      </div>
                      <DollarSign className="h-8 w-8 text-blue-500" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">P&L</p>
                        <p className={`text-2xl font-bold ${selectedInstance.current_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {selectedInstance.current_pnl >= 0 ? '+' : ''}{formatCurrency(selectedInstance.current_pnl)}
                        </p>
                      </div>
                      {selectedInstance.current_pnl >= 0 ? (
                        <TrendingUp className="h-8 w-8 text-green-500" />
                      ) : (
                        <TrendingDown className="h-8 w-8 text-red-500" />
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Trades</p>
                        <p className="text-2xl font-bold">{selectedInstance.trades_count}</p>
                        <p className="text-xs text-muted-foreground">
                          <span className="text-green-600">{selectedInstance.winning_trades}W</span> /{' '}
                          <span className="text-red-600">{selectedInstance.losing_trades}L</span>
                        </p>
                      </div>
                      <BarChart3 className="h-8 w-8 text-purple-500" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Status</p>
                        <Badge className={getStatusColor(selectedInstance.status)}>
                          {selectedInstance.status}
                        </Badge>
                      </div>
                      {selectedInstance.status === 'running' ? (
                        <Play className="h-8 w-8 text-green-500" />
                      ) : selectedInstance.status === 'paused' ? (
                        <Pause className="h-8 w-8 text-yellow-500" />
                      ) : (
                        <Square className="h-8 w-8 text-red-500" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                {selectedInstance.status === 'running' ? (
                  <>
                    <Button onClick={handleRunTick} disabled={actionLoading}>
                      {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                      Run Tick
                    </Button>
                    <Button variant="outline" onClick={handlePause} disabled={actionLoading}>
                      <Pause className="w-4 h-4 mr-2" />
                      Pause
                    </Button>
                  </>
                ) : selectedInstance.status === 'paused' ? (
                  <Button onClick={handleResume} disabled={actionLoading}>
                    <Play className="w-4 h-4 mr-2" />
                    Resume
                  </Button>
                ) : null}
                
                {selectedInstance.status !== 'stopped' && (
                  <Button variant="destructive" onClick={handleStop} disabled={actionLoading}>
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </Button>
                )}
              </div>

              {/* Tabs */}
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                  <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
                  <TabsTrigger value="positions">Positions ({positions.length})</TabsTrigger>
                  <TabsTrigger value="trades">Trades ({trades.length})</TabsTrigger>
                </TabsList>

                <TabsContent value="dashboard">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card>
                      <CardHeader>
                        <CardTitle>Performance</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Realized P&L</span>
                          <span className={selectedInstance.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                            {formatCurrency(selectedInstance.realized_pnl)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Unrealized P&L</span>
                          <span className={selectedInstance.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                            {formatCurrency(selectedInstance.unrealized_pnl)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Allocated Capital</span>
                          <span>{formatCurrency(selectedInstance.allocated_capital)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Available Capital</span>
                          <span>{formatCurrency(selectedInstance.capital - selectedInstance.allocated_capital)}</span>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle>Win Rate</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-4xl font-bold text-center">
                          {selectedInstance.trades_count > 0
                            ? ((selectedInstance.winning_trades / selectedInstance.trades_count) * 100).toFixed(1)
                            : 0}%
                        </div>
                        <p className="text-center text-muted-foreground mt-2">
                          {selectedInstance.winning_trades} wins / {selectedInstance.losing_trades} losses
                        </p>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="positions">
                  <Card>
                    <CardHeader>
                      <CardTitle>Open Positions</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {positions.length === 0 ? (
                        <p className="text-center text-muted-foreground py-8">No open positions</p>
                      ) : (
                        <div className="space-y-4">
                          {positions.map((pos) => (
                            <div key={pos.id} className="flex items-center justify-between p-4 border rounded-lg">
                              <div>
                                <div className="flex items-center gap-2">
                                  <Badge variant={pos.side === 'BUY' ? 'default' : 'secondary'}>
                                    {pos.side}
                                  </Badge>
                                  <span className="font-medium">{pos.symbol}</span>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  Qty: {pos.quantity} @ {formatCurrency(pos.entry_price)}
                                </p>
                              </div>
                              <div className="text-right">
                                <p className={`font-medium ${pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {pos.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(pos.unrealized_pnl)}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  LTP: {formatCurrency(pos.current_price)}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="trades">
                  <Card>
                    <CardHeader>
                      <CardTitle>Trade History</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {trades.length === 0 ? (
                        <p className="text-center text-muted-foreground py-8">No trades yet</p>
                      ) : (
                        <div className="space-y-4">
                          {trades.map((trade) => (
                            <div key={trade.id} className="flex items-center justify-between p-4 border rounded-lg">
                              <div>
                                <div className="flex items-center gap-2">
                                  <Badge variant={trade.side === 'BUY' ? 'default' : 'secondary'}>
                                    {trade.side}
                                  </Badge>
                                  <span className="font-medium">{trade.symbol}</span>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {formatDate(trade.entry_time)} • {trade.entry_signal}
                                </p>
                              </div>
                              <div className="text-right">
                                <p className={`font-medium ${(trade.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {trade.pnl !== null ? ((trade.pnl >= 0 ? '+' : '') + formatCurrency(trade.pnl)) : '-'}
                                </p>
                                {trade.exit_time && (
                                  <p className="text-sm text-muted-foreground">
                                    Exit: {trade.exit_reason}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </>
          )}
        </>
      )}
    </div>
  );
}
