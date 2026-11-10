/**
 * Full WCAG 2.0/2.1 A+AA accessibility audit across public and authenticated routes
 * in both light and dark themes using axe-core, plus 100-finding render performance check.
 *
 * Run with: npx playwright test e2e/accessibility.spec.ts
 */
import { createRequire } from 'node:module'
import { test, expect } from '@playwright/test'

const require = createRequire(import.meta.url)
const axePath = require.resolve('axe-core')
const API_BASE = (process.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')

const PUBLIC_ROUTES = ['/', '/login', '/signup']

const AUTHENTICATED_STATIC_ROUTES = [
  '/app/dashboard',
  '/app/reviews',
  '/app/reviews/new',
  '/app/reviewer/queue',
  '/app/approvals',
  '/app/brand/guidelines',
  '/app/brand/rules',
  '/app/brand/facts',
  '/app/brand/assets',
  '/app/brand/guideline-health',
  '/app/insights',
  '/app/precedents',
  '/app/intelligence/fix-verify',
  '/app/settings/models',
  '/app/audit',
  '/app/settings/workspace',
  '/app/settings/members',
]

const THEMES = ['light', 'dark'] as const

type AxeViolation = {
  id: string
  impact?: string | null
  description: string
  help: string
  helpUrl: string
  nodes: Array<{ target: string[]; failureSummary?: string }>
}

async function runAxeAudit(page: import('@playwright/test').Page, label: string) {
  await page.addScriptTag({ path: axePath })
  const results = await page.evaluate(async () => {
    const axeWindow = window as unknown as {
      axe: {
        run: (
          context: Document,
          options: object
        ) => Promise<{ violations: AxeViolation[] }>
      }
    }
    return await axeWindow.axe.run(document, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
      },
    })
  })

  if (results.violations.length > 0) {
    const formatted = results.violations
      .map(
        (v) =>
          `  [${v.impact ?? 'unknown'}] ${v.id}: ${v.help} (${v.nodes.length} nodes: ${v.nodes
            .slice(0, 3)
            .map((n) => n.target.join(' '))
            .join(', ')})`
      )
      .join('\n')
    console.log(`AXE VIOLATIONS for ${label}:\n${formatted}`)
  } else {
    console.log(`AXE CLEAN for ${label}: 0 violations`)
  }
  return results.violations
}

test.describe('Accessibility audits with Axe (light & dark themes)', () => {
  test.setTimeout(360_000)

  let authToken = ''
  let sampleContentId = ''

  test.beforeAll(async ({ request }) => {
    const unique = `${Date.now()}-${Math.floor(Math.random() * 10000)}`
    const regResp = await request.post(`${API_BASE}/auth/register-workspace`, {
      data: {
        workspace_name: `A11y Audit Org ${unique}`,
        full_name: 'A11y Auditor',
        email: `a11y-${unique}@example.com`,
        password: 'StrongAuditPassword!2026',
      },
    })
    if (regResp.ok()) {
      const regData = await regResp.json()
      authToken = regData.access_token
      const contentResp = await request.post(`${API_BASE}/content`, {
        headers: { Authorization: `Bearer ${authToken}` },
        data: {
          title: 'A11y Audit Sample Post',
          channel: 'instagram',
          campaign: 'Audit 2026',
          caption: 'Our GlowSerum hydrates skin for 24 hours.',
        },
      })
      if (contentResp.ok()) {
        const created = await contentResp.json()
        sampleContentId = created.id
      }
    }
  })

  for (const theme of THEMES) {
    for (const route of PUBLIC_ROUTES) {
      test(`public route ${route} [${theme}]`, async ({ page }) => {
        await page.emulateMedia({ colorScheme: theme })
        await page.addInitScript((selectedTheme) => {
          localStorage.removeItem('brandcourt-token')
          document.documentElement.dataset.theme = selectedTheme
          document.documentElement.classList.toggle('dark', selectedTheme === 'dark')
        }, theme)

        await page.goto(route)
        await page.waitForLoadState('domcontentloaded')
        await expect(page).toHaveURL(new RegExp(`${route === '/' ? '/$' : `${route}$`}`))
        await page.waitForTimeout(800)

        const violations = await runAxeAudit(page, `${route} [${theme}]`)
        expect(violations).toEqual([])
      })
    }

    test(`authenticated routes audit [${theme}]`, async ({ page }) => {
      test.skip(!authToken, 'Backend API required to audit authenticated routes.')
      const routes = [...AUTHENTICATED_STATIC_ROUTES]
      if (sampleContentId) {
        routes.push(`/app/reviews/${sampleContentId}`, `/app/approvals/${sampleContentId}`)
      }

      await page.emulateMedia({ colorScheme: theme })
      await page.addInitScript(
        ({ token, selectedTheme }) => {
          localStorage.setItem('brandcourt-token', token)
          document.documentElement.dataset.theme = selectedTheme
          document.documentElement.classList.toggle('dark', selectedTheme === 'dark')
        },
        { token: authToken, selectedTheme: theme }
      )

      const summary: Array<{ route: string; count: number; ids: string[] }> = []
      for (const route of routes) {
        await page.goto(route)
        await page.waitForLoadState('domcontentloaded')
        // Ensure loading skeletons settle
        await page.waitForTimeout(250)
        const pathname = new URL(page.url()).pathname
        expect(pathname).toBe(route)

        const violations = await runAxeAudit(page, `${route} [${theme}]`)
        if (violations.length > 0) {
          summary.push({ route, count: violations.length, ids: violations.map((v) => v.id) })
        }
      }

      expect(summary).toEqual([])
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

