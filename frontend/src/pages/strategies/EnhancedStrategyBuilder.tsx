import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
  Wand2, Loader2, Save, Play, CheckCircle, XCircle, AlertTriangle, 
  ChevronRight, ArrowRight, Eye, Settings, RefreshCw, Clock, Check, X,
  BarChart3, TrendingUp, TrendingDown, Pause, PlayCircle, StopCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, Button, Badge, Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui';
import { parseStrategy, validateStrategy, getLifecycle, transitionStrategy, runBacktest, getStateColor, LIFECYCLE_STATES } from '@/services/strategyLifecycleApi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const PLACEHOLDER_TEXT = "e.g., Buy when RSI crosses above 30 and sell when RSI crosses below 70. Use 2% stoploss and 5% target.";

const LIFECYCLE_STEPS = [
  { key: 'DRAFT', label: 'Draft', icon: Clock },
  { key: 'validated', label: 'Validated', icon: CheckCircle },
  { key: 'backtested', label: 'Backtested', icon: BarChart3 },
  { key: 'paper_trading', label: 'Paper Trading', icon: PlayCircle },
  { key: 'live', label: 'Live', icon: TrendingUp },
];

interface ParsedStrategy {
  name: string;
  description: string;
  strategy_type: string;
  parameters: Record<string, any>;
  entry_conditions: any[];
  exit_conditions: any[];
  validation_errors: string[];
  is_valid: boolean;
}

interface BacktestResult {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_return: number;
  total_return_pct: number;
  max_drawdown: number;
  sharpe_ratio: number;
  trades: any[];
}

export default function StrategyBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditMode = !!id;
  
  const [input, setInput] = useState('');
  const [parsedStrategy, setParsedStrategy] = useState<ParsedStrategy | null>(null);
  const [strategyName, setStrategyName] = useState('');
  const [strategyType, setStrategyType] = useState('MOMENTUM');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [activeTab, setActiveTab] = useState('create');
  
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<any>(null);
  const [validation, setValidation] = useState<any>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [backtesting, setBacktesting] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null);

  const getUserRole = () => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        return user.role?.toLowerCase() || '';
      } catch {
        return '';
      }
    }
    return '';
  };
  
  const isAdmin = getUserRole() === 'admin';

  const fetchLifecycle = useCallback(async (sid: string) => {
    try {
      const data = await getLifecycle(sid);
      setLifecycle(data);
    } catch (error) {
      console.error('Error fetching lifecycle:', error);
    }
  }, []);

  const fetchValidation = useCallback(async (sid: string) => {
    try {
      const data = await validateStrategy(sid);
      setValidation(data);
    } catch (error) {
      console.error('Error validating:', error);
    }
  }, []);

  useEffect(() => {
    if (strategyId) {
      fetchLifecycle(strategyId);
      fetchValidation(strategyId);
    }
  }, [strategyId, fetchLifecycle, fetchValidation]);

  useEffect(() => {
    if (isEditMode && id) {
      loadStrategy(id);
    }
  }, [isEditMode, id]);

  const loadStrategy = async (strategyId: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setStrategyId(strategyId);
        if (data.parameters?.entry_conditions) {
          setParsedStrategy({
            name: data.name,
            description: data.description,
            strategy_type: data.strategy_type,
            parameters: data.parameters,
            entry_conditions: data.parameters.entry_conditions,
            exit_conditions: data.parameters.exit_conditions,
            validation_errors: [],
            is_valid: true,
          });
        }
      }
    } catch (error) {
      console.error('Error loading strategy:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || trimmedInput === PLACEHOLDER_TEXT) {
      setNotification({ type: 'error', message: 'Please enter a strategy description' });
      return;
    }
    
    setLoading(true);
    try {
      const result = await parseStrategy(trimmedInput);
      setParsedStrategy(result);
      setInput(trimmedInput);
      // Auto-set name from parsed result
      if (result.name && !strategyName) {
        setStrategyName(result.name);
      }
      if (result.strategy_type && !strategyType) {
        setStrategyType(result.strategy_type.toUpperCase());
      }
    } catch (error: any) {
      setNotification({ type: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!parsedStrategy && !input) {
      setNotification({ type: 'error', message: 'Please parse a strategy first' });
      return;
    }
    
    if (!strategyName.trim()) {
      setNotification({ type: 'error', message: 'Please enter a strategy name' });
      return;
    }
    
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const url = isEditMode && id 
        ? `${API_URL}/api/v1/strategies/${id}`
        : `${API_URL}/api/v1/strategies`;
      const method = isEditMode && id ? 'PUT' : 'POST';
      
      // Build parameters with editable name and type
      const params = {
        ...parsedStrategy?.parameters,
        symbol: parsedStrategy?.parameters?.symbol || 'UNKNOWN',
        exchange: parsedStrategy?.parameters?.exchange || 'NSE',
        timeframe: parsedStrategy?.parameters?.timeframe || 'daily',
        entry_conditions: parsedStrategy?.entry_conditions || [],
        exit_conditions: parsedStrategy?.exit_conditions || [],
      };
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: strategyName,
          description: parsedStrategy?.description || `Strategy: ${strategyName}`,
          strategy_type: strategyType,
          parameters: params,
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save strategy');
      }
      
      const data = await response.json();
      if (!strategyId) {
        setStrategyId(data.id);
        navigate(`/strategies/${data.id}`, { replace: true });
      }
      setNotification({ type: 'success', message: 'Strategy saved successfully!' });
      await fetchLifecycle(data.id);
    } catch (error: any) {
      setNotification({ type: 'error', message: error.message });
    } finally {
      setSaving(false);
    }
  };

  const handleValidate = async () => {
    // Validate can work with parsed strategy even without saving
    if (!parsedStrategy && !strategyId) {
      setNotification({ type: 'error', message: 'Please parse a strategy first' });
      return;
    }
    
    setValidating(true);
    try {
      // If we have a strategy ID, validate via API
      if (strategyId) {
        await fetchValidation(strategyId);
        setNotification({ type: 'success', message: 'Strategy validated!' });
      } else {
        // Validate parsed strategy locally
        const errors: string[] = [];
        if (!parsedStrategy?.entry_conditions?.length) {
          errors.push('No entry conditions defined');
        }
        if (!parsedStrategy?.parameters?.symbol || parsedStrategy?.parameters?.symbol === 'UNKNOWN') {
          errors.push('No trading symbol specified');
        }
        if (errors.length === 0) {
          setNotification({ type: 'success', message: 'Strategy looks valid! Save to continue.' });
        } else {
          setNotification({ type: 'error', message: errors.join(', ') });
        }
      }
    } catch (error: any) {
      setNotification({ type: 'error', message: error.message });
    } finally {
      setValidating(false);
    }
  };

  const handleRunBacktest = async () => {
    if (!input) {
      setNotification({ type: 'error', message: 'Enter strategy text first' });
      return;
    }
    
    setBacktesting(true);
    try {
      const result = await runBacktest(input);
      setBacktestResult(result.backtest);
      setNotification({ type: 'success', message: 'Backtest completed!' });
    } catch (error: any) {
      setNotification({ type: 'error', message: error.message });
    } finally {
      setBacktesting(false);
    }
  };

  const handleTransition = async (targetState: string) => {
    if (!strategyId) {
      setNotification({ type: 'error', message: 'Save strategy first' });
      return;
    }
    
    setTransitioning(true);
    try {
      const result = await transitionStrategy(strategyId, targetState);
      if (result.success) {
        setNotification({ type: 'success', message: `Transitioned to ${targetState}` });
        await fetchLifecycle(strategyId);
        await fetchValidation(strategyId);
      } else {
        setNotification({ 
          type: 'error', 
          message: `${result.message}\nMissing: ${result.requirements_missing?.join(', ')}` 
        });
      }
    } catch (error: any) {
      setNotification({ type: 'error', message: error.message });
    } finally {
      setTransitioning(false);
    }
  };

  const formatCondition = (condition: any): string => {
    if (!condition || typeof condition !== 'object') return String(condition);
    const indicator = condition.indicator || condition.signal || '';
    const op = condition.operator?.replace(/_/g, ' ') || '';
    const value = condition.value || '';
    const period = condition.period ? `(${condition.period})` : '';
    return `${indicator}${period} ${op} ${value}`.trim();
  };

  const getCurrentStepIndex = () => {
    if (!lifecycle) return 0;
    return LIFECYCLE_STEPS.findIndex(s => s.key === lifecycle.current_state);
  };

  const formatNumber = (num: number, decimals = 2) => {
    return new Intl.NumberFormat('en-IN', { 
      minimumFractionDigits: decimals, 
      maximumFractionDigits: decimals 
    }).format(num);
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {notification && (
        <div className={`fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg ${
          notification.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
            <span>{notification.message}</span>
            <button onClick={() => setNotification(null)} className="ml-2">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Wand2 className="w-6 h-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">
            {isEditMode ? 'Edit Strategy' : 'Strategy Builder'}
          </h1>
          <p className="text-sm text-muted-foreground">
            Create and manage your trading strategies with lifecycle workflow
          </p>
        </div>
        {lifecycle && (
          <Badge className={`ml-auto ${getStateColor(lifecycle.current_state)}`}>
            {LIFECYCLE_STATES[lifecycle.current_state as keyof typeof LIFECYCLE_STATES]?.label || lifecycle.current_state}
          </Badge>
        )}
      </div>

      {lifecycle && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              {LIFECYCLE_STEPS.map((step, index) => {
                const currentIndex = getCurrentStepIndex();
                const isCompleted = index < currentIndex;
                const isCurrent = index === currentIndex;
                const isClickable = isAdmin || isCompleted;
                const Icon = step.icon;
                
                return (
                  <div key={step.key} className="flex items-center">
                    <button
                      onClick={() => isClickable && handleTransition(step.key)}
                      disabled={!isClickable || transitioning}
                      className={`flex flex-col items-center p-3 rounded-lg transition-all ${
                        isCurrent ? 'bg-primary/10 border-2 border-primary' :
                        isCompleted ? 'bg-green-50 hover:bg-green-100 cursor-pointer' :
                        'bg-gray-50 opacity-50'
                      }`}
                    >
                      <Icon className={`w-5 h-5 ${
                        isCurrent ? 'text-primary' : isCompleted ? 'text-green-600' : 'text-gray-400'
                      }`} />
                      <span className={`text-xs mt-1 font-medium ${
                        isCurrent ? 'text-primary' : isCompleted ? 'text-green-700' : 'text-gray-500'
                      }`}>{step.label}</span>
                    </button>
                    {index < LIFECYCLE_STEPS.length - 1 && (
                      <ChevronRight className={`w-5 h-5 mx-2 ${
                        isCompleted ? 'text-green-600' : 'text-gray-300'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>
            
            {lifecycle.requirements && Object.keys(lifecycle.requirements).length > 0 && (
              <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                <p className="text-sm font-medium text-yellow-800 mb-2">Requirements for next steps:</p>
                {Object.entries(lifecycle.requirements).map(([state, reqs]: [string, any]) => (
                  <div key={state} className="text-xs text-yellow-700">
                    <span className="font-semibold">{LIFECYCLE_STATES[state as keyof typeof LIFECYCLE_STATES]?.label}:</span>
                    <ul className="ml-4 list-disc">
                      {(reqs as string[]).map((req, i) => <li key={i}>{req}</li>)}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="create">Create</TabsTrigger>
          <TabsTrigger value="validate">Validate</TabsTrigger>
          <TabsTrigger value="backtest">Backtest</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>

        <TabsContent value="create">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Describe Your Strategy</CardTitle>
                <CardDescription>Tell us what you want in plain English</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={PLACEHOLDER_TEXT}
                  className="w-full h-40 p-4 border rounded-md resize-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
                
                <div className="flex gap-2">
                  <Button onClick={handleParse} disabled={!input.trim() || loading} className="flex-1">
                    {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating... </> : <><Wand2 className="w-4 h-4 mr-2" /> Generate Strategy</>}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Strategy Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground">Name</label>
                  <input
                    type="text"
                    value={strategyName}
                    onChange={(e) => setStrategyName(e.target.value)}
                    placeholder="My Trading Strategy"
                    className="w-full mt-1 p-2 border rounded-md focus:ring-2 focus:ring-primary"
                  />
                </div>
                
                <div>
                  <label className="text-sm text-muted-foreground">Type</label>
                  <select
                    value={strategyType}
                    onChange={(e) => setStrategyType(e.target.value)}
                    className="w-full mt-1 p-2 border rounded-md focus:ring-2 focus:ring-primary"
                  >
                    <option value="MOMENTUM">Momentum</option>
                    <option value="MEAN_REVERSION">Mean Reversion</option>
                    <option value="BREAKOUT">Breakout</option>
                    <option value="GRID">Grid Trading</option>
                    <option value="DCA">Dollar Cost Averaging</option>
                    <option value="CUSTOM">Custom</option>
                  </select>
                </div>
                
                <Button onClick={handleSave} disabled={!parsedStrategy && !input || saving || !strategyName.trim()} className="w-full">
                  {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving... </> : <><Save className="w-4 h-4 mr-2" /> Save Strategy</>}
                </Button>
              </CardContent>
            </Card>

            {parsedStrategy && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Generated Strategy</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Symbol</p>
                      <p className="font-medium">{parsedStrategy.parameters?.symbol || 'Not specified'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Exchange</p>
                      <p className="font-medium">{parsedStrategy.parameters?.exchange || 'NSE'}</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <ArrowRight className="w-4 h-4 text-green-600" /> Entry Conditions
                    </p>
                    {parsedStrategy.entry_conditions?.map((group: any, idx: number) => (
                      <div key={idx} className="mt-1 p-2 bg-green-50 rounded text-sm">
                        {group.conditions?.map((c: any, i: number) => (
                          <span key={i}>{i > 0 && <span className="font-bold mx-1">{group.logic}</span>}{formatCondition(c)}</span>
                        ))}
                      </div>
                    ))}
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <ArrowRight className="w-4 h-4 text-red-600 rotate-180" /> Exit Conditions
                    </p>
                    {parsedStrategy.exit_conditions?.map((group: any, idx: number) => (
                      <div key={idx} className="mt-1 p-2 bg-red-50 rounded text-sm">
                        {group.conditions?.map((c: any, i: number) => (
                          <span key={i}>{i > 0 && <span className="font-bold mx-1">{group.logic}</span>}{formatCondition(c)}</span>
                        ))}
                      </div>
                    ))}
                  </div>

                  {parsedStrategy.validation_errors?.length > 0 && (
                    <div className="p-3 bg-red-50 rounded-lg">
                      <p className="text-sm font-medium text-red-800">Errors</p>
                      {parsedStrategy.validation_errors.map((err, i) => (
                        <p key={i} className="text-xs text-red-600">• {err}</p>
                      ))}
                    </div>
                  )}

                  {parsedStrategy.is_valid && (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-sm font-medium">Strategy is valid</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="validate">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Validation</CardTitle>
              <CardDescription>Validate your strategy before running backtests</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={handleValidate} disabled={!parsedStrategy && !strategyId || loading} className="w-full">
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                Validate Strategy
              </Button>

              {validation && (
                <>
                  <div className={`p-4 rounded-lg ${validation.is_valid ? 'bg-green-100' : 'bg-red-100'}`}>
                    <div className="flex items-center gap-2">
                      {validation.is_valid ? (
                        <CheckCircle className="w-6 h-6 text-green-600" />
                      ) : (
                        <XCircle className="w-6 h-6 text-red-600" />
                      )}
                      <span className={`font-medium ${validation.is_valid ? 'text-green-800' : 'text-red-800'}`}>
                        {validation.is_valid ? 'Strategy is Valid' : 'Strategy has Errors'}
                      </span>
                    </div>
                  </div>

                  {validation.errors?.length > 0 && (
                    <div className="p-4 bg-red-50 rounded-lg">
                      <p className="font-medium text-red-800 mb-2">Errors</p>
                      {validation.errors.map((err: string, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-red-700 text-sm mb-1">
                          <XCircle className="w-4 h-4" /> {err}
                        </div>
                      ))}
                    </div>
                  )}

                  {validation.warnings?.length > 0 && (
                    <div className="p-4 bg-yellow-50 rounded-lg">
                      <p className="font-medium text-yellow-800 mb-2">Warnings</p>
                      {validation.warnings.map((warn: string, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-yellow-700 text-sm mb-1">
                          <AlertTriangle className="w-4 h-4" /> {warn}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-4">
                    <div className={`p-4 rounded-lg text-center ${validation.can_run_backtest ? 'bg-green-50' : 'bg-gray-50'}`}>
                      <BarChart3 className={`w-6 h-6 mx-auto mb-2 ${validation.can_run_backtest ? 'text-green-600' : 'text-gray-400'}`} />
                      <p className="text-sm font-medium">Backtest</p>
                      <p className="text-xs text-muted-foreground">{validation.can_run_backtest ? 'Ready' : 'Not Ready'}</p>
                    </div>
                    <div className={`p-4 rounded-lg text-center ${validation.can_start_paper_trading ? 'bg-yellow-50' : 'bg-gray-50'}`}>
                      <PlayCircle className={`w-6 h-6 mx-auto mb-2 ${validation.can_start_paper_trading ? 'text-yellow-600' : 'text-gray-400'}`} />
                      <p className="text-sm font-medium">Paper Trading</p>
                      <p className="text-xs text-muted-foreground">{validation.can_start_paper_trading ? 'Ready' : 'Not Ready'}</p>
                    </div>
                    <div className={`p-4 rounded-lg text-center ${validation.can_start_live ? 'bg-green-50' : 'bg-gray-50'}`}>
                      <TrendingUp className={`w-6 h-6 mx-auto mb-2 ${validation.can_start_live ? 'text-green-600' : 'text-gray-400'}`} />
                      <p className="text-sm font-medium">Go Live</p>
                      <p className="text-xs text-muted-foreground">{validation.can_start_live ? 'Ready' : 'Not Ready'}</p>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="backtest">
          <Card>
            <CardHeader>
              <CardTitle>Backtesting</CardTitle>
              <CardDescription>Run backtest to see historical performance</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={handleRunBacktest} disabled={!input || backtesting} className="w-full">
                {backtesting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <BarChart3 className="w-4 h-4 mr-2" />}
                {backtesting ? 'Running Backtest...' : 'Run Backtest'}
              </Button>

              {backtestResult && (
                <>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg text-center">
                      <p className="text-2xl font-bold text-blue-700">{backtestResult.total_trades}</p>
                      <p className="text-sm text-muted-foreground">Total Trades</p>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg text-center">
                      <p className="text-2xl font-bold text-green-700">{formatNumber(backtestResult.win_rate)}%</p>
                      <p className="text-sm text-muted-foreground">Win Rate</p>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg text-center">
                      <p className={`text-2xl font-bold ${backtestResult.total_return >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                        {backtestResult.total_return >= 0 ? '+' : ''}{formatNumber(backtestResult.total_return_pct)}%
                      </p>
                      <p className="text-sm text-muted-foreground">Total Return</p>
                    </div>
                    <div className="p-4 bg-red-50 rounded-lg text-center">
                      <p className="text-2xl font-bold text-red-700">{formatNumber(backtestResult.max_drawdown)}%</p>
                      <p className="text-sm text-muted-foreground">Max Drawdown</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-green-50 rounded-lg text-center">
                      <p className="text-xl font-bold text-green-700">{backtestResult.winning_trades}</p>
                      <p className="text-sm text-muted-foreground">Winning Trades</p>
                    </div>
                    <div className="p-4 bg-red-50 rounded-lg text-center">
                      <p className="text-xl font-bold text-red-700">{backtestResult.losing_trades}</p>
                      <p className="text-sm text-muted-foreground">Losing Trades</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg text-center">
                      <p className="text-lg font-bold">{formatNumber(backtestResult.sharpe_ratio)}</p>
                      <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg text-center">
                      <p className="text-lg font-bold">{formatNumber(backtestResult.profit_factor || 0)}</p>
                      <p className="text-sm text-muted-foreground">Profit Factor</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg text-center">
                      <p className="text-lg font-bold">₹{formatNumber(backtestResult.total_return)}</p>
                      <p className="text-sm text-muted-foreground">Total P&L</p>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preview">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Preview</CardTitle>
              <CardDescription>Review and adjust parameters</CardDescription>
            </CardHeader>
            <CardContent>
              {parsedStrategy?.parameters && (
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(parsedStrategy.parameters).map(([key, value]) => (
                    <div key={key} className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </p>
                      <p className="font-medium">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
