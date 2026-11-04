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
  await expect(page.getByText('YOUR BRAND, WITH EVIDENCE')).toBeVisible({ timeout: 15000 })
  await page.getByRole('link', { name: /Content reviews/ }).click()
  await expect(page.getByRole('heading', { name: /Content review & Claim Court/ })).toBeVisible()
  await page.getByRole('button', { name: /New content/ }).click()
  await page.getByLabel('Content title').fill('E2E GlowSerum draft')
  await page.getByLabel('Caption / marketing copy').fill('GlowSerum is a lightweight step in your evening routine.')
  await page.getByRole('button', { name: /Create draft/ }).click()
  await expect(page.getByText('E2E GlowSerum draft')).toBeVisible({ timeout: 10000 })
})
