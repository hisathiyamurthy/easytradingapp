import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Play, Pause, Square, RefreshCw, TrendingUp, TrendingDown,
  Loader2, Plus, Plug, PlugZap, Wallet, AlertCircle, CheckCircle2,
  BarChart3, ArrowRightLeft, AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Tabs, TabsContent, TabsList, TabsTrigger, Input, Label } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface BrokerConnection {
  broker: string;
  connected: boolean;
  connected_at?: string;
  api_key?: string;
}

interface LiveBalance {
  available_cash: number;
  collateral: number;
  margin_used: number;
  total_value: number;
  unrealized_pnl: number;
}

interface LiveInstance {
  id: string;
  strategy_id: string;
  strategy_name: string;
  symbol: string;
  exchange: string;
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
  ltp: number;
  unrealized_pnl: number;
  is_open: boolean;
  opened_at: string;
  broker_order_id?: string;
}

interface Trade {
  id: string;
  symbol: string;
  exchange: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  price: number;
  pnl: number | null;
  commission: number;
  entry_time: string;
  exit_time: string | null;
  entry_signal: string;
  exit_reason: string | null;
  broker_order_id?: string;
  status: string;
}

export default function LiveTrading() {
  const navigate = useNavigate();
  
  const [connection, setConnection] = useState<BrokerConnection | null>(null);
  const [balance, setBalance] = useState<LiveBalance | null>(null);
  const [instances, setInstances] = useState<LiveInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<LiveInstance | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState('MOCK');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [totp, setTotp] = useState('');

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  const fetchConnectionStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/live-trading/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setConnection(data);
      }
    } catch (error) {
      console.error('Error fetching connection status:', error);
    }
  }, []);

  const fetchBalance = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/live-trading/balance`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        setBalance(await response.json());
      }
    } catch (error) {
      console.error('Error fetching balance:', error);
    }
  }, []);

  const fetchInstances = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/live-trading/instances`, {
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
        fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/positions`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/trades?limit=50`, {
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
    fetchConnectionStatus();
    fetchInstances();
  }, [fetchConnectionStatus, fetchInstances]);

  useEffect(() => {
    if (selectedInstance) {
      fetchInstanceDetails(selectedInstance.id);
    }
  }, [selectedInstance, fetchInstanceDetails]);

  useEffect(() => {
    if (connection?.connected) {
      fetchBalance();
    }
  }, [connection, fetchBalance]);

  const handleConnect = async () => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      const body: any = {
        broker: selectedBroker,
        api_key: apiKey,
        api_secret: apiSecret,
      };
      if (totp) body.totp = totp;
      
      const response = await fetch(`${API_URL}/api/v1/live-trading/connect`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      
      if (response.ok) {
        await fetchConnectionStatus();
        await fetchBalance();
        setConnectModalOpen(false);
        setApiKey('');
        setApiSecret('');
        setTotp('');
      } else {
        const error = await response.json();
        console.error('Connect error:', error);
      }
    } catch (error) {
      console.error('Error connecting:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/live-trading/disconnect`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchConnectionStatus();
      setBalance(null);
    } catch (error) {
      console.error('Error disconnecting:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async (instanceId: string) => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error starting instance:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async (instanceId: string) => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/pause`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error pausing:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async (instanceId: string) => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/resume`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error resuming:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async (instanceId: string) => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/stop`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchInstances();
    } catch (error) {
      console.error('Error stopping:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExitAll = async (instanceId: string) => {
    const confirmMsg = 'EMERGENCY: This will close ALL open positions immediately at market price. Are you sure?';
    const confirm2 = `Type "EXIT ALL" to confirm:`;
    
    const response = prompt(`${confirmMsg}\n\n${confirm2}`);
    if (response !== 'EXIT ALL') {
      alert('Exit All cancelled.');
      return;
    }
    
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token');
      const result = await fetch(`${API_URL}/api/v1/live-trading/instances/${instanceId}/exit-all`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      
      const data = await result.json();
      
      if (data.success) {
        alert(`Emergency Exit Complete!\nClosed ${data.closed_positions?.length || 0} positions.`);
        await fetchPositions(instanceId);
        await fetchTrades(instanceId);
      } else {
        alert(`Exit All Failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error exiting all:', error);
      alert('Error executing Exit All. Check console for details.');
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
          <h1 className="text-2xl font-bold">Live Trading</h1>
          <p className="text-muted-foreground">Trade with real money on your broker account</p>
        </div>
        {!connection?.connected ? (
          <Button onClick={() => setConnectModalOpen(true)} className="bg-green-600 hover:bg-green-700">
            <PlugZap className="w-4 h-4 mr-2" />
            Connect Broker
          </Button>
        ) : (
          <div className="flex items-center gap-4">
            <Badge className="bg-green-100 text-green-800">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              {connection.broker} Connected
            </Badge>
            <Button variant="outline" onClick={handleDisconnect} disabled={actionLoading}>
              Disconnect
            </Button>
          </div>
        )}
      </div>

      {/* Connection Modal */}
      {connectModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Connect to Broker</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Broker</Label>
                <select 
                  className="w-full mt-1 p-2 border rounded-md"
                  value={selectedBroker}
                  onChange={(e) => setSelectedBroker(e.target.value)}
                >
                  <option value="MOCK">Mock Broker (Testing)</option>
                  <option value="ZERODHA">Zerodha</option>
                  <option value="UPSTOX">Upstox</option>
                  <option value="KOTAK_NEO">Kotak Neo</option>
                </select>
              </div>
              
              {selectedBroker === 'MOCK' ? (
                <>
                  <div>
                    <Label>API Key</Label>
                    <Input 
                      value={apiKey} 
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter mock API key"
                    />
                  </div>
                  <div>
                    <Label>API Secret</Label>
                    <Input 
                      type="password"
                      value={apiSecret} 
                      onChange={(e) => setApiSecret(e.target.value)}
                      placeholder="Enter mock API secret"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
                    <p className="text-sm text-yellow-800">
                      For {selectedBroker}, you need to generate API keys from their developer portal. 
                      API integration will be available once you provide valid credentials.
                    </p>
                  </div>
                  <div>
                    <Label>API Key</Label>
                    <Input 
                      value={apiKey} 
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter your API key"
                    />
                  </div>
                  <div>
                    <Label>API Secret</Label>
                    <Input 
                      type="password"
                      value={apiSecret} 
                      onChange={(e) => setApiSecret(e.target.value)}
                      placeholder="Enter your API secret"
                    />
                  </div>
                  <div>
                    <Label>TOTP Secret (Optional)</Label>
                    <Input 
                      value={totp} 
                      onChange={(e) => setTotp(e.target.value)}
                      placeholder="Enter TOTP secret for 2FA"
                    />
                  </div>
                </>
              )}
              
              <div className="flex gap-2 pt-4">
                <Button onClick={handleConnect} disabled={actionLoading || !apiKey || !apiSecret}>
                  {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plug className="w-4 h-4 mr-2" />}
                  Connect
                </Button>
                <Button variant="outline" onClick={() => setConnectModalOpen(false)}>
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Not Connected State */}
      {!connection?.connected ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Plug className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium">Connect Your Broker</h3>
            <p className="text-gray-500 mt-1">
              Connect a broker account to start live trading with your strategies
            </p>
            <Button className="mt-4 bg-green-600 hover:bg-green-700" onClick={() => setConnectModalOpen(true)}>
              <PlugZap className="w-4 h-4 mr-2" />
              Connect Broker
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Balance & Connection Stats */}
          {balance && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Available Cash</p>
                      <p className="text-2xl font-bold">{formatCurrency(balance.available_cash)}</p>
                    </div>
                    <Wallet className="h-8 w-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Value</p>
                      <p className="text-2xl font-bold">{formatCurrency(balance.total_value)}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Margin Used</p>
                      <p className="text-2xl font-bold">{formatCurrency(balance.margin_used)}</p>
                    </div>
                    <ArrowRightLeft className="h-8 w-8 text-orange-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Unrealized P&L</p>
                      <p className={`text-2xl font-bold ${balance.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {balance.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(balance.unrealized_pnl)}
                      </p>
                    </div>
                    {balance.unrealized_pnl >= 0 ? (
                      <TrendingUp className="h-8 w-8 text-green-500" />
                    ) : (
                      <TrendingDown className="h-8 w-8 text-red-500" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Instance Selector */}
          {instances.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <BarChart3 className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium">No Live Trading Instances</h3>
                <p className="text-gray-500 mt-1">
                  Backtest and validate a strategy before starting live trading
                </p>
                <Button className="mt-4" onClick={() => navigate('/strategies')}>
                  Go to Strategies
                </Button>
              </CardContent>
            </Card>
          ) : (
            <>
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
                    <div className="text-sm font-medium">{inst.strategy_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {inst.symbol} • {inst.status}
                    </div>
                  </button>
                ))}
              </div>

              {selectedInstance && (
                <>
                  {/* Instance Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-muted-foreground">Capital</p>
                            <p className="text-2xl font-bold">{formatCurrency(selectedInstance.capital)}</p>
                          </div>
                          <Wallet className="h-8 w-8 text-blue-500" />
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

                  {/* Instance Actions */}
                  <div className="flex gap-2">
                    {selectedInstance.status === 'pending' && (
                      <Button onClick={() => handleStart(selectedInstance.id)} disabled={actionLoading}>
                        <Play className="w-4 h-4 mr-2" />
                        Start
                      </Button>
                    )}
                    {selectedInstance.status === 'running' && (
                      <>
                        <Button variant="outline" onClick={() => handlePause(selectedInstance.id)} disabled={actionLoading}>
                          <Pause className="w-4 h-4 mr-2" />
                          Pause
                        </Button>
                        <Button variant="destructive" onClick={() => handleStop(selectedInstance.id)} disabled={actionLoading}>
                          <Square className="w-4 h-4 mr-2" />
                          Stop
                        </Button>
                        <Button 
                          variant="destructive" 
                          className="bg-red-700 hover:bg-red-800 animate-pulse"
                          onClick={() => handleExitAll(selectedInstance.id)} 
                          disabled={actionLoading}
                        >
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          EXIT ALL
                        </Button>
                      </>
                    )}
                    {selectedInstance.status === 'paused' && (
                      <>
                        <Button onClick={() => handleResume(selectedInstance.id)} disabled={actionLoading}>
                          <Play className="w-4 h-4 mr-2" />
                          Resume
                        </Button>
                        <Button variant="destructive" onClick={() => handleStop(selectedInstance.id)} disabled={actionLoading}>
                          <Square className="w-4 h-4 mr-2" />
                          Stop
                        </Button>
                      </>
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
                                      <span className="text-sm text-muted-foreground">{pos.exchange}</span>
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                      Qty: {pos.quantity} @ {formatCurrency(pos.entry_price)}
                                    </p>
                                    {pos.broker_order_id && (
                                      <p className="text-xs text-muted-foreground">
                                        Order ID: {pos.broker_order_id}
                                      </p>
                                    )}
                                  </div>
                                  <div className="text-right">
                                    <p className={`font-medium ${pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {pos.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(pos.unrealized_pnl)}
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                      LTP: {formatCurrency(pos.ltp || pos.current_price)}
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
                                      <Badge variant="outline" className="text-xs">
                                        {trade.status}
                                      </Badge>
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                      {formatDate(trade.entry_time)} • {trade.entry_signal}
                                    </p>
                                    {trade.broker_order_id && (
                                      <p className="text-xs text-muted-foreground">
                                        Order ID: {trade.broker_order_id}
                                      </p>
                                    )}
                                  </div>
                                  <div className="text-right">
                                    <p className={`font-medium ${(trade.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {trade.pnl !== null ? ((trade.pnl >= 0 ? '+' : '') + formatCurrency(trade.pnl)) : '-'}
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                      Price: {formatCurrency(trade.price || trade.entry_price)}
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
        </>
      )}
    </div>
  );
}
