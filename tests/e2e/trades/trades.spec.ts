import { test, expect } from '@playwright/test';

test.describe('Trading', () => {
  test('orders page requires authentication', async ({ page }) => {
    await page.goto('/orders');
    await expect(page).toHaveURL(/login/);
  });
});
