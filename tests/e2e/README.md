# E2E Testing with Playwright

This directory contains end-to-end tests for the EasyTradingApp algorithmic trading platform.

## Directory Structure

```
tests/e2e/
├── auth/              # Authentication tests
│   └── auth.spec.ts
├── dashboard/         # Dashboard tests
│   └── dashboard.spec.ts
├── broker/           # Broker integration tests
│   └── broker.spec.ts
├── strategy/         # Strategy management tests
│   └── strategy.spec.ts
├── trades/           # Trading/Orders tests
│   └── trades.spec.ts
├── backtesting/      # Backtesting tests
│   └── backtesting.spec.ts
├── admin/            # Admin panel tests
│   └── admin.spec.ts
├── utils/            # Test utilities
│   ├── test-utils.ts
│   ├── coverage.ts
│   └── global-test.ts
└── coverage.spec.ts  # Coverage report generator
```

## Prerequisites

1. Install dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install chromium
```

## Running Tests

### Run all E2E tests
```bash
npm run test:e2e
```

### Run tests with UI
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (see browser)
```bash
npm run test:e2e:headed
```

### View test report
```bash
npm run test:e2e:report
```

### Run specific test file
```bash
npx playwright test tests/e2e/auth/auth.spec.ts
```

### Run tests by tag
```bash
npx playwright test --grep "@auth"
```

## Test Coverage

The test suite covers:

### Authentication
- Login page loads
- Successful login with valid credentials
- Invalid login error handling
- Empty field validation
- Logout functionality
- Register page access

### Dashboard
- Dashboard page loads
- Portfolio stats display
- Portfolio chart display
- Market overview
- Recent orders
- Navigation to all pages

### Broker Integration
- Broker connections page
- Add broker dialog
- Broker form validation
- Test connection button
- Settings navigation

### Strategy Management
- Strategies page loads
- Create new strategy
- Strategy filters
- Grid/List view toggle
- Edit strategy
- Delete strategy
- Strategy stats

### Trading/Orders
- Orders page loads
- Orders table display
- Order status filters
- Order columns
- Empty state handling

### Backtesting
- Backtesting page loads
- Configuration inputs
- Run backtest
- Results display

### Admin Panel
- Admin dashboard access
- User management page
- User table display
- Approve user functionality

## Test Reports

Reports are generated in:
- HTML: `playwright-report/index.html`
- JSON: `playwright-report/test-results.json`
- Coverage: `playwright-report/coverage-report.md`

## Configuration

Edit `playwright.config.ts` to customize:
- Base URL
- Test timeout
- Retry settings
- Browser selection
- Screenshot/video settings

## Environment Variables

- `FRONTEND_URL`: Override frontend URL (default: http://localhost:5173)
- `CI`: Enable CI mode (more retries, less parallelism)
