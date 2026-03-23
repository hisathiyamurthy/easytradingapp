import { useState, useEffect } from 'react';
import { Users, UserCheck, UserX, UserMinus, UserPlus, Search, Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useAuth } from '@/App';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  status: string;
  role: string;
  created_at: string;
}

interface PendingUser {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  created_at: string;
}

export function AdminUserManagement() {
  const { token } = useAuth();
  
  console.log('AdminUserManagement - token:', token);
  
  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'pending' | 'all'>('pending');
  const [searchQuery, setSearchQuery] = useState('');
  const [rejectModal, setRejectModal] = useState<{ userId: string; show: boolean; reason: string }>({
    userId: '',
    show: false,
    reason: '',
  });

  useEffect(() => {
    if (!token) {
      setError('Please log in to access this page');
      setLoading(false);
      return;
    }
    fetchData();
  }, [token]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [pendingRes, usersRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/auth/admin/pending-users`, { headers }),
        fetch(`${API_URL}/api/v1/auth/admin/users`, { headers }),
      ]);

      if (pendingRes.ok) {
        const data = await pendingRes.json();
        setPendingUsers(data);
      }

      if (usersRes.ok) {
        const data = await usersRes.json();
        setAllUsers(data.users);
      }
    } catch {
      setError('Failed to load user data');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (userId: string) => {
    setActionLoading(userId);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/admin/users/${userId}/approve`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId, action: 'approve' }),
      });

      if (response.ok) {
        setPendingUsers(prev => prev.filter(u => u.id !== userId));
        fetchData();
      } else {
        const data = await response.json();
        setError(data.detail || data.message || 'Failed to approve user');
      }
    } catch (err: any) {
      console.error('Approve error:', err);
      setError('Failed to approve user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!rejectModal.reason.trim()) {
      return;
    }

    setActionLoading(rejectModal.userId);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/admin/users/${rejectModal.userId}/reject`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          user_id: rejectModal.userId, 
          action: 'reject',
          reason: rejectModal.reason 
        }),
      });

      if (response.ok) {
        setPendingUsers(prev => prev.filter(u => u.id !== rejectModal.userId));
        setRejectModal({ userId: '', show: false, reason: '' });
        fetchData();
      } else {
        const data = await response.json();
        setError(data.detail || data.message || 'Failed to reject user');
      }
    } catch (err: any) {
      console.error('Reject error:', err);
      setError('Failed to reject user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSuspend = async (userId: string) => {
    const reason = prompt('Enter reason for suspension:');
    if (!reason) return;

    setActionLoading(userId);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/admin/users/${userId}/suspend`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId, action: 'suspend', reason }),
      });

      if (response.ok) {
        fetchData();
      } else {
        const data = await response.json();
        setError(data.detail || data.message || 'Failed to suspend user');
      }
    } catch (err: any) {
      console.error('Suspend error:', err);
      setError('Failed to suspend user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReactivate = async (userId: string) => {
    setActionLoading(userId);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/admin/users/${userId}/reactivate`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId, action: 'reactivate' }),
      });

      if (response.ok) {
        fetchData();
      } else {
        const data = await response.json();
        setError(data.detail || data.message || 'Failed to reactivate user');
      }
    } catch (err: any) {
      console.error('Reactivate error:', err);
      setError('Failed to reactivate user');
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'suspended': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredUsers = activeTab === 'pending' 
    ? pendingUsers 
    : allUsers.filter(u => 
        u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (u.first_name && u.first_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (u.last_name && u.last_name.toLowerCase().includes(searchQuery.toLowerCase()))
      );

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
        <div className="flex items-center gap-3">
          <Users className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">User Management</h1>
            <p className="text-sm text-muted-foreground">Manage user registrations and account status</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg border border-red-200">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <UserPlus className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold">{pendingUsers.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                <UserCheck className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold">
                  {allUsers.filter(u => u.status === 'active').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <UserMinus className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Suspended</p>
                <p className="text-2xl font-bold">
                  {allUsers.filter(u => u.status === 'suspended').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold">{allUsers.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4">
        <Button
          variant={activeTab === 'pending' ? 'default' : 'outline'}
          onClick={() => setActiveTab('pending')}
        >
          <UserPlus className="w-4 h-4 mr-2" />
          Pending Approval ({pendingUsers.length})
        </Button>
        <Button
          variant={activeTab === 'all' ? 'default' : 'outline'}
          onClick={() => setActiveTab('all')}
        >
          <Users className="w-4 h-4 mr-2" />
          All Users
        </Button>
      </div>

      {activeTab === 'all' && (
        <Card>
          <CardContent className="pt-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search users..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* User List */}
      {activeTab === 'pending' ? (
        pendingUsers.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <UserCheck className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No pending registrations</h3>
              <p className="text-muted-foreground">All user registrations have been processed</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {pendingUsers.map((user) => (
              <Card key={user.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="h-12 w-12 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-lg font-semibold text-primary">
                          {(user.first_name?.[0] || user.email[0]).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium">
                          {user.first_name} {user.last_name}
                        </p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                        {user.phone && (
                          <p className="text-xs text-muted-foreground">{user.phone}</p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          Registered: {formatDate(user.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge className={getStatusColor(user.status)}>
                        {user.status}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRejectModal({ userId: user.id, show: true, reason: '' })}
                        disabled={actionLoading === user.id}
                      >
                        {actionLoading === user.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <UserX className="w-4 h-4 mr-1" />
                            Reject
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleApprove(user.id)}
                        disabled={actionLoading === user.id}
                      >
                        {actionLoading === user.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <UserCheck className="w-4 h-4 mr-1" />
                            Approve
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">User</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Email</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Role</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Registered</th>
                  <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-3">
                        <div className="h-8 w-8 bg-primary-100 rounded-full flex items-center justify-center">
                          <span className="text-sm font-semibold text-primary">
                            {(user.first_name?.[0] || user.email[0]).toUpperCase()}
                          </span>
                        </div>
                        <span className="font-medium">
                          {user.first_name} {user.last_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">{user.email}</td>
                    <td className="px-4 py-3">
                      <Badge className={getStatusColor(user.status)}>
                        {user.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm capitalize">{user.role}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {user.status === 'active' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSuspend(user.id)}
                          disabled={actionLoading === user.id}
                        >
                          <UserMinus className="w-4 h-4" />
                        </Button>
                      )}
                      {user.status === 'suspended' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleReactivate(user.id)}
                          disabled={actionLoading === user.id}
                        >
                          <UserPlus className="w-4 h-4" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Reject Modal */}
      {rejectModal.show && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Reject User</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Please provide a reason for rejecting this user registration.
              </p>
              <textarea
                value={rejectModal.reason}
                onChange={(e) => setRejectModal({ ...rejectModal, reason: e.target.value })}
                placeholder="Enter rejection reason..."
                className="w-full h-24 px-3 py-2 border rounded-lg resize-none"
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setRejectModal({ userId: '', show: false, reason: '' })}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleReject}
                  disabled={!rejectModal.reason.trim() || actionLoading === rejectModal.userId}
                >
                  {actionLoading === rejectModal.userId ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    'Reject User'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default AdminUserManagement;
