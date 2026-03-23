import { test, expect } from '@playwright/test';

test('Debug registration flow', async ({ page }) => {
  // Listen to console messages
  page.on('console', msg => {
    console.log(`[BROWSER ${msg.type()}]:`, msg.text());
  });
  
  page.on('pageerror', err => {
    console.log(`[PAGE ERROR]:`, err.message);
  });

  await page.goto('/register');
  await page.waitForLoadState('networkidle');
  
  // Fill form
  await page.fill('input[placeholder="John"]', 'Debug');
  await page.fill('input[placeholder="Doe"]', 'User');
  await page.fill('input[placeholder="name@example.com"]', 'debugtest@test.com');
  await page.fill('input[placeholder="Create a strong password"]', 'Test1234');
  await page.fill('input[placeholder="Confirm your password"]', 'Test1234');
  
  // Click submit
  await page.click('button:has-text("Create Account")');
  
  // Wait and check
  await page.waitForTimeout(5000);
  
  // Get current URL
  console.log('Current URL:', page.url());
  
  // Get page content
  const content = await page.content();
  
  // Check for success elements
  const hasSuccess = content.includes('Registration Successful');
  const hasLoginBtn = content.includes('Go to Login');
  const hasError = content.includes('Registration failed');
  
  console.log('Has success:', hasSuccess);
  console.log('Has login button:', hasLoginBtn);
  console.log('Has error:', hasError);
  
  // Take screenshot
  await page.screenshot({ path: 'debug-register.png', fullPage: true });
  
  // The test passes if we see success content
  expect(hasSuccess || hasLoginBtn).toBeTruthy();
});
