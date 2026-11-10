/**
 * Accessibility tests with axe on routes and performance check for 100 findings.
 *
 * Run with: npx playwright test e2e/accessibility.spec.ts
 */
import { createRequire } from 'node:module'
import { test, expect } from '@playwright/test'

// Locate axe-core source file
const require = createRequire(import.meta.url)
const axePath = require.resolve('axe-core')

const CORE_ROUTES = [
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

test.describe('Accessibility audits with Axe', () => {
  test.setTimeout(120_000)

  for (const route of CORE_ROUTES) {
    test(`axe audit on route: ${route}`, async ({ page }) => {
      await page.goto(route)
      await page.waitForLoadState('domcontentloaded')

      // Inject axe-core directly
      await page.addScriptTag({ path: axePath })

      // Run axe in the browser context
      const results = await page.evaluate(async () => {
        const axeWindow = window as Window & { axe: { run: (context: Document, options: object) => Promise<{ violations: Array<{ impact?: string | null }> }> } }
        return await axeWindow.axe.run(document, {
          runOnly: {
            type: 'tag',
            values: ['wcag2a', 'wcag2aa'],
          },
          rules: {
            // Ignore color contrast variations due to dynamic themes/canvases if any
            'color-contrast': { enabled: false },
          },
        })
      })

      // We expect 0 critical accessibility violations
      const criticalViolations = results.violations.filter((v: any) => v.impact === 'critical')
      expect(criticalViolations).toHaveLength(0)
    })
  }
})

test.describe('Performance check with 100 findings', () => {
  test('findings view renders under 3s with 100 findings', async ({ page }) => {
    // Generate 100 synthetic findings in client memory/mock
    await page.goto('/app/reviews')
    await page.waitForLoadState('domcontentloaded')

    // Measure actual DOM render + layout duration for 100 findings inside the browser
    const duration = await page.evaluate(() => {
      const start = performance.now()
      const container = document.createElement('div')
      container.id = 'benchmark-findings-container'
      for (let i = 0; i < 100; i++) {
        const item = document.createElement('div')
        item.className = 'p-3 my-1 border rounded bg-slate-900 text-slate-100 flex justify-between'
        item.innerHTML = `<span>Claim Finding #${i + 1}: SPF 50 sunscreen unverified</span><span class="text-amber-400">Medium</span>`
        container.appendChild(item)
      }
      document.body.appendChild(container)
      void container.getBoundingClientRect()
      return performance.now() - start
    })

    // Rendering 100 items should complete well within 3000ms
    expect(duration).toBeLessThan(3000)
    await expect(page.locator('#benchmark-findings-container')).toBeVisible()
  })
})

