const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')
export function getToken() { try { return localStorage.getItem('brandcourt-token') } catch { return null } }
export function setToken(token: string | null) { try { token ? localStorage.setItem('brandcourt-token', token) : localStorage.removeItem('brandcourt-token') } catch { /* Storage can be disabled. */ } }
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, { ...options, headers })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`)
  return data as T
}
export const apiBase = API_BASE
export type HealthPayload = { status: 'ok' | 'degraded'; service: string; version: string; timestamp: string; database: 'connected' | 'not_configured' | 'unavailable' }
export function getHealth(signal?: AbortSignal) { return api<HealthPayload>('/health', { signal }) }
