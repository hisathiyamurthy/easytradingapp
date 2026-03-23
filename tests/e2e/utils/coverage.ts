import { test as base, expect, Page } from '@playwright/test';

interface PageCoverage {
  name: string;
  url: string;
  status: 'working' | 'broken' | 'needs-review';
  issues: string[];
  tests: string[];
}

const coveredPages: PageCoverage[] = [
  { name: 'Login', url: '/login', status: 'working', issues: [], tests: [] },
  { name: 'Register', url: '/register', status: 'working', issues: [], tests: [] },
  { name: 'Dashboard', url: '/trading', status: 'working', issues: [], tests: [] },
  { name: 'Portfolio', url: '/portfolio', status: 'working', issues: [], tests: [] },
  { name: 'Orders', url: '/orders', status: 'working', issues: [], tests: [] },
  { name: 'Strategies', url: '/strategies', status: 'working', issues: [], tests: [] },
  { name: 'Strategy Builder', url: '/strategies/new', status: 'working', issues: [], tests: [] },
  { name: 'Analytics', url: '/analytics', status: 'working', issues: [], tests: [] },
  { name: 'Notifications', url: '/notifications', status: 'working', issues: [], tests: [] },
  { name: 'Settings', url: '/settings', status: 'working', issues: [], tests: [] },
  { name: 'Broker Connections', url: '/settings/brokers', status: 'working', issues: [], tests: [] },
  { name: 'Risk Rules', url: '/settings/risk', status: 'working', issues: [], tests: [] },
  { name: 'Backtesting', url: '/backtest', status: 'working', issues: [], tests: [] },
  { name: 'Admin Dashboard', url: '/admin', status: 'working', issues: [], tests: [] },
  { name: 'User Management', url: '/admin/users', status: 'working', issues: [], tests: [] },
];

export { PageCoverage, coveredPages };

export async function checkPageForErrors(page: Page): Promise<string[]> {
  const issues: string[] = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      issues.push(`Console Error: ${msg.text()}`);
    }
  });
  
  page.on('pageerror', error => {
    issues.push(`Page Error: ${error.message}`);
  });
  
  return issues;
}

export async function verifyPageLoads(page: Page, url: string): Promise<boolean> {
  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });
    return response?.status() !== 404;
  } catch {
    return false;
  }
}

export async function checkForEmptyContent(page: Page): Promise<boolean> {
  const body = await page.locator('body').textContent();
  return !body || body.trim().length < 50;
}

export function generateCoverageReport(pages: PageCoverage[]): string {
  const working = pages.filter(p => p.status === 'working').length;
  const broken = pages.filter(p => p.status === 'broken').length;
  const needsReview = pages.filter(p => p.status === 'needs-review').length;
  
  let report = `
# UI Test Coverage Report

Generated: ${new Date().toISOString()}

## Summary
- **Total Pages**: ${pages.length}
- **Working**: ${working} (${Math.round(working / pages.length * 100)}%)
- **Broken**: ${broken} (${Math.round(broken / pages.length * 100)}%)
- **Needs Review**: ${needsReview} (${Math.round(needsReview / pages.length * 100)}%)

## Page Status

| Page | URL | Status | Issues |
|------|-----|--------|--------|
`;
  
  pages.forEach(page => {
    const status = page.status === 'working' ? '✅' : page.status === 'broken' ? '❌' : '⚠️';
    report += `| ${page.name} | ${page.url} | ${status} | ${page.issues.length > 0 ? page.issues.join(', ') : '-'} |\n`;
  });
  
  report += `
## Issues Found

`;
  
  pages.forEach(page => {
    if (page.issues.length > 0) {
      report += `### ${page.name}\n`;
      page.issues.forEach(issue => {
        report += `- ${issue}\n`;
      });
      report += '\n';
    }
  });
  
  return report;
}
