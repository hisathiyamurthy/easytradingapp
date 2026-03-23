# EasyTradingApp - Frontend Architecture

## Tech Stack
- React 18 + TypeScript
- Vite (build tool)
- React Router v6
- Zustand (state management)
- TanStack Query (server state)
- React Hook Form + Zod (forms)
- TailwindCSS (styling)
- shadcn/ui (component library)
- Recharts (charts)
- React Query (data fetching)

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # App-level providers and routing
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   └── providers.tsx
│   │
│   ├── pages/                  # Page components
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   └── ForgotPassword.tsx
│   │   ├── dashboard/
│   │   │   ├── Dashboard.tsx
│   │   │   └── Overview.tsx
│   │   ├── strategies/
│   │   │   ├── StrategyList.tsx
│   │   │   ├── StrategyEditor.tsx
│   │   │   ├── StrategyBuilder.tsx  # NL strategy builder
│   │   │   └── StrategyDetail.tsx
│   │   ├── trading/
│   │   │   ├── PaperTrading.tsx
│   │   │   ├── LiveTrading.tsx
│   │   │   └── TradeHistory.tsx
│   │   ├── backtesting/
│   │   │   ├── BacktestList.tsx
│   │   │   ├── BacktestRun.tsx
│   │   │   └── BacktestResults.tsx
│   │   ├── analytics/
│   │   │   ├── ProfitAnalytics.tsx
│   │   │   ├── Performance.tsx
│   │   │   └── Reports.tsx
│   │   ├── settings/
│   │   │   ├── Profile.tsx
│   │   │   ├── BrokerConnections.tsx
│   │   │   ├── RiskLimits.tsx
│   │   │   └── Notifications.tsx
│   │   └── admin/
│   │       ├── UserManagement.tsx
│   │       └── SystemHealth.tsx
│   │
│   ├── components/              # Reusable components
│   │   ├── ui/                 # Base UI components (shadcn)
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── AppLayout.tsx
│   │   ├── charts/
│   │   │   ├── CandlestickChart.tsx
│   │   │   ├── EquityCurve.tsx
│   │   │   ├── DrawdownChart.tsx
│   │   │   └── WinLossPie.tsx
│   │   ├── forms/
│   │   │   ├── StrategyForm.tsx
│   │   │   ├── OrderForm.tsx
│   │   │   └── RiskLimitForm.tsx
│   │   ├── tables/
│   │   │   ├── TradesTable.tsx
│   │   │   ├── OrdersTable.tsx
│   │   │   └── StrategiesTable.tsx
│   │   └── widgets/
│   │       ├── PortfolioSummary.tsx
│   │       ├── ActivePositions.tsx
│   │       ├── QuickTrade.tsx
│   │       └── MarketTicker.tsx
│   │
│   ├── hooks/                  # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useStrategies.ts
│   │   ├── useOrders.ts
│   │   ├── usePositions.ts
│   │   ├── useBacktest.ts
│   │   └── useWebSocket.ts
│   │
│   ├── services/               # API clients
│   │   ├── api.ts             # Axios instance
│   │   ├── auth.service.ts
│   │   ├── strategy.service.ts
│   │   ├── order.service.ts
│   │   ├── broker.service.ts
│   │   ├── backtest.service.ts
│   │   └── analytics.service.ts
│   │
│   ├── stores/                # Zustand stores
│   │   ├── authStore.ts
│   │   ├── strategyStore.ts
│   │   ├── tradingStore.ts
│   │   └── uiStore.ts
│   │
│   ├── types/                 # TypeScript types
│   │   ├── api.types.ts
│   │   ├── strategy.types.ts
│   │   ├── order.types.ts
│   │   ├── user.types.ts
│   │   └── analytics.types.ts
│   │
│   ├── utils/                 # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   ├── constants.ts
│   │   └── helpers.ts
│   │
│   └── lib/                   # Third-party configuration
│       ├── axios.ts
│       ├── query-client.ts
│       └── utils.ts
│
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## Component Hierarchy

```
App
├── AuthProvider
│   └── Router
│       ├── Public Routes
│       │   ├── /login
│       │   ├── /register
│       │   └── /forgot-password
│       │
│       └── Protected Routes
│           └── AppLayout
│               ├── Header
│               │   ├── Logo
│               │   ├── Navigation
│               │   ├── Search
│               │   ├── Notifications
│               │   └── UserMenu
│               │
│               ├── Sidebar
│               │   ├── Dashboard
│               │   ├── Strategies
│               │   ├── Trading
│               │   ├── Backtesting
│               │   ├── Analytics
│               │   └── Settings
│               │
│               └── MainContent
│                   ├── Dashboard
│                   │   ├── PortfolioSummary
│                   │   ├── ActivePositions
│                   │   ├── RecentTrades
│                   │   └── MarketOverview
│                   │
│                   ├── Strategies
│                   │   ├── StrategyList
│                   │   │   └── StrategiesTable
│                   │   ├── StrategyEditor
│                   │   │   ├── ParametersForm
│                   │   │   └── IndicatorConfig
│                   │   └── StrategyBuilder (NL)
│                   │       └── NLPromptInput
│                   │
│                   ├── Trading
│                   │   ├── PaperTrading
│                   │   │   ├── VirtualPortfolio
│                   │   │   ├── QuickTrade
│                   │   │   └── PositionTracker
│                   │   └── LiveTrading
│                   │       ├── OrderBook
│                   │       ├── TradePanel
│                   │       └── PositionManager
│                   │
│                   ├── Backtesting
│                   │   ├── BacktestList
│                   │   ├── BacktestConfig
│                   │   └── ResultsView
│                   │       ├── EquityCurve
│                   │       ├── TradeHistory
│                   │       └── MetricsPanel
│                   │
│                   └── Analytics
│                       ├── ProfitDashboard
│                       ├── PerformanceCharts
│                       └── RiskMetrics
```

## State Management

### Zustand Stores

```typescript
// authStore.ts
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

// strategyStore.ts
interface StrategyState {
  strategies: Strategy[];
  activeStrategy: Strategy | null;
  isLoading: boolean;
  fetchStrategies: () => Promise<void>;
  createStrategy: (data: CreateStrategyDTO) => Promise<void>;
  updateStrategy: (id: string, data: UpdateStrategyDTO) => Promise<void>;
  deleteStrategy: (id: string) => Promise<void>;
}

// tradingStore.ts
interface TradingState {
  positions: Position[];
  orders: Order[];
  balance: VirtualBalance;
  isTrading: boolean;
  placeOrder: (order: OrderRequest) => Promise<void>;
  cancelOrder: (id: string) => Promise<void>;
}
```

## API Integration (TanStack Query)

```typescript
// strategy.hooks.ts
export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyService.getAll(),
  });
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ['strategy', id],
    queryFn: () => strategyService.getById(id),
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => strategyService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}
```

## Real-time Updates (WebSocket)

```typescript
// useWebSocket.ts
export function useMarketData(symbols: string[]) {
  const [prices, setPrices] = useState<Record<string, Price>>({});
  
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/market`);
    
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'subscribe', symbols }));
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPrices(prev => ({ ...prev, [data.symbol]: data }));
    };
    
    return () => ws.close();
  }, [symbols]);
  
  return prices;
}
```

## Authentication Flow

```
1. User enters credentials
2. POST /api/v1/auth/login
3. Receive JWT access + refresh token
4. Store tokens in localStorage
5. Add token to API requests via interceptor
6. On 401, attempt token refresh
7. On refresh failure, redirect to login
```

## File Naming Conventions

- Components: `PascalCase` (e.g., `StrategyList.tsx`)
- Hooks: `camelCase` with `use` prefix (e.g., `useStrategies.ts`)
- Services: `camelCase` with `.service` suffix (e.g., `strategy.service.ts`)
- Types: `PascalCase` with `.types` suffix (e.g., `strategy.types.ts`)
- Utils: `camelCase` (e.g., `formatters.ts`)
- Stores: `camelCase` with `Store` suffix (e.g., `authStore.ts`)
