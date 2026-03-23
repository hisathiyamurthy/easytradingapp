// Strategy Builder with Natural Language Preview.
import { useState } from 'react';
import { Wand2, ArrowRight, CheckCircle, Settings, Eye, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, Button, Badge } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ParsedStrategy {
  name: string;
  description: string;
  strategyType: string;
  parameters: Record<string, any>;
  entryConditions: string[];
  exitConditions: string[];
  validationErrors: string[];
  isValid: boolean;
}

const PLACEHOLDER_TEXT = "e.g., Buy when RSI crosses above 30 and sell when it crosses below 70";

export default function StrategyBuilder() {
  const [input, setInput] = useState('');
  const [parsedStrategy, setParsedStrategy] = useState<ParsedStrategy | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [strategyName, setStrategyName] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [saving, setSaving] = useState(false);
  
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

  const handleParse = async () => {
    const trimmedInput = input.trim();
    
    if (trimmedInput === PLACEHOLDER_TEXT) {
      alert('Please enter a custom strategy description instead of using the placeholder example.');
      return;
    }
    
    setLoading(true);
    setParsedStrategy(null);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/strategies/parse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ strategy_text: trimmedInput })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to parse strategy');
      }
      
      const data = await response.json();
      
      setParsedStrategy({
        name: data.name,
        description: data.description,
        strategyType: data.strategy_type,
        parameters: data.parameters,
        entryConditions: data.entry_conditions,
        exitConditions: data.exit_conditions,
        validationErrors: data.validation_errors,
        isValid: data.is_valid
      });
      setStrategyName(data.name || '');
    } catch (error: any) {
      console.error('Error parsing strategy:', error);
      alert(error.message || 'Failed to parse strategy. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveStrategy = async () => {
    if (!parsedStrategy || !parsedStrategy.isValid) {
      alert('Please parse a valid strategy first.');
      return;
    }

    if (!strategyName.trim()) {
      alert('Please enter a strategy name.');
      return;
    }

    setSaving(true);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/strategies`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          name: strategyName,
          description: parsedStrategy.description,
          strategy_type: parsedStrategy.strategyType,
          parameters: parsedStrategy.parameters,
          entry_conditions: parsedStrategy.entryConditions,
          exit_conditions: parsedStrategy.exitConditions,
          status: 'draft'
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save strategy');
      }
      
      const data = await response.json();
      alert(`Strategy "${strategyName}" saved successfully!`);
      
      // Reset state
      setInput('');
      setParsedStrategy(null);
      setStrategyName('');
      setShowPreview(false);
      
      // Redirect to strategy dashboard
      window.location.href = '/strategies';
    } catch (error: any) {
      console.error('Error saving strategy:', error);
      alert(error.message || 'Failed to save strategy. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const formatCondition = (condition: any): string => {
    if (typeof condition === 'string') return condition;
    if (typeof condition !== 'object' || condition === null) return String(condition);
    
    const indicator = condition.indicator || condition.signal || 'unknown';
    
    switch (indicator) {
      case 'ema_above_ema':
        return `EMA ${condition.period} above EMA ${condition.period2}`;
      case 'ema_crossover':
        return `EMA ${condition.period} crosses ${condition.operator === 'crosses_above' ? 'above' : 'below'} EMA ${condition.period2}`;
      case 'rsi':
        return `RSI(${condition.period || 14}) ${condition.operator === 'greater_than' ? '>' : condition.operator === 'less_than' ? '<' : condition.operator} ${condition.value}`;
      case 'macd_crossover':
        return `MACD crosses ${condition.operator === 'crosses_above' ? 'above' : 'below'} signal`;
      case 'sma':
        return `SMA(${condition.period}) ${condition.operator === 'greater_than' ? '>' : '<'} ${condition.value}`;
      default:
        return JSON.stringify(condition);
    }
  };
  
  const formatConditionGroup = (group: any): string => {
    if (!group || !group.conditions) return '';
    return group.conditions.map((c: any) => formatCondition(c)).join(` ${group.logic || 'AND'} `);
  };

  const getStrategyTypeColor = (type: string) => {
    switch (type) {
      case 'mean_reversion': return 'bg-purple-100 text-purple-800';
      case 'breakout': return 'bg-blue-100 text-blue-800';
      case 'momentum': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center gap-3">
        <Wand2 className="w-6 h-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Strategy Builder</h1>
          <p className="text-sm text-muted-foreground">Create strategies using natural language</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Describe Your Strategy</CardTitle>
              <CardDescription>Tell us what you want your strategy to do</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={PLACEHOLDER_TEXT}
                className="w-full h-40 p-4 border rounded-md resize-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              
              <Button
                onClick={handleParse}
                disabled={!input.trim() || loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4 mr-2" />
                    Generate Strategy
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {parsedStrategy && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Parsed Strategy</CardTitle>
                </div>
                <div className="flex gap-2">
                  {isAdmin && (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={async () => {
                        if (!strategyName.trim()) {
                          alert('Please enter a strategy name');
                          return;
                        }
                        setSaving(true);
                        try {
                          const token = localStorage.getItem('token');
                          const response = await fetch(`${API_URL}/api/v1/strategies`, {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                              ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                            },
                            body: JSON.stringify({
                              name: strategyName,
                              description: parsedStrategy.description,
                              strategy_type: 'custom',
                              parameters: parsedStrategy.parameters
                            })
                          });
                          
                          if (!response.ok) {
                            const error = await response.json();
                            throw new Error(error.detail || 'Failed to save strategy');
                          }
                          
                          alert('Strategy saved successfully!');
                        } catch (error: any) {
                          console.error('Error saving strategy:', error);
                          alert(error.message || 'Failed to save strategy');
                        } finally {
                          setSaving(false);
                        }
                      }}
                      disabled={saving}
                    >
                      {saving ? 'Saving...' : 'Save Strategy'}
                    </Button>
                  )}
                  {!isAdmin && parsedStrategy && (
                    <p className="text-xs text-muted-foreground">Admin can save strategies</p>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowPreview(!showPreview)}
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    {showPreview ? 'Hide Preview' : 'Show Preview'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Strategy Name</p>
                  {isEditingName ? (
                    <div className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={strategyName}
                        onChange={(e) => setStrategyName(e.target.value)}
                        className="flex-1 p-2 border rounded text-sm"
                        placeholder="Enter strategy name"
                      />
                      <Button size="sm" onClick={() => {
                        setIsEditingName(false);
                        setParsedStrategy(prev => prev ? { ...prev, name: strategyName } : null);
                      }}>
                        Save
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mt-1">
                      <p className="font-medium">{parsedStrategy.name}</p>
                      {isAdmin && (
                        <Button variant="ghost" size="sm" onClick={() => setIsEditingName(true)}>
                          <Settings className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-sm text-muted-foreground">Type</p>
                  <Badge className={getStrategyTypeColor(parsedStrategy.strategyType)}>
                    {parsedStrategy.strategyType}
                  </Badge>
                </div>

                {parsedStrategy.entryConditions && parsedStrategy.entryConditions.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <ArrowRight className="w-4 h-4" /> Entry Conditions
                    </p>
                    <ul className="mt-1 space-y-1">
                      {parsedStrategy.entryConditions.map((group: any, idx: number) => (
                        <li key={idx} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          {group.logic && group.conditions 
                            ? formatConditionGroup(group) 
                            : formatCondition(group)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {parsedStrategy.exitConditions && parsedStrategy.exitConditions.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <ArrowRight className="w-4 h-4 rotate-180" /> Exit Conditions
                    </p>
                    <ul className="mt-1 space-y-1">
                      {parsedStrategy.exitConditions.map((group: any, idx: number) => (
                        <li key={idx} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-red-600" />
                          {group.logic && group.conditions 
                            ? formatConditionGroup(group) 
                            : formatCondition(group)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {showPreview && parsedStrategy && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Parameters
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(parsedStrategy.parameters).map(([key, value]) => (
                  <div key={key}>
                    <label className="block text-sm font-medium mb-1">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </label>
                    <input
                      type={typeof value === 'number' ? 'number' : 'text'}
                      defaultValue={String(value)}
                      className="w-full px-3 py-2 border rounded-md"
                    />
                  </div>
                ))}
                <Button 
                  className="w-full" 
                  onClick={handleSaveStrategy}
                  disabled={saving || !parsedStrategy?.isValid}
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Strategy'
                  )}
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="pt-4">
                <h3 className="font-semibold text-blue-900 mb-2">Tips</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Use specific numbers for better accuracy</li>
                  <li>• Mention entry and exit conditions separately</li>
                  <li>• Include stop loss and take profit levels</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
