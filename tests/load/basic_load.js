import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_BASE = `${BASE_URL}/api/v1`;

const errorRate = new Rate('errors');
const requestDuration = new Trend('request_duration');
const ordersPlaced = new Counter('orders_placed');
const strategyCreated = new Counter('strategies_created');

const headers = {
  'Content-Type': 'application/json',
};

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.1'],
  },
};

const login = () => {
  const res = http.post(
    `${API_BASE}/auth/login`,
    JSON.stringify({ email: 'test@example.com', password: 'testpass123' }),
    { headers }
  );
  
  if (res.status === 200) {
    const token = res.json('access_token');
    return token;
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

  group('Health Checks', () => {
    const res = http.get(`${BASE_URL}/health`);
    check(res, { 'health endpoint works': (r) => r.status === 200 });
  });

  group('Market Data', () => {
    const res = http.get(`${API_BASE}/market/quote/NIFTY`, { headers: authHeaders });
    requestDuration.add(res.timings.duration);
    check(res, { 'quote fetch works': (r) => r.status === 200 || r.status === 404 });
  });

  group('Strategies', () => {
    const res = http.get(`${API_BASE}/strategies`, { headers: authHeaders });
    requestDuration.add(res.timings.duration);
    check(res, { 'list strategies works': (r) => r.status === 200 });
  });

  group('Orders', () => {
    const res = http.get(`${API_BASE}/orders`, { headers: authHeaders });
    requestDuration.add(res.timings.duration);
    check(res, { 'list orders works': (r) => r.status === 200 });
    ordersPlaced.add(1);
  });

  group('Portfolio', () => {
    const res = http.get(`${API_BASE}/portfolio/positions`, { headers: authHeaders });
    requestDuration.add(res.timings.duration);
    check(res, { 'get positions works': (r) => r.status === 200 });
  });

  group('Analytics', () => {
    const res = http.get(`${API_BASE}/analytics/summary`, { headers: authHeaders });
    requestDuration.add(res.timings.duration);
    check(res, { 'analytics works': (r) => r.status === 200 });
  });

  sleep(1);
};

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let output = `${indent}Test Summary\n`;
  output += `${indent}==============\n\n`;
  
  output += `${indent}Total Requests: ${data.metrics.http_reqs.values.count}\n`;
  output += `${indent}Failed Requests: ${data.metrics.http_req_failed?.values.passes || 0}\n`;
  output += `${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  output += `${indent}p95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  output += `${indent}p99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
  
  return output;
}