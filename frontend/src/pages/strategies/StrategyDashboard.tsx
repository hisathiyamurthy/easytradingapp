import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useStrategies, useActivateStrategy, useDeactivateStrategy, useDeleteStrategy } from '@/hooks/useStrategies';
import { useAuth } from '@/App';
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger, Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui';
import { Loader2, Plus, Play, Pause, Trash2, Edit, Copy, Activity, TrendingUp, BarChart3, MoreVertical, Power, PowerOff, Shield } from 'lucide-react';
import { format } from 'date-fns';

const strategyTypeLabels: Record<string, string> = {
  momentum: 'Momentum',
  mean_reversion: 'Mean Reversion',
  breakout: 'Breakout',
  grid: 'Grid',
  dca: 'DCA',
  custom: 'Custom',
};

const statusColors: Record<string, string> = {
  created: 'bg-gray-100 text-gray-700',
  initializing: 'bg-blue-100 text-blue-700',
  running: 'bg-green-100 text-green-700',
  paused: 'bg-yellow-100 text-yellow-700',
  stopped: 'bg-red-100 text-red-700',
  error: 'bg-red-100 text-red-700',
};

interface StrategyCardProps {
  strategy: any;
  onActivate: (id: string) => void;
  onDeactivate: (id: string) => void;
  onDelete: (id: string) => void;
  isActivating: boolean;
}

function StrategyCard({ strategy, onActivate, onDeactivate, onDelete, isActivating }: StrategyCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{strategy.name}</CardTitle>
            <CardDescription className="mt-1">
              {strategyTypeLabels[strategy.strategy_type] || strategy.strategy_type}
            </CardDescription>
          </div>
          <Badge className={statusColors[strategy.status] || 'bg-gray-100'}>
            {strategy.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Total Trades</p>
            <p className="font-medium">{strategy.stats?.total_trades || 0}</p>
          </div>
          <div>
            <p className="text-gray-500">Win Rate</p>
            <p className="font-medium">{strategy.stats?.win_rate || 0}%</p>
          </div>
          <div>
            <p className="text-gray-500">P&L</p>
            <p className={`font-medium ${(strategy.stats?.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ₹{strategy.stats?.pnl || 0}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center space-x-2">
            {strategy.status === 'running' ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDeactivate(strategy.id)}
                disabled={isActivating}
              >
                <Pause className="h-4 w-4 mr-1" />
                Pause
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onActivate(strategy.id)}
                disabled={isActivating || strategy.status === 'error'}
              >
                <Play className="h-4 w-4 mr-1" />
                Start
              </Button>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link to={`/strategies/${strategy.id}`}>
                <Edit className="h-4 w-4 mr-1" />
                Edit
              </Link>
            </Button>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-red-600 hover:text-red-700"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Strategy</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{strategy.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={() => {
              onDelete(strategy.id);
              setShowDeleteDialog(false);
            }}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

export function StrategyDashboard() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  
  const { data: strategies, isLoading, refetch } = useStrategies();
  const activateMutation = useActivateStrategy();
  const deactivateMutation = useDeactivateStrategy();
  const deleteMutation = useDeleteStrategy();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Filter strategies
  const filteredStrategies = strategies?.filter((strategy) => {
    const matchesSearch = strategy.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || strategy.status === statusFilter;
    const matchesType = typeFilter === 'all' || strategy.strategy_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  }) || [];

  // Calculate stats
  const totalStrategies = strategies?.length || 0;
  const activeStrategies = strategies?.filter(s => s.status === 'running').length || 0;
  const totalPnl = strategies?.reduce((acc, s) => acc + (s.stats?.pnl || 0), 0) || 0;

  const handleActivate = async (id: string) => {
    await activateMutation.mutateAsync(id);
    refetch();
  };

  const handleDeactivate = async (id: string) => {
    await deactivateMutation.mutateAsync(id);
    refetch();
  };

  const handleDelete = async (id: string) => {
    await deleteMutation.mutateAsync(id);
    refetch();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Strategies</h1>
          <p className="text-gray-500 mt-1">Manage and monitor your trading strategies</p>
        </div>
        <div className="flex items-center space-x-2">
          {isAdmin && (
            <Button asChild>
              <Link to="/strategies/builder">
                <Plus className="h-4 w-4 mr-2" />
                New Strategy
              </Link>
            </Button>
          )}
          {!isAdmin && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Shield className="w-4 h-4" />
              Only admins can create strategies
            </div>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Strategies</p>
                <p className="text-2xl font-bold">{totalStrategies}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Activity className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Active</p>
                <p className="text-2xl font-bold">{activeStrategies}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total P&L</p>
                <p className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ₹{totalPnl.toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <Power className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Paused</p>
                <p className="text-2xl font-bold">
                  {strategies?.filter(s => s.status === 'paused').length || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-start md:items-center space-y-4 md:space-y-0 md:space-x-4">
            <Input
              placeholder="Search strategies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full md:w-64"
            />

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="created">Created</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
                <SelectItem value="stopped">Stopped</SelectItem>
                <SelectItem value="error">Error</SelectItem>
              </SelectContent>
            </Select>

            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full md:w-48">
                <SelectValue placeholder="Strategy Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="momentum">Momentum</SelectItem>
                <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
                <SelectItem value="breakout">Breakout</SelectItem>
                <SelectItem value="grid">Grid</SelectItem>
                <SelectItem value="dca">DCA</SelectItem>
                <SelectItem value="custom">Custom</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center space-x-1 ml-auto">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                Grid
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
              >
                List
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Strategy List */}
      {filteredStrategies.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <BarChart3 className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium">No strategies found</h3>
            <p className="text-gray-500 mt-1">
              {searchQuery || statusFilter !== 'all' || typeFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Create your first trading strategy'}
            </p>
            <Button className="mt-4" asChild>
              <Link to="/strategies/builder">
                <Plus className="h-4 w-4 mr-2" />
                Create Strategy
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredStrategies.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              onActivate={handleActivate}
              onDeactivate={handleDeactivate}
              onDelete={handleDelete}
              isActivating={activateMutation.isPending || deactivateMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Trades</TableHead>
                <TableHead>Win Rate</TableHead>
                <TableHead>P&L</TableHead>
                <TableHead>Last Run</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredStrategies.map((strategy) => (
                <TableRow key={strategy.id}>
                  <TableCell className="font-medium">{strategy.name}</TableCell>
                  <TableCell>{strategyTypeLabels[strategy.strategy_type] || strategy.strategy_type}</TableCell>
                  <TableCell>
                    <Badge className={statusColors[strategy.status] || 'bg-gray-100'}>
                      {strategy.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{strategy.stats?.total_trades || 0}</TableCell>
                  <TableCell>{strategy.stats?.win_rate || 0}%</TableCell>
                  <TableCell className={(strategy.stats?.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}>
                    ₹{strategy.stats?.pnl || 0}
                  </TableCell>
                  <TableCell>
                    {strategy.last_run_at ? format(new Date(strategy.last_run_at), 'MMM d, HH:mm') : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      {strategy.status === 'running' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeactivate(strategy.id)}
                        >
                          <Pause className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleActivate(strategy.id)}
                          disabled={strategy.status === 'error'}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" asChild>
                        <Link to={`/strategies/${strategy.id}`}>
                          <Edit className="h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

export default StrategyDashboard;
