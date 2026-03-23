import { test, expect } from '@playwright/test';

test.describe('Broker Integration', () => {
  test('broker page requires authentication', async ({ page }) => {
    await page.goto('/settings/brokers');
    await expect(page).toHaveURL(/login/);
  });

  test('risk rules page requires authentication', async ({ page }) => {
    await page.goto('/settings/risk');
    await expect(page).toHaveURL(/login/);
  });
});
