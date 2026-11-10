/**
 * Full GlowSerum compliance flow:
 *   Creator → submit content
 *   Reviewer → review findings, override one with reason
 *   Manager  → approve the content
 *
 * Uses the demo Aurora Brand workspace seeded at startup.
 * Run with:  npx playwright test e2e/glowserum-flow.spec.ts
 */
import { test, expect, type Page } from '@playwright/test'

// Helpers ----------------------------------------------------------------

/** Register a fresh workspace and return the signed-in page. */
async function signUpAndSignIn(
  page: Page,
  role: 'creator' | 'reviewer' | 'manager',
  workspaceName: string,
): Promise<{ email: string; password: string }> {
  const ts = Date.now()
  const email = `${role}-${ts}@example.com`
  const password = 'GlowSerum#2026!'

  await page.goto('/signup')
  await expect(page.getByRole('heading', { name: 'Create your workspace' })).toBeVisible()
  await page.getByLabel('Workspace name').fill(workspaceName)
  await page.getByLabel('Your full name').fill(`${role.charAt(0).toUpperCase() + role.slice(1)} Test`)
  await page.getByLabel('Work email').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill(password)
  await page.getByRole('button', { name: /Create workspace/ }).click()
  await expect(page.getByRole('heading', { name: 'Insights dashboard' })).toBeVisible({ timeout: 20000 })
  return { email, password }
}

// Tests ------------------------------------------------------------------

test.describe('GlowSerum full compliance flow', () => {
  test.setTimeout(120_000)

  test('creator can create GlowSerum content and submit for review', async ({ page }) => {
    const ws = `GlowSerum-Creator-${Date.now()}`
    const { email, password } = await signUpAndSignIn(page, 'creator', ws)
    void email; void password // used implicitly for session

    // Navigate to Content reviews
    await page.getByRole('link', { name: /Content Reviews/i }).click()
    await expect(page.getByRole('heading', { name: 'Content Reviews' })).toBeVisible()

    // Open new review form
    await page.getByRole('button', { name: /New Review/i }).click()

    // Fill in clean GlowSerum content so it can be submitted without unresolved blockers
    await page.getByLabel(/Content Title/i).fill('GlowSerum Evening Glow Campaign')
    await page.getByLabel(/Caption \/ Marketing Copy/i).fill(
      'Enjoy a gentle daily evening routine with GlowSerum.',
    )

    const channelSelect = page.getByLabel(/Target Channel/i)
    if (await channelSelect.isVisible()) {
      await channelSelect.selectOption({ index: 1 })
    }

    await page.getByRole('button', { name: /Create Review/i }).click()

    // Redirected to ReviewDetailPage
    await expect(page.getByRole('heading', { name: 'GlowSerum Evening Glow Campaign' })).toBeVisible({ timeout: 15000 })

    // Run Claim Court check and submit for review
    await page.getByRole('button', { name: /Run Claim Court Check/i }).click()
    await expect(page.getByTestId('review-progress')).toContainText(/completed/i, { timeout: 25000 })

    const submitBtn = page.getByRole('button', { name: /Submit for Review/i })
    await expect(submitBtn).toBeEnabled({ timeout: 10000 })
    await submitBtn.click()
    await expect(page.getByText(/submitted/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('reviewer can view findings and override one with a written reason', async ({ page }) => {
    const ws = `GlowSerum-Reviewer-${Date.now()}`
    await signUpAndSignIn(page, 'reviewer', ws)

    // Create a content item with a claim that triggers a finding
    await page.goto('/app/reviews')
    await page.getByRole('button', { name: /New Review/i }).click()
    await page.getByLabel(/Content Title/i).fill('GlowSerum Reviewer Test')
    await page.getByLabel(/Caption \/ Marketing Copy/i).fill('Clinically proven to erase wrinkles overnight, guaranteed!')
    await page.getByRole('button', { name: /Create Review/i }).click()
    await expect(page.getByRole('heading', { name: 'GlowSerum Reviewer Test' })).toBeVisible({ timeout: 15000 })

    // Run Claim Court Check and wait for findings
    await page.getByRole('button', { name: /Run Claim Court Check/i }).click()
    await expect(page.getByTestId('finding-card').first()).toBeVisible({ timeout: 25000 })

    // Open Approvals / Workflow view where reviewer Override decision is available
    await page.goto('/app/approvals')
    await expect(page.getByLabel('Select content item')).toBeVisible({ timeout: 10000 })
    const overrideBtn = page.getByRole('button', { name: /^Override$/i }).first()
    await expect(overrideBtn).toBeVisible({ timeout: 10000 })

    page.once('dialog', async (dialog) => {
      await dialog.accept('Marketing claim has supporting clinical study on file, ref CS-2026-04.')
    })
    await overrideBtn.click()

    await expect(page.getByText(/Finding decision recorded: override/i)).toBeVisible({ timeout: 10000 })
  })

  test('manager can approve content after all blockers resolved', async ({ page }) => {
    const ws = `GlowSerum-Manager-${Date.now()}`
    await signUpAndSignIn(page, 'manager', ws)

    // Create clean content item that can be approved
    await page.goto('/app/reviews')
    await page.getByRole('button', { name: /New Review/i }).click()
    await page.getByLabel(/Content Title/i).fill('GlowSerum Manager Approve Test')
    await page.getByLabel(/Caption \/ Marketing Copy/i).fill('Our gentle daily formula is soothing on skin.')
    await page.getByRole('button', { name: /Create Review/i }).click()
    await expect(page.getByRole('heading', { name: 'GlowSerum Manager Approve Test' })).toBeVisible({ timeout: 15000 })

    // Submit, start review, and approve on WorkflowPage
    await page.goto('/app/approvals')
    await expect(page.getByLabel('Select content item')).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /Submit for review/i }).click()
    await expect(page.getByRole('button', { name: /Start review/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /Start review/i }).click()
    await expect(page.getByRole('button', { name: /^Approve$/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /^Approve$/i }).click()

    await expect(page.getByText(/Workflow updated: approved/i)).toBeVisible({ timeout: 10000 })
  })
})

