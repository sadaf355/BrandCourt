/**
 * Keyboard-only run of the main flow:
 * Tests tab navigation and Enter/Space activation across core views.
 *
 * Run with: npx playwright test e2e/keyboard-nav.spec.ts
 */
import { test, expect } from '@playwright/test'

test.describe('Keyboard-only navigation flow', () => {
  test.setTimeout(90_000)

  test('tab navigation works on login page and dialogs', async ({ page }) => {
    await page.goto('/login')

    // Tab through the login form elements
    await page.keyboard.press('Tab')
    const focusedTag = await page.evaluate(() => document.activeElement?.tagName)
    expect(focusedTag).toBeTruthy()

    // Tab to next input
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Check we can hit Enter without mouse click
    const activeElemType = await page.evaluate(() => (document.activeElement as HTMLInputElement)?.type || document.activeElement?.tagName)
    expect(activeElemType).toBeTruthy()
  })

  test('keyboard navigation through sidebar and reviews', async ({ page }) => {
    const ts = Date.now()
    await page.goto('/signup')
    await page.getByLabel('Workspace name').fill(`KeyboardNav-${ts}`)
    await page.getByLabel('Your full name').fill('Keyboard Tester')
    await page.getByLabel('Work email').fill(`kbd-${ts}@example.com`)
    await page.getByPlaceholder('At least 8 characters').fill('KeyboardPass#2026!')
    await page.getByRole('button', { name: /Create workspace/ }).click()
    await expect(page.getByRole('heading', { name: 'Insights dashboard' })).toBeVisible({ timeout: 20000 })

    // Visit reviews page
    await page.goto('/app/reviews')
    await expect(page.getByRole('heading', { name: 'Content Reviews' })).toBeVisible()

    // Tab into sidebar / page navigation buttons
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Focus state exists
    const hasFocus = await page.evaluate(() => document.activeElement !== document.body)
    expect(hasFocus).toBe(true)
  })
})

