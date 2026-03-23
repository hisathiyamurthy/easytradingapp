import { test, expect } from '@playwright/test';

test.describe('Strategy Management', () => {
  test('strategies page requires authentication', async ({ page }) => {
    await page.goto('/strategies');
    await expect(page).toHaveURL(/login/);
  });

  test('strategy builder requires authentication', async ({ page }) => {
    await page.goto('/strategies/new');
    await expect(page).toHaveURL(/login/);
  });
});
