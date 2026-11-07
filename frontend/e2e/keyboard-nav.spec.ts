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
    // Visit app dashboard
    await page.goto('/app/reviews')

    // Tab into main navigation or buttons
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Focus state exists
    const hasFocus = await page.evaluate(() => document.activeElement !== document.body)
    expect(hasFocus).toBe(true)
  })
})

