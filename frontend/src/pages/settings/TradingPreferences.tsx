import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { Button } from '@/components/ui';
import { Input } from '@/components/ui';
import { Label } from '@/components/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui';
import { Switch } from '@/components/ui';
import { CreditCard, Save, Loader2, Clock, DollarSign, TrendingUp } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface TradingPreferences {
  defaultOrderType: string;
  defaultProductType: string;
  defaultTimeframe: string;
  defaultQuantity: number;
  autoConfirmOrders: boolean;
  showConfirmDialog: boolean;
  defaultSL: number;
  defaultTarget: number;
  riskPerTrade: number;
}

export default function TradingPreferences() {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  
  const [prefs, setPrefs] = useState<TradingPreferences>({
    defaultOrderType: 'market',
    defaultProductType: 'MIS',
    defaultTimeframe: '5min',
    defaultQuantity: 1,
    autoConfirmOrders: false,
    showConfirmDialog: true,
    defaultSL: 2,
    defaultTarget: 5,
    riskPerTrade: 1,
  });

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    
    // Save to localStorage for now (backend storage not implemented)
    try {
      localStorage.setItem('trading_preferences', JSON.stringify(prefs));
      setMessage({ type: 'success', text: 'Trading preferences saved!' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save preferences' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold">Trading Preferences</h1>
        <p className="text-gray-500 mt-1">Configure your default trading settings</p>
      </div>

      {/* Default Order Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Default Order Settings
          </CardTitle>
          <CardDescription>Set defaults for new orders</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Default Order Type</Label>
              <Select 
                value={prefs.defaultOrderType} 
                onValueChange={(v) => setPrefs({ ...prefs, defaultOrderType: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="market">Market</SelectItem>
                  <SelectItem value="limit">Limit</SelectItem>
                  <SelectItem value="stop_loss">Stop Loss</SelectItem>
                  <SelectItem value="stop_loss_limit">Stop Loss Limit</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Default Product Type</Label>
              <Select 
                value={prefs.defaultProductType} 
                onValueChange={(v) => setPrefs({ ...prefs, defaultProductType: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MIS">MIS (Intraday)</SelectItem>
                  <SelectItem value="CNC">CNC (Delivery)</SelectItem>
                  <SelectItem value="NRML">NRML (Overnight)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Default Timeframe</Label>
              <Select 
                value={prefs.defaultTimeframe} 
                onValueChange={(v) => setPrefs({ ...prefs, defaultTimeframe: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1min">1 Minute</SelectItem>
                  <SelectItem value="5min">5 Minutes</SelectItem>
                  <SelectItem value="15min">15 Minutes</SelectItem>
                  <SelectItem value="1hour">1 Hour</SelectItem>
                  <SelectItem value="1day">Daily</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Default Quantity</Label>
              <Input
                type="number"
                min="1"
                value={prefs.defaultQuantity}
                onChange={(e) => setPrefs({ ...prefs, defaultQuantity: parseInt(e.target.value) || 1 })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Risk Management Defaults
          </CardTitle>
          <CardDescription>Set default risk parameters</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Default Stop Loss (%)</Label>
              <div className="relative">
                <Input
                  type="number"
                  min="0"
                  step="0.1"
                  value={prefs.defaultSL}
                  onChange={(e) => setPrefs({ ...prefs, defaultSL: parseFloat(e.target.value) || 0 })}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Default Target (%)</Label>
              <div className="relative">
                <Input
                  type="number"
                  min="0"
                  step="0.1"
                  value={prefs.defaultTarget}
                  onChange={(e) => setPrefs({ ...prefs, defaultTarget: parseFloat(e.target.value) || 0 })}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Risk Per Trade (%)</Label>
            <div className="relative">
              <Input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={prefs.riskPerTrade}
                onChange={(e) => setPrefs({ ...prefs, riskPerTrade: parseFloat(e.target.value) || 0 })}
              />
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            </div>
            <p className="text-xs text-gray-500">Maximum % of capital risked per trade</p>
          </div>
        </CardContent>
      </Card>

      {/* Confirmation Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Order Confirmation
          </CardTitle>
          <CardDescription>Configure order confirmation behavior</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Show Confirmation Dialog</p>
              <p className="text-sm text-gray-500">Ask before placing orders</p>
            </div>
            <Switch
              checked={prefs.showConfirmDialog}
              onCheckedChange={(checked) => setPrefs({ ...prefs, showConfirmDialog: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Auto-execute without confirmation</p>
              <p className="text-sm text-gray-500">Skip confirmation for quick orders</p>
            </div>
            <Switch
              checked={prefs.autoConfirmOrders}
              onCheckedChange={(checked) => setPrefs({ ...prefs, autoConfirmOrders: checked })}
            />
          </div>
        </CardContent>
      </Card>

      {message && (
        <div className={`p-3 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message.text}
        </div>
      )}

      <Button onClick={handleSave} disabled={saving} className="w-full">
        {saving ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Saving...
          </>
        ) : (
          <>
            <Save className="w-4 h-4 mr-2" />
            Save Preferences
          </>
        )}
      </Button>
    </div>
  );
}