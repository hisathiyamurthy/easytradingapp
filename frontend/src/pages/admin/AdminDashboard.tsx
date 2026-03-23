import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui';
import { useAuth } from '@/App';
import { adminApi, AdminStats, BrokerStatus, ActiveSession } from '@/services/adminApi';

export function AdminDashboard() {
  const { token } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [brokers, setBrokers] = useState<BrokerStatus[]>([]);
  const [activeUsers, setActiveUsers] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchDashboardData();
    }
  }, [token]);

  const fetchDashboardData = async () => {
    try {
      const [statsData, brokersData, sessionsData] = await Promise.all([
        adminApi.getStats(),
        adminApi.getBrokers().catch(() => []),
        adminApi.getActiveSessions().catch(() => []),
      ]);

      setStats(statsData);
      setBrokers(brokersData);
      setActiveUsers(sessionsData);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-muted-foreground">Loading admin dashboard...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-sm text-muted-foreground">System overview and management</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Users" value={stats?.total_users || 0} color="blue" />
        <StatCard title="Active Users" value={stats?.active_users || 0} color="green" />
        <StatCard title="Active Strategies" value={stats?.active_strategies || 0} color="purple" />
        <StatCard title="Orders Today" value={stats?.total_orders_today || 0} color="orange" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Broker Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {brokers.map((broker) => (
                <div key={broker.name} className="flex items-center justify-between p-3 bg-muted rounded">
                  <span className="font-medium">{broker.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full ${broker.connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    <span className="text-sm text-muted-foreground">{broker.connected ? 'Connected' : 'Disconnected'}</span>
                  </div>
                </div>
              ))}
              {brokers.length === 0 && (
                <p className="text-center py-4 text-muted-foreground">No brokers configured</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <HealthMetric label="API Server" status="healthy" />
              <HealthMetric label="Database" status="healthy" />
              <HealthMetric label="Redis Cache" status="healthy" />
              <HealthMetric label="Message Queue" status="healthy" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {activeUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.user_email}</TableCell>
                  <TableCell>{user.user_email}</TableCell>
                  <TableCell>{user.last_activity_at ? new Date(user.last_activity_at).toLocaleString() : '-'}</TableCell>
                  <TableCell>{user.ip_address}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                      Revoke
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {activeUsers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-4 text-muted-foreground">No active sessions</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex gap-4">
        <Button>
          View Logs
        </Button>
        <Button variant="outline">
          System Settings
        </Button>
      </div>
    </div>
  );
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className={`h-12 w-12 rounded-lg flex items-center justify-center mb-4 ${colorClasses[color]}`}>
          <span className="text-2xl font-bold">{value.toLocaleString()}</span>
        </div>
        <p className="text-sm text-muted-foreground">{title}</p>
      </CardContent>
    </Card>
  );
}

function HealthMetric({ label, status }: { label: string; status: string }) {
  const statusColors: Record<string, string> = {
    healthy: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  return (
    <div className="flex items-center justify-between p-3 bg-muted rounded">
      <span className="font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`w-3 h-3 rounded-full ${statusColors[status]}`}></span>
        <span className="text-sm text-muted-foreground capitalize">{status}</span>
      </div>
    </div>
  );
}

export default AdminDashboard;
