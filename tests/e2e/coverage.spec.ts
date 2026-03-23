import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface PageStatus {
  name: string;
  url: string;
  status: 'working' | 'broken' | 'needs-review';
  issues: string[];
  screenshot?: string;
}

const pagesToTest: { name: string; url: string }[] = [
  { name: 'Login', url: '/login' },
  { name: 'Register', url: '/register' },
  { name: 'Dashboard', url: '/trading' },
  { name: 'Portfolio', url: '/portfolio' },
  { name: 'Orders', url: '/orders' },
  { name: 'Strategies', url: '/strategies' },
  { name: 'Analytics', url: '/analytics' },
  { name: 'Notifications', url: '/notifications' },
  { name: 'Settings', url: '/settings' },
  { name: 'Broker Connections', url: '/settings/brokers' },
  { name: 'Risk Rules', url: '/settings/risk' },
  { name: 'Backtesting', url: '/backtest' },
  { name: 'Admin Dashboard', url: '/admin' },
  { name: 'User Management', url: '/admin/users' },
];

test.describe('UI Coverage Test', () => {
  const results: PageStatus[] = [];

  for (const pageInfo of pagesToTest) {
    test(`Page: ${pageInfo.name} (${pageInfo.url})`, async ({ page }) => {
      const errors: string[] = [];
      let pageLoaded = false;

      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(`Console Error: ${msg.text()}`);
        }
      });

      page.on('pageerror', error => {
        errors.push(`JS Error: ${error.message}`);
      });

      try {
        const response = await page.goto(pageInfo.url, { 
          waitUntil: 'domcontentloaded', 
          timeout: 15000 
        });
        
        if (response?.status() === 404) {
          results.push({
            name: pageInfo.name,
            url: pageInfo.url,
            status: 'broken',
            issues: ['Page returned 404 - Not Found'],
          });
          return;
        }

        await page.waitForTimeout(2000);
        
        const title = await page.title();
        const bodyContent = await page.locator('body').textContent();
        
        if (!bodyContent || bodyContent.trim().length < 10) {
          errors.push('Page appears to be empty or not loaded properly');
        }

        pageLoaded = true;
      } catch (e: unknown) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        errors.push(`Navigation failed: ${errorMessage}`);
      }

      const criticalErrors = errors.filter(e => 
        !e.includes('favicon') && 
        !e.includes('404') &&
        !e.includes('network')
      );

      const status: 'working' | 'broken' | 'needs-review' = 
        !pageLoaded ? 'broken' : 
        criticalErrors.length > 2 ? 'broken' :
        criticalErrors.length > 0 ? 'needs-review' : 'working';

      results.push({
        name: pageInfo.name,
        url: pageInfo.url,
        status,
        issues: errors,
      });

      if (status !== 'working') {
        const screenshotPath = path.join(__dirname, '../../playwright-report', 'screenshots', `${pageInfo.name.replace(/\s+/g, '-').toLowerCase()}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
      }

      expect(pageLoaded).toBe(true);
    });
  }

  test.afterAll(async () => {
    const report = generateReport(results);
    const reportPath = path.join(__dirname, '../../playwright-report', 'coverage-report.md');
    fs.writeFileSync(reportPath, report);
    console.log('\n' + report);
  });
});

function generateReport(results: PageStatus[]): string {
  const working = results.filter(r => r.status === 'working');
  const broken = results.filter(r => r.status === 'broken');
  const needsReview = results.filter(r => r.status === 'needs-review');

  let report = `# UI Test Coverage Report

Generated: ${new Date().toISOString()}

---

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Pages** | ${results.length} | 100% |
| **Working** | ${working.length} | ${Math.round(working.length / results.length * 100)}% |
| **Needs Review** | ${needsReview.length} | ${Math.round(needsReview.length / results.length * 100)}% |
| **Broken** | ${broken.length} | ${Math.round(broken.length / results.length * 100)}% |

---

## Page Status Details

### Working Pages ✅
`;
  
  if (working.length === 0) {
    report += '_No pages marked as working_\n';
  } else {
    working.forEach(p => {
      report += `- ${p.name} (${p.url})\n`;
    });
  }

  report += `
### Pages Needing Review ⚠️
`;
  
  if (needsReview.length === 0) {
    report += '_No pages need review_\n';
  } else {
    needsReview.forEach(p => {
      report += `- **${p.name}** (${p.url})\n`;
      p.issues.forEach(issue => {
        report += `  - ${issue}\n`;
      });
    });
  }

  report += `
### Broken Pages ❌
`;
  
  if (broken.length === 0) {
    report += '_No broken pages detected_\n';
  } else {
    broken.forEach(p => {
      report += `- **${p.name}** (${p.url})\n`;
      p.issues.forEach(issue => {
        report += `  - ${issue}\n`;
      });
    });
  }

  report += `
---

## Test Commands

Run all tests:
\`\`\`bash
npx playwright test
\`\`\`

Run with UI:
\`\`\`bash
npx playwright test --ui
\`\`\`

Run headed:
\`\`\`bash
npx playwright test --headed
\`\`\`

View report:
\`\`\`bash
npx playwright show-report
\`\`\`

---

## Notes

- Tests automatically capture screenshots for failed/broken pages
- Screenshots are saved to: \`playwright-report/screenshots/\`
- HTML report available at: \`playwright-report/index.html\`
`;

  return report;
}
