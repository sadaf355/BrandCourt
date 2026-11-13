import { test, expect } from '@playwright/test'

const API_BASE = (process.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')

test.describe('Judge resilience and stranger journey', () => {
  test.setTimeout(120_000)

  test('signed-out /app visit redirects to /login and login shows Demo cue', async ({ page }) => {
    await page.addInitScript(() => localStorage.removeItem('brandcourt-token'))
    await page.goto('/app/dashboard')
    await page.waitForURL('**/login')
    await expect(page.getByText('No account needed: press Demo to explore')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Demo' })).toBeVisible()
  })

  test('expired or tampered token redirects cleanly to /login', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('brandcourt-token', 'tampered.jwt.value'))
    await page.goto('/app/reviews')
    await page.waitForURL('**/login')
    await expect(page.getByRole('button', { name: 'Demo' })).toBeVisible()
  })

  test('brand-new workspace shows clear empty states and handles refresh + 404 + backend failure', async ({
    page,
    request,
  }) => {
    const unique = `${Date.now()}-${Math.floor(Math.random() * 10000)}`
    const reg = await request.post(`${API_BASE}/auth/register-workspace`, {
      data: {
        workspace_name: `Empty Org ${unique}`,
        full_name: 'Judge Tester',
        email: `judge-${unique}@example.com`,
        password: 'JudgeStrongPassword!2026',
      },
    })
    expect(reg.ok()).toBeTruthy()
    const { access_token } = await reg.json()

    await page.addInitScript((token) => {
      localStorage.setItem('brandcourt-token', token)
    }, access_token)

    // Refresh on /app/dashboard keeps user signed in & shows empty state
    await page.goto('/app/dashboard')
    await expect(page.getByText('No content reviews yet')).toBeVisible({ timeout: 15_000 })
    await page.reload()
    await expect(page.getByText('No content reviews yet')).toBeVisible({ timeout: 15_000 })

    // Empty states across lists
    await page.goto('/app/reviews')
    await expect(page.getByText('No reviews yet')).toBeVisible()

    await page.goto('/app/brand/rules')
    await expect(page.getByText('No rules found')).toBeVisible()

    await page.goto('/app/brand/facts')
    await expect(page.getByText('No approved facts yet')).toBeVisible()

    await page.goto('/app/precedents')
    await expect(page.getByText('No precedents found')).toBeVisible()

    await page.goto('/app/brand/guideline-health')
    await expect(page.getByText('All guidelines are healthy')).toBeVisible()

    // Missing / another workspace review -> clear message + back button
    await page.goto('/app/reviews/does-not-exist-999')
    await expect(page.getByText('Could not open content review')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Back to Content Reviews' })).toBeVisible()

    // Network/backend failure -> visible error with Retry
    await page.route(`${API_BASE}/content`, (route) => route.abort('failed'))
    await page.goto('/app/reviews')
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible()
  })

  test('stranger Demo journey: Demo login -> review -> accept fix -> comment -> Reviewer -> Manager approve -> report', async ({
    page,
    request,
  }) => {
    const demoStatus = await request.get(`${API_BASE}/auth/demo-status`)
    const statusJson = await demoStatus.json()
    test.skip(!statusJson.enabled || !statusJson.ready, 'Demo workspace not active/ready')

    await page.goto('/login')
    await expect(page.getByText('No account needed: press Demo to explore')).toBeVisible()

    await page.getByRole('button', { name: 'Demo' }).click()
    await page.waitForURL('**/app/dashboard')

    // Role switcher shows capability descriptions in accessible labels/titles
    await expect(page.getByRole('button', { name: /Switch to Reviewer/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /Switch to Manager/ })).toBeVisible()

    // Open clean demo draft ("Demo: clean and approved" or create/open a draft) -> navigate to Content Reviews
    await page.goto('/app/reviews')
    await expect(page.getByText('Demo: fresh findings')).toBeVisible()
    await page.getByText('Demo: fresh findings').first().click()
    await page.waitForURL('**/app/reviews/*')

    // Run review
    const runBtn = page.getByRole('button', { name: /Run Claim Court Check/i })
    await runBtn.click()
    await expect(page.getByText('Claim Court check complete!')).toBeVisible({ timeout: 20_000 })
    await expect(runBtn).toBeEnabled({ timeout: 10_000 })
    await expect(page.getByTestId('finding-card').first()).toBeVisible({ timeout: 10_000 })

    // Suggest fix & accept/apply
    await page.getByRole('button', { name: 'Suggest fix' }).first().click()
    await expect(page.getByText(/Fix verified|Fix not approved/)).toBeVisible({ timeout: 15_000 })
    const acceptBtn = page.getByRole('button', { name: /Accept finding/i }).first()
    await acceptBtn.click()
    await expect(page.getByRole('button', { name: /Accepted/i }).first()).toBeVisible({ timeout: 10_000 })

    // Add comment
    const commentBox = page.getByPlaceholder(/Add a comment/i).first()
    if (await commentBox.isVisible()) {
      await commentBox.fill('Checked by stranger judge walkthrough.')
      await page.getByRole('button', { name: 'Comment', exact: true }).click()
      await expect(page.getByRole('region', { name: 'Finding comments' }).getByRole('paragraph').filter({ hasText: 'Checked by stranger judge walkthrough.' }).first()).toBeVisible({ timeout: 10_000 })
    }

    // Switch role to Reviewer and Manager and approve a clean draft end-to-end
    await page.getByRole('button', { name: /Switch to Reviewer/ }).click()
    await expect(page.getByText('Reviewer access')).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: /Switch to Manager/ }).click()
    await expect(page.getByText('Manager access')).toBeVisible({ timeout: 10_000 })

    // Create a clean post, submit, start review, approve, and open compliance report
    await page.goto('/app/reviews/new')
    await page.locator('#review-title').fill('Stranger Judge Clean Post')
    await page.locator('textarea').first().fill('Enjoy a gentle daily skincare ritual with GlowSerum. #ad')
    await page.getByRole('button', { name: /Create Review & Open Claim Court/i }).click()
    await page.waitForURL(/\/app\/reviews\/(?!new$)[^/]+/, { timeout: 20_000 })

    const runCleanBtn = page.getByRole('button', { name: /Run Claim Court Check/i })
    await runCleanBtn.click()
    await expect(page.getByText('Claim Court check complete!').first()).toBeVisible({ timeout: 20_000 })
    await expect(runCleanBtn).toBeEnabled({ timeout: 10_000 })
    await page.getByRole('button', { name: /Submit for Review/i }).click()
    await expect(page.getByRole('button', { name: /Start Reviewer Sign-Off/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: /Start Reviewer Sign-Off/i }).click()
    await expect(page.getByRole('button', { name: /Approve for Publication/i })).toBeEnabled({ timeout: 10_000 })
    await page.getByRole('button', { name: /Approve for Publication/i }).click()
    await expect(page.getByRole('button', { name: /Open Compliance Report/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: /Open Compliance Report/i }).click()
    await page.waitForURL('**/app/insights')
    await expect(page.getByRole('button', { name: 'Download JSON' })).toBeVisible()
  })
})
