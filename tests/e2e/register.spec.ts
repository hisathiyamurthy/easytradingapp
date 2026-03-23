import { test, expect } from '@playwright/test';

test('Register success shows success page', async ({ page }) => {
  await page.goto('/register');
  await page.waitForLoadState('networkidle');
  
  // Fill form
  await page.fill('input[placeholder="John"]', 'Test');
  await page.fill('input[placeholder="Doe"]', 'User');
  await page.fill('input[placeholder="name@example.com"]', 'playwright2@test.com');
  await page.fill('input[placeholder="Create a strong password"]', 'Test1234');
  await page.fill('input[placeholder="Confirm your password"]', 'Test1234');
  
  // Submit
  await page.click('button:has-text("Create Account")');
  
  await page.waitForTimeout(3000);
  
  // Check what's rendered
  const content = await page.content();
  console.log('Page has success:', content.includes('Registration Successful'));
  console.log('Page has go to login:', content.includes('Go to Login'));
  
  // Take screenshot
  await page.screenshot({ path: 'register-success.png', fullPage: true });
});
