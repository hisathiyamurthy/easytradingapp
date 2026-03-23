import { test, expect } from '@playwright/test';

test('Debug registration - check actual rendered HTML', async ({ page }) => {
  page.on('console', msg => {
    console.log(`[${msg.type()}]:`, msg.text());
  });
  
  page.on('pageerror', err => {
    console.log('[ERROR]:', err.message);
  });

  await page.goto('/register');
  await page.waitForLoadState('networkidle');
  
  // Fill form
  await page.fill('input[placeholder="John"]', 'Browser');
  await page.fill('input[placeholder="Doe"]', 'Test');
  await page.fill('input[placeholder="name@example.com"]', 'browsertest@test.com');
  await page.fill('input[placeholder="Create a strong password"]', 'Test1234');
  await page.fill('input[placeholder="Confirm your password"]', 'Test1234');
  
  // Click submit
  await page.click('button:has-text("Create Account")');
  
  // Wait longer
  await page.waitForTimeout(5000);
  
  // Get the #root content to see what's actually rendered
  const rootContent = await page.locator('#root').innerHTML();
  console.log('=== ROOT CONTENT ===');
  console.log(rootContent.substring(0, 2000));
  
  // Check body text
  const bodyText = await page.locator('body').innerText();
  console.log('=== BODY TEXT ===');
  console.log(bodyText);
  
  // Take screenshot
  await page.screenshot({ path: 'browser-debug.png', fullPage: true });
});
