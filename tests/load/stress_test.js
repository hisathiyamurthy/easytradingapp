import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_BASE = `${BASE_URL}/api/v1`;

const errorRate = new Rate('errors');
const orderLatency = new Trend('order_placement_latency');

const headers = {
  'Content-Type': 'application/json',
};

export const options = {
  stages: [
    { duration: '10s', target: 5 },
    { duration: '30s', target: 20 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 20 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    order_placement_latency: ['p(95)<1000', 'p(99)<2000'],
    errors: ['rate<0.05'],
  },
};

const login = () => {
  const res = http.post(
    `${API_BASE}/auth/login`,
    JSON.stringify({ email: 'trader@example.com', password: 'trader123' }),
    { headers }
  );
  
  if (res.status === 200) {
    return res.json('access_token');
  }
  return null;
};

export default () => {
  const token = login();
  if (!token) {
    errorRate.add(1);
    return;
  }
  
  const authHeaders = { ...headers, Authorization: `Bearer ${token}` };

  group('Order Placement Stress', () => {
    const orderPayload = JSON.stringify({
      symbol: 'NIFTY',
      exchange: 'NSE',
      side: 'buy',
      order_type: 'market',
      quantity: 10,
      product_type: 'MIS',
      validity: 'DAY',
    });
    
    const res = http.post(`${API_BASE}/orders`, orderPayload, { headers: authHeaders });
    
    orderLatency.add(res.timings.duration);
    
    check(res, {
      'order accepted': (r) => [200, 201, 400, 429].includes(r.status),
    });
    
    if (res.status >= 400) {
      errorRate.add(1);
    }
  });

  group('Market Data Stress', () => {
    const symbols = ['NIFTY', 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY'];
    const symbol = symbols[Math.floor(Math.random() * symbols.length)];
    
    const res = http.get(`${API_BASE}/market/quote/${symbol}`, { headers: authHeaders });
    
    if (res.status >= 400) {
      errorRate.add(1);
    }
  });

  group('Strategy Execution', () => {
    const res = http.get(`${API_BASE}/strategies/active`, { headers: authHeaders });
    
    if (res.status >= 400) {
      errorRate.add(1);
    }
  });

  sleep(0.5);
};

export const handleSummary = (data) => {
  return {
    'stdout': `Stress Test Summary\n\nTotal: ${data.metrics.http_reqs.values.count}\nFailed: ${data.metrics.http_req_failed?.values.passes || 0}\n`,
    'stress-test-report.json': JSON.stringify(data),
  };
};