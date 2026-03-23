const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface LifecycleState {
  strategy_id: string;
  current_state: string;
  allowed_transitions: string[];
  requirements: Record<string, string[]>;
}

export interface ValidationResult {
  strategy_id: string;
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  can_run_backtest: boolean;
  can_start_paper_trading: boolean;
  can_start_live: boolean;
  lifecycle_state: string;
  allowed_transitions: string[];
}

export interface TransitionResult {
  success: boolean;
  from_state: string;
  to_state: string;
  message: string;
  requirements_met: string[];
  requirements_missing: string[];
}

export async function parseStrategy(text: string): Promise<any> {
  const response = await fetch(`${API_URL}/api/v1/strategies/parse`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ strategy_text: text }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to parse strategy');
  }
  
  return response.json();
}

export async function validateStrategy(strategyId: string): Promise<ValidationResult> {
  const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}/validate`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to validate strategy');
  }
  
  return response.json();
}

export async function getLifecycle(strategyId: string): Promise<LifecycleState> {
  const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}/lifecycle`, {
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get lifecycle');
  }
  
  return response.json();
}

export async function transitionStrategy(strategyId: string, targetState: string): Promise<TransitionResult> {
  const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}/transition`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ target_state: targetState }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to transition strategy');
  }
  
  return response.json();
}

export async function runBacktest(text: string): Promise<any> {
  const response = await fetch(`${API_URL}/api/v1/strategies/backtest-text`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ strategy_text: text }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to run backtest');
  }
  
  return response.json();
}

export async function approveStrategy(strategyId: string, approved: boolean, reason?: string): Promise<any> {
  const response = await fetch(`${API_URL}/api/v1/strategies/${strategyId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ approved, reason }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to approve strategy');
  }
  
  return response.json();
}

export async function getPendingApproval(): Promise<{ strategies: any[]; total: number }> {
  const response = await fetch(`${API_URL}/api/v1/strategies/admin/pending-approval`, {
    headers: getAuthHeaders(),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get pending strategies');
  }
  
  return response.json();
}

export const LIFECYCLE_STATES = {
  DRAFT: { label: 'Draft', color: 'gray' },
  validated: { label: 'Validated', color: 'blue' },
  backtested: { label: 'Backtested', color: 'purple' },
  paper_trading: { label: 'Paper Trading', color: 'yellow' },
  live: { label: 'Live', color: 'green' },
  PAUSED: { label: 'Paused', color: 'orange' },
  STOPPED: { label: 'Stopped', color: 'red' },
} as const;

export function getStateColor(state: string): string {
  const stateInfo = LIFECYCLE_STATES[state as keyof typeof LIFECYCLE_STATES];
  switch (stateInfo?.color) {
    case 'gray': return 'bg-gray-100 text-gray-800';
    case 'blue': return 'bg-blue-100 text-blue-800';
    case 'purple': return 'bg-purple-100 text-purple-800';
    case 'yellow': return 'bg-yellow-100 text-yellow-800';
    case 'green': return 'bg-green-100 text-green-800';
    case 'orange': return 'bg-orange-100 text-orange-800';
    case 'red': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}
