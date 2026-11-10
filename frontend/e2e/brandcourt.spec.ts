import { test, expect } from '@playwright/test'
const email = `brandcourt-e2e-${Date.now()}@example.com`

test('signed-out visit to / shows landing page and Create workspace opens sign-up', async ({ page }) => {
  test.setTimeout(60000)
  await page.goto('/')
  // Landing page headline must be visible
  await expect(page.getByRole('heading', { level: 1, name: /Every claim needs proof/i })).toBeVisible()
  // Click 'Create workspace' button
  const createBtn = page.getByRole('link', { name: /Create workspace/i }).first()
  await createBtn.click()
  // Should open registration form
  await expect(page.getByRole('heading', { name: 'Create your workspace' })).toBeVisible()
})

test('workspace registration, content creation and navigation smoke test', async ({ page }) => {
  test.setTimeout(60000)
  await page.goto('/signup')
  await expect(page.getByRole('heading', { name: 'Create your workspace' })).toBeVisible()
  await page.getByLabel('Workspace name').fill('BrandCourt E2E')
  await page.getByLabel('Your full name').fill('E2E Reviewer')
  await page.getByLabel('Work email').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill('SafeDemoPass!234')
  await page.getByRole('button', { name: /Create workspace/ }).click()
  await expect(page.getByRole('heading', { name: 'Insights dashboard' })).toBeVisible({ timeout: 15000 })
  await page.getByRole('link', { name: /Content Reviews/i }).click()
  await expect(page.getByRole('heading', { name: 'Content Reviews' })).toBeVisible()
  await page.getByRole('button', { name: /New Review/i }).click()
  await page.getByLabel(/Content Title/i).fill('E2E GlowSerum draft')
  await page.getByLabel(/Caption \/ Marketing Copy/i).fill('GlowSerum is a lightweight step in your evening routine.')
  await page.getByRole('button', { name: /Create Review/i }).click()
  await expect(page.getByRole('heading', { name: 'E2E GlowSerum draft' })).toBeVisible({ timeout: 10000 })
})
