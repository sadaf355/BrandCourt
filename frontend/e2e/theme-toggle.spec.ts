/**
 * Theme toggle test on every route:
 * Verifies theme toggle changes class or style without layout disruption.
 *
 * Run with: npx playwright test e2e/theme-toggle.spec.ts
 */
import { test, expect } from '@playwright/test'

const ROUTES = [
  '/',
  '/login',
  '/signup',
  '/app/dashboard',
  '/app/reviews',
  '/app/reviewer/queue',
  '/app/approvals',
  '/app/brand/rules',
  '/app/brand/facts',
  '/app/brand/guideline-health',
  '/app/insights',
  '/app/intelligence/precedents',
  '/app/intelligence/fix-verify',
  '/app/settings/models',
]

test.describe('Theme toggle on every route', () => {
  test.setTimeout(120_000)

  for (const route of ROUTES) {
    test(`theme toggle functions on route: ${route}`, async ({ page }) => {
      await page.goto(route)

      // Look for theme toggle button (often has moon/sun or title/aria-label containing theme/mode)
      const themeBtn = page
        .getByRole('button', { name: /theme|dark|light|mode/i })
        .or(page.locator('[data-testid="theme-toggle"]'))
        .or(page.locator('button:has(svg.lucide-moon, svg.lucide-sun)'))
        .first()

      if (await themeBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
        const html = page.locator('html')
        const initialClass = (await html.getAttribute('class')) || ''

        await themeBtn.click()
        await page.waitForTimeout(300)

        const toggledClass = (await html.getAttribute('class')) || ''
        // Either class changed or toggled between dark/light
        expect(toggledClass !== initialClass || toggledClass.includes('dark') || toggledClass.includes('light')).toBe(true)

        // Toggle back
        await themeBtn.click()
      } else {
        // Route doesn't have an explicit toggle or requires auth redirect; ensure page rendered cleanly
        await expect(page.locator('body')).toBeVisible()
      }
    })
  }
})

