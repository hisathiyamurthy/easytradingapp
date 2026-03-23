# EasyTradingApp Bug Tracker

## Bug ID: BUG-001
**Module:** Routing
**Page URL:** /trading
**Steps to Reproduce:**
1. Navigate to /trading without authentication
2. The page redirects to /login (expected)
3. Login with demo access
4. Observe that it doesn't use the TradingDashboard component

**Expected Result:** Trading page should use the TradingDashboard component with positions/orders/place order functionality

**Actual Result:** The /trading route uses Dashboard component instead of TradingDashboard component

**Root Cause:** In App.tsx line 66, `/trading` points to Dashboard instead of the actual TradingDashboard component that has the trading functionality

**Severity:** High
**Status:** RESOLVED ✓

---

## Bug ID: BUG-002
**Module:** TradingDashboard
**Page URL:** (Not routed)
**Steps to Reproduce:**
1. Check the frontend/src/pages/trading/TradingDashboard.tsx file
2. Notice it exists but is not connected to any route

**Expected Result:** TradingDashboard should be accessible at /trading route

**Actual Result:** TradingDashboard exists but has no route - it's completely unused

**Severity:** High
**Status:** RESOLVED ✓

---

## Bug ID: BUG-003
**Module:** API Services
**Page URL:** Multiple
**Steps to Reproduce:**
1. Check frontend/src/services directory
2. Look for hooks that use the API services

**Expected Result:** All pages should use API services for data

**Actual Result:** TradingDashboard.tsx uses placeholder hooks with empty data

**Severity:** Medium
**Status:** RESOLVED ✓

---

## Bug ID: BUG-004
**Module:** Settings Page
**Page URL:** /settings
**Steps to Reproduce:**
1. Navigate to /settings
2. Look for navigation links to Broker Connections and Risk Rules

**Expected Result:** Settings page should have clear navigation to sub-pages

**Actual Result:** Need to verify Settings.tsx content

**Severity:** Low
**Status:** OPEN

---

## Bug ID: BUG-005
**Module:** Admin Access
**Page URL:** /admin
**Steps to Reproduce:**
1. Try to access /admin without admin role

**Expected Result:** Should show access denied or redirect

**Actual Result:** Currently just checks authentication but not role

**Severity:** Medium
**Status:** OPEN

---

## Bug ID: BUG-006
**Module:** Login / Demo Access
**Page URL:** /login
**Steps to Reproduce:**
1. Go to /login
2. Click "Continue to Demo Dashboard" button

**Expected Result:** Should navigate to /trading with dashboard visible

**Actual Result:** Page stays at /login - navigate() is blocked by ProtectedRoute

**Root Cause:** The demo button uses React Router's navigate() but ProtectedRoute intercepts the request before it renders the protected page

**Severity:** Critical
**Status:** FIXED (code changed, needs rebuild)
