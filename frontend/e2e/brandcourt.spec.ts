import { test, expect } from '@playwright/test'
const email=`brandcourt-e2e-${Date.now()}@example.com`
test('workspace registration, content creation and navigation smoke test',async({page})=>{
 await page.goto('/')
 await expect(page.getByRole('heading',{name:'Create your workspace'})).toBeVisible()
 await page.getByLabel('Workspace name').fill('BrandCourt E2E')
 await page.getByLabel('Your full name').fill('E2E Reviewer')
 await page.getByLabel('Work email').fill(email)
 await page.getByLabel('Password').fill('SafeDemoPass!234')
 await page.getByRole('button',{name:/Create workspace/}).click()
 await expect(page.getByText('YOUR BRAND, WITH EVIDENCE')).toBeVisible({timeout:15000})
 await page.getByRole('link',{name:/Content reviews/}).click()
 await expect(page.getByRole('heading',{name:/Content review & Claim Court/})).toBeVisible()
 await page.getByRole('button',{name:/New content/}).click()
 await page.getByLabel('Content title').fill('E2E GlowSerum draft')
 await page.getByLabel('Caption / marketing copy').fill('GlowSerum is a lightweight step in your evening routine.')
 await page.getByRole('button',{name:/Create draft/}).click()
 await expect(page.getByText('E2E GlowSerum draft')).toBeVisible({timeout:10000})
})
