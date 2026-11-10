/**
 * Blocked-approval tests:
 *   1. UI: attempt to approve content with an unresolved critical finding
 *      → verify error message / disabled button is shown.
 *   2. API: POST /api/content/{id}/approve on unapproved content
 *      → verify 422 response body lists blockers.
 *
 * Run with:  npx playwright test e2e/blocked-approval.spec.ts
 */
import { test, expect } from '@playwright/test'

test.describe('Blocked approval gate', () => {
  test.setTimeout(90_000)

  test('UI shows error or disables Approve when critical blocker is unresolved', async ({ page }) => {
    // Register fresh workspace
    const ts = Date.now()
    const email = `blocker-${ts}@example.com`
    const password = 'BlockTest#2026!'

    await page.goto('/signup')
    await page.getByLabel('Workspace name').fill(`BlockedApproval-${ts}`)
    await page.getByLabel('Your full name').fill('Blocker Tester')
    await page.getByLabel('Work email').fill(email)
    await page.getByPlaceholder('At least 8 characters').fill(password)
    await page.getByRole('button', { name: /Create workspace/ }).click()
    await expect(page.getByRole('heading', { name: 'Insights dashboard' })).toBeVisible({ timeout: 20000 })

    // Create content with a likely-to-trigger critical claim
    await page.goto('/app/reviews')
    await page.getByRole('button', { name: /New Review/i }).click()
    await page.getByLabel(/Content Title/i).fill('Blocked Approval Test Item')
    await page.getByLabel(/Caption \/ Marketing Copy/i).fill(
      'GlowSerum completely eliminates all wrinkles permanently. 100% guaranteed results for everyone.',
    )
    await page.getByRole('button', { name: /Create Review/i }).click()
    await expect(page.getByRole('heading', { name: 'Blocked Approval Test Item' })).toBeVisible({ timeout: 15000 })

    // Run Claim Court Check so findings are produced
    await page.getByRole('button', { name: /Run Claim Court Check/i }).click()
    await expect(page.getByTestId('finding-card').first()).toBeVisible({ timeout: 25000 })

    // Verify Approval Gate blocks publication
    const gate = page.getByTestId('approval-gate')
    await expect(gate).toContainText(/Approval Gate: Blocked/i)
    await expect(gate.getByRole('button', { name: /Approve for Publication/i })).toBeDisabled()
  })

  test('API returns 409/422 when approving content with unresolved blockers', async ({ page, request }) => {
    // Register fresh workspace to get a valid auth token
    const ts = Date.now()
    const email = `api-block-${ts}@example.com`
    const password = 'ApiBlockTest#2026!'

    await page.goto('/signup')
    await page.getByLabel('Workspace name').fill(`APIBlock-${ts}`)
    await page.getByLabel('Your full name').fill('API Blocker')
    await page.getByLabel('Work email').fill(email)
    await page.getByPlaceholder('At least 8 characters').fill(password)
    await page.getByRole('button', { name: /Create workspace/ }).click()
    await expect(page.getByRole('heading', { name: 'Insights dashboard' })).toBeVisible({ timeout: 20000 })

    // Extract auth token from localStorage
    const token = await page.evaluate(() => {
      return (
        localStorage.getItem('brandcourt-token') ||
        localStorage.getItem('brandcourt_token') ||
        localStorage.getItem('token') ||
        ''
      )
    })

    // Determine backend base URL (default for dev)
    const backendBase = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
    expect(token).toBeTruthy()

    // Create content with guaranteed-results claim, analyze it, submit and start review
    const createRes = await request.post(`${backendBase}/api/content`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title: 'API Blocker Gate Test',
        channel: 'instagram',
        caption: 'GlowSerum cures acne and guarantees results.',
      },
    })
    expect(createRes.status()).toBe(201)
    const created = await createRes.json()

    const analyzeRes = await request.post(`${backendBase}/api/content/${created.id}/analyze`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(analyzeRes.status()).toBe(202)
    const { job_id: jobId } = await analyzeRes.json()

    for (let i = 0; i < 30; i += 1) {
      const jobRes = await request.get(`${backendBase}/api/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const job = await jobRes.json()
      if (job.status === 'completed') break
      await page.waitForTimeout(500)
    }

    await request.post(`${backendBase}/api/content/${created.id}/workflow`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { action: 'submit' },
    })
    await request.post(`${backendBase}/api/content/${created.id}/workflow`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { action: 'start_review' },
    })

    const approveRes = await request.post(`${backendBase}/api/content/${created.id}/workflow`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { action: 'approve' },
    })
    expect([409, 422]).toContain(approveRes.status())
    const approveBody = await approveRes.json()
    expect(approveBody.detail.unresolved.length).toBeGreaterThan(0)
  })
})

