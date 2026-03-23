import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('login page loads successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/EasyTrading/i);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button:has-text("Sign in")')).toBeVisible();
  });

  test('protected routes redirect to login', async ({ page }) => {
    await page.goto('/trading');
    await expect(page).toHaveURL(/login/);
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test('login form has required fields', async ({ page }) => {
    await expect(page.locator('input[placeholder="name@example.com"]')).toBeVisible();
    await expect(page.locator('input[placeholder="Enter your password"]')).toBeVisible();
    await expect(page.locator('text=Remember me')).toBeVisible();
  });

  test('login button is clickable', async ({ page }) => {
    const loginButton = page.locator('button:has-text("Sign in")');
    await expect(loginButton).toBeVisible();
    await expect(loginButton).toBeEnabled();
  });

  test('signup link is accessible', async ({ page }) => {
    await page.getByRole('link', { name: 'Sign up' }).click();
    await expect(page).toHaveURL(/register/);
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible();
  });

  test('forgot password link is clickable', async ({ page }) => {
    const forgotLink = page.getByRole('link', { name: 'Forgot password?' });
    await expect(forgotLink).toBeVisible();
    await expect(forgotLink).toBeEnabled();
  });

  test('branding elements are visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'EasyTrade' })).toBeVisible();
    await expect(page.locator('text=Professional algorithmic trading')).toBeVisible();
  });

  test('remember me checkbox is present', async ({ page }) => {
    await expect(page.locator('text=Remember me')).toBeVisible();
    const checkbox = page.locator('input[type="checkbox"]');
    await expect(checkbox).toBeVisible();
    await expect(checkbox).not.toBeChecked();
  });
});
