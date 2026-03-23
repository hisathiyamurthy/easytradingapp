import { test, expect } from '@playwright/test';

test.describe('Admin Panel', () => {
  test('admin dashboard requires authentication', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/login/);
  });

  test('user management requires authentication', async ({ page }) => {
    await page.goto('/admin/users');
    await expect(page).toHaveURL(/login/);
  });
});
