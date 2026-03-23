# Frontend Structure

## Page Organization

```
frontend/src/pages/
├── admin/              # Admin pages
│   ├── AdminDashboard.tsx
│   ├── AdminUserManagement.tsx
│   └── AdminSettings.tsx
├── analytics/          # Analytics pages
│   └── Analytics.tsx
├── auth/               # Authentication pages
│   ├── Login.tsx
│   ├── Register.tsx
│   ├── ForgotPassword.tsx
│   └── ResetPassword.tsx
├── backtesting/        # Backtesting pages
│   └── Backtesting.tsx
├── dashboard/          # Main dashboard
│   └── Dashboard.tsx
├── notifications/       # Notifications
│   └── Notifications.tsx
├── orders/             # Order management
│   └── Orders.tsx
├── portfolio/          # Portfolio pages
│   ├── Portfolio.tsx
│   └── Positions.tsx
├── settings/           # User settings
│   ├── Settings.tsx
│   └── Profile.tsx
├── strategies/         # Strategy pages
│   ├── StrategyList.tsx
│   ├── StrategyDetail.tsx
│   └── StrategyBuilder.tsx
└── trading/           # Trading pages
    └── Trading.tsx
```

## Component Structure

```
frontend/src/
├── components/
│   ├── ui/             # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   └── ...
│   ├── Layout.tsx      # Main layout
│   └── ProtectedRoute.tsx
├── hooks/              # Custom React hooks
│   ├── useAuth.ts
│   ├── useStrategies.ts
│   └── useWebSocket.ts
├── services/           # API service modules
│   ├── authApi.ts
│   ├── portfolioApi.ts
│   ├── ordersApi.ts
│   └── ...
├── pages/              # Page components
├── App.tsx             # Main app with routing
└── main.tsx            # Entry point
```

## Routing

Routes are defined in `App.tsx` using React Router:

- `/` - Dashboard
- `/login` - Login
- `/register` - Register
- `/forgot-password` - Forgot Password
- `/strategies` - Strategy List
- `/strategies/builder` - Strategy Builder
- `/strategies/:id` - Strategy Detail
- `/portfolio` - Portfolio
- `/orders` - Orders
- `/trading` - Trading
- `/backtesting` - Backtesting
- `/analytics` - Analytics
- `/settings` - Settings
- `/admin` - Admin Dashboard (admin only)
- `/admin/users` - User Management (admin only)

## State Management

- **Auth State:** LocalStorage + React Context
- **API Data:** React hooks with fetch
- **UI State:** useState/useReducer

## API Integration

API calls use the `fetch` API with the following pattern:

```typescript
const getToken = () => localStorage.getItem('token');

const response = await fetch(`${API_URL}/api/v1/...`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  },
  body: JSON.stringify(data)
});
```

## Environment Variables

```
VITE_API_URL=http://localhost:8000
```

---

*Last Updated: March 2026*
