import { test as base, Page } from '@playwright/test';

interface PageError {
  page: string;
  error: string;
  timestamp: string;
}

let capturedErrors: PageError[] = [];

export const test = base.extend({
  page: async ({ page }, use) => {
    capturedErrors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        capturedErrors.push({
          page: page.url(),
          error: `Console: ${msg.text()}`,
          timestamp: new Date().toISOString(),
        });
      }
    });
    
    page.on('pageerror', error => {
      capturedErrors.push({
        page: page.url(),
        error: `Page Error: ${error.message}`,
        timestamp: new Date().toISOString(),
      });
    });
    
    await use(page);
  },
});

export { capturedErrors };
