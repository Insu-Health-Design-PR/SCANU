import { test, expect } from '@playwright/test';

const LAYOUT_OPTION_2_CAMERAS = '[data-testid="layout-option-2-cameras"]';
const VIEW_LAYOUT_BUTTON = '[data-testid="view-layout-button"]';
const OPEN_PREVIEW_BUTTON = '[data-testid="open-layout-preview"]';
const APPLY_LAYOUT_BUTTON = '[data-testid="apply-layout"]';

const PREFS_KEY = 'scanu-layer8-ui-prefs';

test('layout flow persists after refresh', async ({ page }) => {
  await page.goto('/');

  await page.click(VIEW_LAYOUT_BUTTON);
  await page.click(LAYOUT_OPTION_2_CAMERAS);
  await page.click(OPEN_PREVIEW_BUTTON);

  await expect(page.getByText('Layout Preview: 2 Cameras')).toBeVisible();
  await page.click(APPLY_LAYOUT_BUTTON);

  await expect(page.getByText('RGB Camera')).toBeVisible();
  await expect(page.getByText('Thermal Camera')).toBeVisible();

  const beforeReload = await page.evaluate((key) => {
    return window.localStorage.getItem(key);
  }, PREFS_KEY);

  expect(beforeReload).toBeTruthy();
  expect(beforeReload ?? '').toContain('2 Cameras');

  await page.reload();

  const afterReload = await page.evaluate((key) => {
    return window.localStorage.getItem(key);
  }, PREFS_KEY);

  expect(afterReload).toBe(beforeReload);
});
