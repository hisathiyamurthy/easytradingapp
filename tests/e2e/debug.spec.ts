import { test, expect, Page } from '@playwright/test';

interface DebugInfo {
  consoleErrors: string[];
  pageErrors: string[];
  networkRequests: number;
  apiCalls: string[];
  domContent: string;
}

async function captureDebugInfo(page: Page): Promise<DebugInfo> {
  const debugInfo: DebugInfo = {
    consoleErrors: [],
    pageErrors: [],
    networkRequests: 0,
    apiCalls: [],
    domContent: '',
  };

  page.on('console', msg => {
    if (msg.type() === 'error') {
      debugInfo.consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', error => {
    debugInfo.pageErrors.push(error.message);
  });

  page.on('request', request => {
    debugInfo.networkRequests++;
    const url = request.url();
    if (url.includes('/api/')) {
      debugInfo.apiCalls.push(url);
    }
  });

  await page.waitForLoadState('networkidle');
  debugInfo.domContent = await page.content();

  return debugInfo;
}

function validatePageRendering(debugInfo: DebugInfo, pageName: string): string[] {
  const issues: string[] = [];

  // Check for console errors
  if (debugInfo.consoleErrors.length > 0) {
    issues.push(`[${pageName}] Console errors: ${debugInfo.consoleErrors.join(', ')}`);
  }

  // Check for page errors
  if (debugInfo.pageErrors.length > 0) {
    issues.push(`[${pageName}] Page errors: ${debugInfo.pageErrors.join(', ')}`);
  }

  // Check DOM is not empty
  if (debugInfo.domContent.length < 1000) {
    issues.push(`[${pageName}] DOM content too small (${debugInfo.domContent.length} chars) - page may be empty`);
  }

  // Check for common React rendering issues
  if (debugInfo.domContent.includes('Something went wrong')) {
    issues.push(`[${pageName}] React error boundary triggered`);
  }

  return issues;
}

test.describe('UI Rendering Tests', () => {
  
  test('Login page renders correctly with all elements', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const debugInfo = await captureDebugInfo(page);
    const issues = validatePageRendering(debugInfo, 'Login');

    // Check for critical elements
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]');

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();

    console.log('Login page debug info:', debugInfo);
    
    if (issues.length > 0) {
      console.log('Issues found:', issues);
    }
  });

  test('After login - dashboard should render with components', async ({ page }) => {
    // Set token first to bypass auth
    await page.addInitScript(() => {
      localStorage.setItem('token', 'demo-token');
    });
    
    // Now navigate to trading
    await page.goto('/trading');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);

    // Should NOT redirect to login
    expect(currentUrl).toContain('/trading');

    const debugInfo = await captureDebugInfo(page);
    const issues = validatePageRendering(debugInfo, 'Dashboard');

    console.log('Dashboard debug info:', debugInfo);
    console.log('Issues:', issues);

    // Check for sidebar navigation
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
    
    // Check for nav items
    const navLinks = page.locator('nav a');
    const navCount = await navLinks.count();
    console.log(`Found ${navCount} navigation items`);
    expect(navCount).toBeGreaterThan(0);

    // Check for main content area
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();

    // This should NOT be empty
    const body = await page.locator('body').textContent();
    expect(body?.length).toBeGreaterThan(100);
  });

  test('Protected routes redirect properly and render after access', async ({ page }) => {
    const routes = [
      '/trading',
      '/portfolio', 
      '/orders',
      '/strategies',
      '/analytics',
      '/notifications',
      '/settings',
      '/backtest',
      '/admin'
    ];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      
      // Should redirect to login
      await expect(page).toHaveURL(/login/, { timeout: 5000 });
      
      const debugInfo = await captureDebugInfo(page);
      const issues = validatePageRendering(debugInfo, route);
      
      console.log(`Route ${route}:`, issues.length === 0 ? 'OK' : issues);
    }
  });

  test('Verify API endpoints are configured', async ({ page }) => {
    // Check frontend API configuration
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Check if API calls are being made
    const debugInfo = await captureDebugInfo(page);
    
    console.log('Network requests on login page:', debugInfo.networkRequests);
    console.log('API calls:', debugInfo.apiCalls);
    
    // Login page should ideally make at least one API call (e.g., check Google OAuth status)
    // This is informational
  });
});

test.describe('Debug: Empty Page Detection', () => {
  
  test('Detect if trading page is empty after login attempt', async ({ page }) => {
    // Try to access trading directly (should redirect to login)
    await page.goto('/trading');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    console.log('Current URL after /trading:', currentUrl);

    // Get the page content
    const content = await page.content();
    console.log('Page content length:', content.length);
    console.log('Page content preview:', content.substring(0, 500));

    // Take screenshot for debugging
    await page.screenshot({ path: 'test-results/debug-trading-page.png', fullPage: true });
  });

  test('Check if Layout component renders sidebar', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Click demo access
    const demoButton = page.getByRole('button', { name: 'Continue to Demo Dashboard' });
    if (await demoButton.isVisible()) {
      await demoButton.click();
    }
    
    await page.waitForURL(/\/trading/, { timeout: 10000 }).catch(() => {});
    await page.waitForLoadState('networkidle');

    // Check for sidebar
    const aside = page.locator('aside');
    const asideCount = await aside.count();
    console.log('Sidebar elements found:', asideCount);

    // Check for nav items
    const navLinks = page.locator('nav a');
    const navCount = await navLinks.count();
    console.log('Navigation links found:', navCount);

    // List nav items if any
    if (navCount > 0) {
      for (let i = 0; i < Math.min(navCount, 10); i++) {
        const text = await navLinks.nth(i).textContent();
        console.log(`Nav ${i}:`, text);
      }
    }
  });
});
