import { test, expect } from '@playwright/test';

test.describe('Backtesting', () => {
  test('backtesting page requires authentication', async ({ page }) => {
    await page.goto('/backtest');
    await expect(page).toHaveURL(/login/);
  });
});
