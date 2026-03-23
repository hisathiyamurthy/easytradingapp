import { test, expect, Page } from '@playwright/test';

async function debugPage(page: Page, url: string) {
  console.log(`\n=== DEBUGGING: ${url} ===`);
  
  page.on('console', msg => {
    console.log(`[CONSOLE ${msg.type()}]:`, msg.text());
  });
  
  page.on('pageerror', err => {
    console.log(`[PAGE ERROR]:`, err.message);
  });

  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  
  const content = await page.content();
  console.log('Content length:', content.length);
  console.log('Root content:', await page.locator('#root').innerHTML().catch(() => 'EMPTY'));
  console.log('URL:', page.url());
}

test('Debug login page', async ({ page }) => {
  await debugPage(page, '/login');
});

test('Debug trading with token', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'demo-token');
  });
  await debugPage(page, '/trading');
});
