import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { Button } from '@/components/ui';
import { Input } from '@/components/ui';
import { Label } from '@/components/ui';
import { Badge } from '@/components/ui';
import { Loader2, CheckCircle2, XCircle, AlertCircle, Trash2, RefreshCw } from 'lucide-react';
import { brokerApi, BrokerAccount, BrokerFields } from '@/services/brokerApi';

const BROKERS = [
  { id: 'zerodha', name: 'Zerodha', logo: '🔴', description: "India's largest stock broker" },
  { id: 'angel_one', name: 'Angel One', logo: '🟢', description: 'Trusted by millions' },
  { id: 'upstox', name: 'Upstox', logo: '🔵', description: 'Pro-trading platform' },
  { id: 'kotak_neo', name: 'Kotak Neo', logo: '🟠', description: 'Kotak Securities Neo' },
];

export function BrokerConnectionsPage() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [brokerFields, setBrokerFields] = useState<BrokerFields[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string>('zerodha');
  const [formData, setFormData] = useState({
    account_id: '',
    account_name: '',
    api_key: '',
    api_secret: '',
    api_passphrase: '',
    is_paper_trading: false,
  });
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [accountsData, fieldsData] = await Promise.all([
        brokerApi.getAccounts(),
        brokerApi.getBrokerFields(),
      ]);
      setAccounts(accountsData);
      setBrokerFields(fieldsData);
    } catch (err) {
      console.error('Failed to fetch broker data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTestStatus('testing');
    setError(null);
    try {
      await brokerApi.testConnection({
        broker_name: selectedBroker,
        account_id: formData.account_id,
        api_key: formData.api_key,
        api_secret: formData.api_secret,
        api_passphrase: formData.api_passphrase,
      });
      setTestStatus('success');
    } catch (err: any) {
      setTestStatus('error');
      setError(err.response?.data?.detail || 'Connection failed');
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      await brokerApi.addAccount({
        broker_name: selectedBroker,
        account_id: formData.account_id,
        account_name: formData.account_name || undefined,
        encrypted_api_key: formData.api_key,
        encrypted_api_secret: formData.api_secret,
        encrypted_api_passphrase: formData.api_passphrase || undefined,
        is_paper_trading: formData.is_paper_trading,
      });
      await fetchData();
      setFormData({
        account_id: '',
        account_name: '',
        api_key: '',
        api_secret: '',
        api_passphrase: '',
        is_paper_trading: false,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect broker');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async (accountId: string) => {
    if (confirm('Are you sure you want to disconnect this broker?')) {
      try {
        await brokerApi.deleteAccount(accountId);
        await fetchData();
      } catch (err) {
        console.error('Failed to disconnect broker:', err);
      }
    }
  };

  const getStatusBadge = (status: string, isActive: boolean) => {
    if (!isActive) {
      return <Badge variant="secondary">Disabled</Badge>;
    }
    switch (status) {
      case 'healthy':
        return <Badge className="bg-green-100 text-green-700"><CheckCircle2 className="w-3 h-3 mr-1" /> Connected</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-700"><XCircle className="w-3 h-3 mr-1" /> Error</Badge>;
      default:
        return <Badge variant="secondary"><AlertCircle className="w-3 h-3 mr-1" /> Unknown</Badge>;
    }
  };

  const getBrokerInfo = (brokerId: string) => BROKERS.find(b => b.id === brokerId) || BROKERS[0];

  if (loading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Broker Connections</h1>
        <p className="text-gray-500 mt-1">Connect your broker accounts to enable trading</p>
      </div>

      {/* Connected Accounts */}
      <Card>
        <CardHeader>
          <CardTitle>Connected Accounts</CardTitle>
          <CardDescription>Your active broker connections</CardDescription>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p>No broker accounts connected yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {accounts.map((account) => {
                const brokerInfo = getBrokerInfo(account.broker_name);
                return (
                  <div key={account.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center">
                        <span className="text-lg font-bold text-primary">{brokerInfo.logo}</span>
                      </div>
                      <div>
                        <p className="font-medium">{brokerInfo.name}</p>
                        <p className="text-sm text-gray-500">{account.account_id}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      {getStatusBadge(account.health_status, account.is_active)}
                      {account.is_paper_trading && (
                        <Badge variant="outline">Paper Trading</Badge>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-600 hover:text-red-700"
                        onClick={() => handleDisconnect(account.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add New Connection */}
      <Card>
        <CardHeader>
          <CardTitle>Add Broker Account</CardTitle>
          <CardDescription>Connect a new broker to start trading</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Broker Selection */}
          <div className="space-y-3">
            <Label>Select Broker</Label>
            <select
              className="w-full p-3 border rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedBroker}
              onChange={(e) => setSelectedBroker(e.target.value)}
            >
              <option value="">Choose a broker...</option>
              {BROKERS.map((broker) => (
                <option key={broker.id} value={broker.id}>
                  {broker.logo} {broker.name} - {broker.description}
                </option>
              ))}
            </select>
          </div>

          {/* Broker Cards Preview */}
          <div className="grid grid-cols-4 gap-4">
            {BROKERS.map((broker) => (
              <button
                key={broker.id}
                onClick={() => setSelectedBroker(broker.id)}
                className={`p-4 border-2 rounded-lg text-center transition-all cursor-pointer ${
                  selectedBroker === broker.id
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="text-2xl mb-1">{broker.logo}</div>
                <p className="font-medium text-sm">{broker.name}</p>
              </button>
            ))}
          </div>

          {/* Form */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="account_id">Account ID / Client ID</Label>
              <Input
                id="account_id"
                value={formData.account_id}
                onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
                placeholder="Enter account ID"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="account_name">Account Name (Optional)</Label>
              <Input
                id="account_name"
                value={formData.account_name}
                onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                placeholder="My Trading Account"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="api_key">API Key</Label>
              <Input
                id="api_key"
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                placeholder="Enter API Key"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="api_secret">API Secret</Label>
              <Input
                id="api_secret"
                type="password"
                value={formData.api_secret}
                onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                placeholder="Enter API Secret"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="api_passphrase">TOTP Key / Password (Optional)</Label>
              <Input
                id="api_passphrase"
                type="password"
                value={formData.api_passphrase}
                onChange={(e) => setFormData({ ...formData, api_passphrase: e.target.value })}
                placeholder="Enter TOTP Key"
              />
            </div>
            <div className="flex items-center space-x-2 pt-6">
              <input
                id="is_paper_trading"
                type="checkbox"
                checked={formData.is_paper_trading}
                onChange={(e) => setFormData({ ...formData, is_paper_trading: e.target.checked })}
                className="h-4 w-4"
              />
              <Label htmlFor="is_paper_trading" className="cursor-pointer">
                Enable Paper Trading
              </Label>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {testStatus === 'success' && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-center">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Connection successful!
            </div>
          )}

          <div className="flex gap-3">
            <Button
              onClick={handleConnect}
              disabled={connecting || !formData.account_id || !formData.api_key}
            >
              {connecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Connect
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={handleTestConnection}
              disabled={testStatus === 'testing' || !formData.account_id || !formData.api_key}
            >
              {testStatus === 'testing' ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Test Connection
                </>
              )}
            </Button>
          </div>
        </CardContent>
        <div className="bg-yellow-50 border-t p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">Security Notice</p>
              <p>Your API credentials are encrypted and stored securely. We never share your data with third parties.</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default BrokerConnectionsPage;
