import { test as base } from '@playwright/test';
import { Page } from '@playwright/test';

export interface TestUser {
  email: string;
  password: string;
}

export const TEST_USER: TestUser = {
  email: 'trader@demo.com',
  password: 'Demo@123',
};

export const ADMIN_USER: TestUser = {
  email: 'admin@demo.com',
  password: 'Admin@123',
};

export interface PageErrors {
  consoleErrors: string[];
  pageErrors: string[];
  failedApiCalls: number;
}

export async function capturePageErrors(page: Page): Promise<PageErrors> {
  const errors: PageErrors = {
    consoleErrors: [],
    pageErrors: [],
    failedApiCalls: 0,
  };

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', (error) => {
    errors.pageErrors.push(error.message);
  });

  page.on('response', (response) => {
    if (response.status() >= 400) {
      errors.failedApiCalls++;
    }
  });

  return errors;
}

export async function waitForPageLoad(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
}

export async function loginUser(page: Page, user: TestUser): Promise<void> {
  await page.goto('/login');
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(trading|dashboard)/);
}

export async function logoutUser(page: Page): Promise<void> {
  await page.click('button:has-text("Logout")');
  await page.waitForURL('/login');
}

export { expect } from '@playwright/test';
