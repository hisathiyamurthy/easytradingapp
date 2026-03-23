import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { Button } from '@/components/ui';
import { Loader2, Users, Link2, Save, X, Check } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Strategy {
  id: string;
  name: string;
  strategy_type: string;
  status: string;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
}

interface Assignment {
  id: string;
  user_id: string;
  strategy_id: string;
  is_default: boolean;
  is_active: boolean;
  assigned_at: string;
}

export default function StrategyAssignment() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [assignToAll, setAssignToAll] = useState(false);
  const [setAsDefault, setSetAsDefault] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      
      const strategiesRes = await fetch(`${API_URL}/api/v1/strategies`, { headers });
      const strategiesData = await strategiesRes.json();
      setStrategies(strategiesData.strategies || []);
      
      const usersRes = await fetch(`${API_URL}/api/v1/admin/users`, { headers });
      const usersData = await usersRes.json();
      setUsers(usersData.users || []);
      
      const assignRes = await fetch(`${API_URL}/api/v1/strategies/assignments`, { headers });
      const assignData = await assignRes.json();
      setAssignments(assignData || []);
      
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async () => {
    if (selectedStrategies.length === 0) {
      setMessage({ type: 'error', text: 'Please select at least one strategy' });
      return;
    }
    if (!assignToAll && selectedUsers.length === 0) {
      setMessage({ type: 'error', text: 'Please select users or select "All Users"' });
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/strategies/assign`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          strategy_ids: selectedStrategies,
          user_ids: selectedUsers,
          is_default: setAsDefault,
          assign_to_all: assignToAll,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message });
        setSelectedStrategies([]);
        setSelectedUsers([]);
        setSetAsDefault(false);
        fetchData();
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.detail || 'Failed to assign' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to assign strategies' });
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveAssignment = async (assignmentId: string) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_URL}/api/v1/strategies/assignments/${assignmentId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchData();
    } catch (error) {
      console.error('Error removing assignment:', error);
    }
  };

  const toggleStrategy = (strategyId: string) => {
    setSelectedStrategies(prev => 
      prev.includes(strategyId) 
        ? prev.filter(id => id !== strategyId)
        : [...prev, strategyId]
    );
  };

  const toggleUser = (userId: string) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const getStrategyName = (id: string) => strategies.find(s => s.id === id)?.name || id;
  const getUserEmail = (id: string) => users.find(u => u.id === id)?.email || id;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Strategy Assignment</h1>
        <p className="text-gray-500 mt-1">Assign strategies to users - admin only</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link2 className="w-5 h-5" />
              Select Strategies
            </CardTitle>
            <CardDescription>Choose strategies to assign</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {strategies.map(strategy => (
                <div 
                  key={strategy.id} 
                  className={`p-3 border rounded-lg cursor-pointer flex items-center gap-3 ${
                    selectedStrategies.includes(strategy.id) 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => toggleStrategy(strategy.id)}
                >
                  {selectedStrategies.includes(strategy.id) ? (
                    <Check className="w-5 h-5 text-blue-500" />
                  ) : (
                    <div className="w-5 h-5 border rounded" />
                  )}
                  <div>
                    <p className="font-medium">{strategy.name}</p>
                    <p className="text-xs text-gray-500">{strategy.strategy_type} - {strategy.status}</p>
                  </div>
                </div>
              ))}
              {strategies.length === 0 && (
                <p className="text-gray-500 text-center py-4">No strategies available</p>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-2">{selectedStrategies.length} selected</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Select Users
            </CardTitle>
            <CardDescription>Choose users to assign strategies to</CardDescription>
          </CardHeader>
          <CardContent>
            <div 
              className={`flex items-center gap-2 mb-4 p-3 rounded-lg cursor-pointer ${assignToAll ? 'bg-blue-50' : 'bg-gray-50'}`}
              onClick={() => {
                setAssignToAll(!assignToAll);
                if (!assignToAll) setSelectedUsers([]);
              }}
            >
              {assignToAll ? (
                <Check className="w-5 h-5 text-blue-500" />
              ) : (
                <div className="w-5 h-5 border rounded" />
              )}
              <span className="text-sm">Assign to ALL active users</span>
            </div>
            
            {!assignToAll && (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {users.map(user => (
                  <div 
                    key={user.id} 
                    className={`p-3 border rounded-lg cursor-pointer flex items-center gap-3 ${
                      selectedUsers.includes(user.id) 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'hover:bg-gray-50'
                    }`}
                    onClick={() => toggleUser(user.id)}
                  >
                    {selectedUsers.includes(user.id) ? (
                      <Check className="w-5 h-5 text-blue-500" />
                    ) : (
                      <div className="w-5 h-5 border rounded" />
                    )}
                    <div>
                      <p className="font-medium">{user.first_name} {user.last_name}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <p className="text-sm text-gray-500 mt-2">
              {assignToAll ? `All ${users.length} users will be assigned` : `${selectedUsers.length} users selected`}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Assignment Options</CardTitle>
        </CardHeader>
        <CardContent>
          <div 
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => setSetAsDefault(!setAsDefault)}
          >
            {setAsDefault ? (
              <Check className="w-5 h-5 text-blue-500" />
            ) : (
              <div className="w-5 h-5 border rounded" />
            )}
            <span className="text-sm">Set as default strategy (auto-assigned to new users)</span>
          </div>

          {message && (
            <div className={`mt-4 p-3 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {message.text}
            </div>
          )}

          <Button 
            onClick={handleAssign} 
            disabled={saving || selectedStrategies.length === 0}
            className="mt-4"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Assigning...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Assign Strategies
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Current Assignments</CardTitle>
          <CardDescription>View and manage existing assignments</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4">Strategy</th>
                  <th className="text-left py-3 px-4">User</th>
                  <th className="text-left py-3 px-4">Default</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Assigned</th>
                  <th className="text-left py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map(assignment => (
                  <tr key={assignment.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">{getStrategyName(assignment.strategy_id)}</td>
                    <td className="py-3 px-4">{getUserEmail(assignment.user_id)}</td>
                    <td className="py-3 px-4">
                      {assignment.is_default && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">Default</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs rounded ${
                        assignment.is_active 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {assignment.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500">
                      {assignment.assigned_at ? new Date(assignment.assigned_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="py-3 px-4">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleRemoveAssignment(assignment.id)}
                      >
                        <X className="w-4 h-4 text-red-500" />
                      </Button>
                    </td>
                  </tr>
                ))}
                {assignments.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-gray-500">
                      No assignments yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}