import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { Button } from '@/components/ui';
import { Input } from '@/components/ui';
import { Label } from '@/components/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui';
import { Badge } from '@/components/ui';
import { Loader2, Plus, Trash2, Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { riskApi, RiskRule, RiskStatus, RULE_TYPES, ACTIONS } from '@/services/riskApi';

export function RiskRulesPage() {
  const [rules, setRules] = useState<RiskRule[]>([]);
  const [status, setStatus] = useState<RiskStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newRule, setNewRule] = useState({
    rule_type: '',
    rule_name: '',
    threshold_value: 0,
    action: 'alert',
    is_enabled: true,
    is_hard: false,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [rulesData, statusData] = await Promise.all([
        riskApi.getRules(),
        riskApi.getStatus(),
      ]);
      setRules(rulesData);
      setStatus(statusData);
    } catch (err) {
      console.error('Failed to fetch risk data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRule = async () => {
    if (!newRule.rule_type || !newRule.rule_name || !newRule.threshold_value) return;
    
    setSaving(true);
    try {
      await riskApi.createRule(newRule);
      await fetchData();
      setShowForm(false);
      setNewRule({
        rule_type: '',
        rule_name: '',
        threshold_value: 0,
        action: 'alert',
        is_enabled: true,
        is_hard: false,
      });
    } catch (err) {
      console.error('Failed to create rule:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
      await riskApi.deleteRule(ruleId);
      await fetchData();
    } catch (err) {
      console.error('Failed to delete rule:', err);
    }
  };

  const handleKillSwitch = async () => {
    const reason = prompt('Please enter a reason for triggering the kill switch (required):');
    if (!reason) return;
    
    if (!confirm('WARNING: This will immediately stop ALL trading activity. Are you absolutely sure?')) return;
    
    setLoading(true);
    try {
      await riskApi.triggerKillSwitch(reason);
      alert('Kill switch activated! All trading has been halted.');
      await fetchData();
    } catch (err) {
      console.error('Failed to trigger kill switch:', err);
      alert('Failed to trigger kill switch. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getRuleTypeLabel = (type: string) => RULE_TYPES.find(r => r.value === type)?.label || type;
  const getActionLabel = (action: string) => ACTIONS.find(a => a.value === action)?.label || action;

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low': return 'bg-green-100 text-green-700';
      case 'medium': return 'bg-yellow-100 text-yellow-700';
      case 'high': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Risk Management</h1>
          <p className="text-gray-500 mt-1">Configure risk limits and protect your portfolio</p>
        </div>
      </div>

      {/* Risk Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Risk Level</p>
                <p className={`text-xl font-bold mt-1 capitalize ${status?.risk_level === 'high' ? 'text-red-600' : status?.risk_level === 'medium' ? 'text-yellow-600' : 'text-green-600'}`}>
                  {status?.risk_level || 'low'}
                </p>
              </div>
              <Shield className={`h-8 w-8 ${status?.risk_level === 'high' ? 'text-red-600' : status?.risk_level === 'medium' ? 'text-yellow-600' : 'text-green-600'}`} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Active Rules</p>
                <p className="text-xl font-bold mt-1">{status?.active_rules || 0}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Active Breaches</p>
                <p className={`text-xl font-bold mt-1 ${(status?.active_breaches || 0) > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                  {status?.active_breaches || 0}
                </p>
              </div>
              <AlertTriangle className={`h-8 w-8 ${(status?.active_breaches || 0) > 0 ? 'text-red-600' : 'text-gray-400'}`} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Exposure</p>
                <p className="text-xl font-bold mt-1">₹{(status?.total_exposure || 0).toLocaleString()}</p>
              </div>
              <Shield className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risk Rules List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Risk Rules</CardTitle>
            <CardDescription>Configure trading limits and safeguards</CardDescription>
          </div>
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Rule
          </Button>
        </CardHeader>
        <CardContent>
          {showForm && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Rule Type</Label>
                  <Select value={newRule.rule_type} onValueChange={(v) => setNewRule({ ...newRule, rule_type: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select rule type" />
                    </SelectTrigger>
                    <SelectContent>
                      {RULE_TYPES.map((rt) => (
                        <SelectItem key={rt.value} value={rt.value}>{rt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Rule Name</Label>
                  <Input
                    value={newRule.rule_name}
                    onChange={(e) => setNewRule({ ...newRule, rule_name: e.target.value })}
                    placeholder="My Risk Rule"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Threshold Value</Label>
                  <Input
                    type="number"
                    value={newRule.threshold_value}
                    onChange={(e) => setNewRule({ ...newRule, threshold_value: Number(e.target.value) })}
                    placeholder="10000"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Action</Label>
                  <Select value={newRule.action} onValueChange={(v) => setNewRule({ ...newRule, action: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTIONS.map((a) => (
                        <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateRule} disabled={saving}>
                  {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Save Rule
                </Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              </div>
            </div>
          )}

          {rules.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Shield className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p>No risk rules configured</p>
              <p className="text-sm">Add rules to protect your portfolio</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => (
                <div key={rule.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${rule.is_enabled ? 'bg-green-100' : 'bg-gray-100'}`}>
                      <Shield className={`h-5 w-5 ${rule.is_enabled ? 'text-green-600' : 'text-gray-400'}`} />
                    </div>
                    <div>
                      <p className="font-medium">{rule.rule_name}</p>
                      <p className="text-sm text-gray-500">{getRuleTypeLabel(rule.rule_type)} • {getActionLabel(rule.action)}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="font-medium">₹{rule.threshold_value.toLocaleString()}</p>
                      {rule.is_hard && <Badge className="ml-2 bg-red-100 text-red-700">Hard Limit</Badge>}
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteRule(rule.id)}>
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Kill Switch */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Emergency Kill Switch</CardTitle>
          <CardDescription>Immediately stop all trading activity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Kill Switch Status</p>
              <p className="text-sm text-gray-500">
                {status?.kill_switch_active 
                  ? 'Active - Trading is halted' 
                  : 'Ready - All trading normal'}
              </p>
            </div>
            <Button 
              variant="destructive"
              onClick={handleKillSwitch}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <AlertTriangle className="w-4 h-4 mr-2" />
              )}
              Trigger Kill Switch
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default RiskRulesPage;
