import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('unauthenticated access redirects to login', async ({ page }) => {
    await page.goto('/trading');
    await expect(page).toHaveURL(/login/);
  });

  test('portfolio page requires authentication', async ({ page }) => {
    await page.goto('/portfolio');
    await expect(page).toHaveURL(/login/);
  });

  test('orders page requires authentication', async ({ page }) => {
    await page.goto('/orders');
    await expect(page).toHaveURL(/login/);
  });

  test('strategies page requires authentication', async ({ page }) => {
    await page.goto('/strategies');
    await expect(page).toHaveURL(/login/);
  });

  test('analytics page requires authentication', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page).toHaveURL(/login/);
  });

  test('notifications page requires authentication', async ({ page }) => {
    await page.goto('/notifications');
    await expect(page).toHaveURL(/login/);
  });

  test('settings page requires authentication', async ({ page }) => {
    await page.goto('/settings');
    await expect(page).toHaveURL(/login/);
  });

  test('backtest page requires authentication', async ({ page }) => {
    await page.goto('/backtest');
    await expect(page).toHaveURL(/login/);
  });

  test('admin page requires authentication', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/login/);
  });
});
