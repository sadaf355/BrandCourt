import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient, setToken } from '../api'

const jsonResponse = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
})

describe('apiClient API contract alignment', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setToken(null)
  })

  it('uses the documented singular finding decision route and reason payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 'd1' }))
    vi.stubGlobal('fetch', fetchMock)
    await apiClient.submitFindingDecision('content-1', 'finding-1', 'override', 'Evidence ref GS-1')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/findings/finding-1/decision')
    expect(JSON.parse(String(init.body))).toEqual({ action: 'override', reason: 'Evidence ref GS-1' })
  })

  it('uses the shared workflow endpoint with the requested action', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ content_id: 'content-1', status: 'submitted', action: 'submit' }))
      .mockResolvedValueOnce(jsonResponse({ id: 'content-1', title: 'GlowSerum', channel: 'instagram', current_revision: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    await apiClient.submitForReview('content-1')
    expect(fetchMock.mock.calls[0][0]).toContain('/content/content-1/workflow')
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ action: 'submit' })
    expect(fetchMock.mock.calls[1][0]).toContain('/content/content-1')
  })

  it('uses the documented report endpoint for JSON and PDF', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ product: 'BrandCourt', findings: [], ai_and_service_disclosure: { calls: [] } }))
      .mockResolvedValueOnce(new Response('%PDF-test', { status: 200, headers: { 'Content-Type': 'application/pdf' } }))
    vi.stubGlobal('fetch', fetchMock)
    await apiClient.downloadReportJson('content-1')
    await apiClient.downloadReportPdf('content-1')
    expect(fetchMock.mock.calls[0][0]).toContain('/content/content-1/report?format=json')
    expect(fetchMock.mock.calls[1][0]).toContain('/content/content-1/report?format=pdf')
  })

  it('uses the documented model-mode read and workspace model-mode update', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ local_model_enabled: false, active_models: [], data_flow_log: [], masking_policy: { strict_pre_masking: true, secret_terms_masked: true, personal_identifiable_info_masked: true } }))
      .mockResolvedValueOnce(jsonResponse({ local_model_enabled: true, default_model: 'llama3', message: 'updated' }))
    vi.stubGlobal('fetch', fetchMock)
    await apiClient.getModelSettings()
    await apiClient.updateModelSettings({ local_model_enabled: true })
    expect(fetchMock.mock.calls[0][0]).toContain('/settings/models')
    expect(fetchMock.mock.calls[1][0]).toContain('/settings/models')
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({ local_model_enabled: true })
  })
})
