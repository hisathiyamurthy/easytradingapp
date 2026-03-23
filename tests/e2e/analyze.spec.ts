import { test, expect, Page } from '@playwright/test';

interface PageAnalysis {
  url: string;
  title: string;
  domElements: number;
  forms: number;
  buttons: number;
  links: number;
  apiCalls: string[];
  consoleErrors: string[];
  jsErrors: string[];
  reactRoot: boolean;
  isEmpty: boolean;
}

async function analyzePage(page: Page, url: string): Promise<PageAnalysis> {
  const analysis: PageAnalysis = {
    url,
    title: '',
    domElements: 0,
    forms: 0,
    buttons: 0,
    links: 0,
    apiCalls: [],
    consoleErrors: [],
    jsErrors: [],
    reactRoot: false,
    isEmpty: true,
  };

  // Capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      analysis.consoleErrors.push(msg.text());
    }
  });

  // Capture JS errors
  page.on('pageerror', error => {
    analysis.jsErrors.push(error.message);
  });

  // Capture API calls
  page.on('response', response => {
    const url = response.url();
    if (url.includes('/api/')) {
      analysis.apiCalls.push(`${response.status()} - ${url}`);
    }
  });

  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });

  analysis.title = await page.title();
  
  // Count DOM elements
  analysis.domElements = await page.locator('*').count();
  analysis.forms = await page.locator('form').count();
  analysis.buttons = await page.locator('button').count();
  analysis.links = await page.locator('a').count();
  
  // Check React root
  analysis.reactRoot = await page.locator('#root').count() > 0;
  
  // Check if page is empty
  const body = await page.locator('body').textContent();
  analysis.isEmpty = !body || body.trim().length < 100;

  return analysis;
}

test.describe('Comprehensive UI Analysis', () => {
  
  test('1. Login Page Analysis', async ({ page }) => {
    const analysis = await analyzePage(page, '/login');
    
    console.log('\n=== LOGIN PAGE ANALYSIS ===');
    console.log('Title:', analysis.title);
    console.log('DOM Elements:', analysis.domElements);
    console.log('Forms:', analysis.forms);
    console.log('Buttons:', analysis.buttons);
    console.log('Links:', analysis.links);
    console.log('React Root:', analysis.reactRoot);
    console.log('Is Empty:', analysis.isEmpty);
    console.log('API Calls:', analysis.apiCalls);
    console.log('Console Errors:', analysis.consoleErrors);
    console.log('JS Errors:', analysis.jsErrors);

    // Assertions
    expect(analysis.reactRoot).toBe(true);
    expect(analysis.isEmpty).toBe(false);
    expect(analysis.forms).toBeGreaterThan(0);
    expect(analysis.buttons).toBeGreaterThan(0);
  });

  test('2. Trading Page (Protected) Analysis', async ({ page }) => {
    const analysis = await analyzePage(page, '/trading');
    
    console.log('\n=== TRADING PAGE ANALYSIS ===');
    console.log('URL after navigation:', page.url());
    console.log('Title:', analysis.title);
    console.log('DOM Elements:', analysis.domElements);
    console.log('React Root:', analysis.reactRoot);
    console.log('Is Empty:', analysis.isEmpty);
    console.log('API Calls:', analysis.apiCalls);
    console.log('Console Errors:', analysis.consoleErrors);
    console.log('JS Errors:', analysis.jsErrors);

    // Check if redirected to login
    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);
    
    if (currentUrl.includes('/login')) {
      console.log('✓ Correctly redirected to login (protected)');
    } else if (analysis.isEmpty) {
      console.log('❌ PROBLEM: Page loaded but is empty!');
    }
  });

  test('3. Direct Trading URL with Token', async ({ page }) => {
    // Set token first
    await page.addInitScript(() => {
      localStorage.setItem('token', 'demo-token');
    });
    
    const analysis = await analyzePage(page, '/trading');
    
    console.log('\n=== TRADING PAGE WITH TOKEN ===');
    console.log('URL:', page.url());
    console.log('DOM Elements:', analysis.domElements);
    console.log('Buttons:', analysis.buttons);
    console.log('Links:', analysis.links);
    console.log('Is Empty:', analysis.isEmpty);
    console.log('API Calls:', analysis.apiCalls);
    console.log('Console Errors:', analysis.consoleErrors);
    console.log('JS Errors:', analysis.jsErrors);

    // After setting token, should access trading
    if (!page.url().includes('/login')) {
      expect(analysis.domElements).toBeGreaterThan(100);
    }
  });

  test('4. All Routes Analysis', async ({ page }) => {
    const routes = [
      '/login',
      '/register', 
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

    console.log('\n=== ALL ROUTES ANALYSIS ===\n');
    
    for (const route of routes) {
      const analysis = await analyzePage(page, route);
      const redirected = page.url().includes('/login');
      
      console.log(`${route}:`);
      console.log(`  → Redirected to login: ${redirected}`);
      console.log(`  → DOM Elements: ${analysis.domElements}`);
      console.log(`  → API Calls: ${analysis.apiCalls.length}`);
      console.log(`  → Errors: ${analysis.jsErrors.length + analysis.consoleErrors.length}`);
      console.log(`  → Is Empty: ${analysis.isEmpty}`);
    }
  });

  test('5. Check React App Mounting', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    console.log('\n=== REACT MOUNTING CHECK ===');
    
    // Check if React root exists
    const root = await page.locator('#root').innerHTML();
    console.log('React root content length:', root.length);
    console.log('React root content preview:', root.substring(0, 200));
    
    // Check for React-specific elements
    const hasForm = await page.locator('form').count() > 0;
    const hasInput = await page.locator('input').count() > 0;
    const hasButton = await page.locator('button').count() > 0;
    
    console.log('Has Form:', hasForm);
    console.log('Has Input:', hasInput);
    console.log('Has Button:', hasButton);
    
    expect(hasInput).toBe(true);
    expect(hasButton).toBe(true);
  });

  test('6. Check API Configuration', async ({ page }) => {
    // Check what API URL is being used
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    console.log('\n=== API CONFIGURATION CHECK ===');
    
    // Try to evaluate the API URL from the frontend
    const apiUrl = await page.evaluate(() => {
      // @ts-ignore
      return window.__env?.VITE_API_URL || 'http://localhost:8000';
    }).catch(() => 'not found');
    
    console.log('API URL from env:', apiUrl);
    
    // Check if there are any fetch requests
    const analysis = await analyzePage(page, '/login');
    console.log('API calls made on login page:', analysis.apiCalls.length);
    
    if (analysis.apiCalls.length === 0) {
      console.log('⚠️ WARNING: No API calls made on login page!');
    }
  });

  test('7. Check Protected Route Behavior', async ({ page }) => {
    console.log('\n=== PROTECTED ROUTE BEHAVIOR ===');
    
    // Without token
    await page.goto('/trading');
    await page.waitForLoadState('networkidle');
    console.log('Without token → URL:', page.url());
    
    // With token
    await page.addInitScript(() => {
      localStorage.setItem('token', 'demo-token');
    });
    
    await page.goto('/trading');
    await page.waitForLoadState('networkidle');
    console.log('With token → URL:', page.url());
    
    // Check what's rendered
    const content = await page.content();
    console.log('Has sidebar:', content.includes('aside'));
    console.log('Has navigation:', content.includes('nav'));
    console.log('Has main:', content.includes('main'));
  });
});
