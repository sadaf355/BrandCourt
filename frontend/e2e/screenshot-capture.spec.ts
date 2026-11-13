import { test, expect } from '@playwright/test'
import path from 'node:path'
import fs from 'node:fs'

const API_BASE = (process.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || 'docs/ui-before'

const ROUTES = [
  { slug: 'landing', path: '/', isPublic: true },
  { slug: 'login', path: '/login', isPublic: true },
  { slug: 'dashboard', path: '/app/dashboard' },
  { slug: 'reviews', path: '/app/reviews' },
  { slug: 'reviews_new', path: '/app/reviews/new' },
  { slug: 'review_detail_findings', path: '/app/reviews/7c044bc5-46e5-43b5-b2ed-252b18b6309d' },
  { slug: 'approvals', path: '/app/approvals' },
  { slug: 'brand_guidelines', path: '/app/brand/guidelines' },
  { slug: 'brand_rules', path: '/app/brand/rules' },
  { slug: 'brand_facts', path: '/app/brand/facts' },
  { slug: 'brand_assets', path: '/app/brand/assets' },
  { slug: 'brand_guideline_health', path: '/app/brand/guideline-health' },
  { slug: 'intelligence_precedents', path: '/app/intelligence/precedents' },
  { slug: 'intelligence_fix_verify', path: '/app/intelligence/fix-verify' },
  { slug: 'insights', path: '/app/insights' },
  { slug: 'audit', path: '/app/audit' },
  { slug: 'settings_members', path: '/app/settings/members' },
  { slug: 'settings_workspace', path: '/app/settings/workspace' },
  { slug: 'settings_models', path: '/app/settings/models' },
]

const VIEWPORTS = [
  { name: '1440x900', width: 1440, height: 900 },
  { name: '390x844', width: 390, height: 844 },
]

const THEMES = ['light', 'dark'] as const

test.describe('Visual Screenshot Capture', () => {
  test.setTimeout(300_000)

  let authToken = ''

  test.beforeAll(async ({ request }) => {
    const loginRes = await request.post(`${API_BASE}/auth/demo-login`, {
      data: { role: 'admin' },
    })
    expect(loginRes.ok()).toBeTruthy()
    const data = await loginRes.json()
    authToken = data.access_token

    // Ensure output dir exists
    const rootDir = path.resolve(process.cwd(), '..')
    const outDir = path.join(rootDir, SCREENSHOT_DIR)
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true })
    }
  })

  for (const vp of VIEWPORTS) {
    for (const theme of THEMES) {
      test(`capture screenshots [${vp.name}] [${theme}]`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height })
        await page.emulateMedia({ colorScheme: theme })

        const rootDir = path.resolve(process.cwd(), '..')
        const outDir = path.join(rootDir, SCREENSHOT_DIR)

        for (const item of ROUTES) {
          await page.addInitScript(
            ({ token, selectedTheme, isPublic }) => {
              if (isPublic) {
                localStorage.removeItem('brandcourt-token')
              } else {
                localStorage.setItem('brandcourt-token', token)
              }
              document.documentElement.dataset.theme = selectedTheme
              document.documentElement.classList.toggle('dark', selectedTheme === 'dark')
            },
            { token: authToken, selectedTheme: theme, isPublic: !!item.isPublic }
          )

          await page.goto(item.path, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {})
          await page.waitForTimeout(600) // let animations and data settle

          const filename = `${item.slug}_${vp.name}_${theme}.png`
          const filePath = path.join(outDir, filename)
          await page.screenshot({ path: filePath, fullPage: false })
        }
      })
    }
  }
})
