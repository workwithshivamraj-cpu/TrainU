import { expect, test } from '@playwright/test';

/**
 * Critical-path smoke tests against the seeded demo data. These require the
 * full stack (backend + Postgres + Redis + MinIO + frontend) to be running
 * — see docs/operations.md for how to bring it up locally or in CI.
 */

const OWNER_EMAIL = 'owner@portfolioteam.example';
const VIEWER_EMAIL = 'viewer@portfolioteam.example';
const PASSWORD = 'TrainU_Demo123!';

test.describe('Authentication', () => {
  test('rejects an invalid login', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', OWNER_EMAIL);
    await page.fill('#password', 'wrong-password');
    await page.click('button[type=submit]');
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page).toHaveURL(/login/);
  });

  test('signs in with demo credentials and reaches the dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', OWNER_EMAIL);
    await page.fill('#password', PASSWORD);
    await page.click('button[type=submit]');
    await page.waitForURL('**/dashboard');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });
});

test.describe('Ask TrainU', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', OWNER_EMAIL);
    await page.fill('#password', PASSWORD);
    await page.click('button[type=submit]');
    await page.waitForURL('**/dashboard');
  });

  test('answers a seeded question with a cited, playable source', async ({ page }) => {
    await page.goto('/assistant');
    await page.fill('#question', 'How do I create a new client account?');
    await page.click('button[type=submit]');

    await expect(page.getByText('Confidence:')).toBeVisible({ timeout: 15000 });

    // Citation timestamps are shown in mm:ss form, e.g. "0:00–0:31".
    await expect(page.locator('text=/\\d+:\\d{2}–\\d+:\\d{2}/').first()).toBeVisible();

    // Clicking a citation loads the video player with the source clip.
    await page.locator('button:has-text("ClientVantage KT")').first().click();
    await expect(page.getByText('Source clip')).toBeVisible();
    await expect(page.locator('video')).toBeVisible();
  });

  test('returns the fixed no-answer response for an out-of-scope question', async ({ page }) => {
    await page.goto('/assistant');
    await page.fill('#question', 'What is the capital of France?');
    await page.click('button[type=submit]');
    await expect(page.getByText(/could not find an approved source/i)).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Role-based access', () => {
  test('viewer does not see admin navigation or content-owner actions', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', VIEWER_EMAIL);
    await page.fill('#password', PASSWORD);
    await page.click('button[type=submit]');
    await page.waitForURL('**/dashboard');

    await expect(page.getByRole('link', { name: 'Users & Roles' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Org Settings' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Upload a source' })).toHaveCount(0);

    // Direct navigation to an admin route is redirected away.
    await page.goto('/admin/users');
    await page.waitForURL('**/dashboard');
  });
});
