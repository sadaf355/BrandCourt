import { useEffect, useState, type FormEvent } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Check, Eye, EyeOff, ShieldCheck, Sparkles } from 'lucide-react'
import { api, setToken } from '../lib/api'

type AuthResult = { access_token: string; user: { id: string; workspace_id: string; email: string; full_name: string; role: 'creator' | 'reviewer' | 'manager' | 'admin' } }
export function AuthPage({ onSignedIn, initialMode = 'register' }: { onSignedIn: (user: AuthResult['user']) => void; initialMode?: 'login' | 'register' }) {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  useEffect(() => { setMode(initialMode) }, [initialMode])
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [demoBusy, setDemoBusy] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ workspace_name: '', full_name: '', email: '', password: '' })
  const change = (key: keyof typeof form, value: string) => setForm(current => ({ ...current, [key]: value }))
  const demoLoginEnabled = import.meta.env.VITE_DEMO_LOGIN_ENABLED !== 'false'

  async function handleDemoLogin() {
    setDemoBusy(true)
    setError('')
    try {
      const result = await api<AuthResult>('/auth/demo-login', {
        method: 'POST',
        body: JSON.stringify({ role: 'admin' }),
      })
      setToken(result.access_token)
      onSignedIn(result.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo workspace is currently unavailable. Please try again.')
    } finally {
      setDemoBusy(false)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const result = await api<AuthResult>(mode === 'register' ? '/auth/register-workspace' : '/auth/login', { method: 'POST', body: JSON.stringify(mode === 'register' ? form : { email: form.email, password: form.password }) })
      setToken(result.access_token); onSignedIn(result.user)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not sign in. Please try again.') }
    finally { setBusy(false) }
  }
  return <div className="auth-layout"><div className="auth-showcase"><div className="auth-brand"><span className="brand-mark"><ShieldCheck size={21} /></span><span>BrandCourt<span className="brand-period">.</span></span></div><div className="auth-showcase__content"><span className="auth-kicker"><Sparkles size={14} /> CONTENT TRUST, BUILT IN</span><h1>Make every brand claim <em>stand on evidence.</em></h1><p>One workspace for brand rules, approved facts, and the people responsible for getting content right before it goes live.</p><div className="auth-proof-list"><div><Check size={15} /> Evidence-led governance</div><div><Check size={15} /> Human-reviewed rules</div><div><Check size={15} /> Versioned brand knowledge</div></div></div><div className="auth-showcase__foot">A clearer path from draft to confident publishing.</div><div className="auth-orb auth-orb--one" /><div className="auth-orb auth-orb--two" /></div><div className="auth-form-side"><motion.form initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} onSubmit={submit} className="auth-form"><div className="auth-mobile-brand"><span className="brand-mark"><ShieldCheck size={20} /></span><b>BrandCourt<span className="brand-period">.</span></b></div><span className="eyebrow">{mode === 'register' ? 'GET STARTED' : 'WELCOME BACK'}</span><h2>{mode === 'register' ? 'Create your workspace' : 'Sign in to BrandCourt'}</h2><p className="muted-copy">{mode === 'register' ? 'Your workspace starts with a guideline-owner account.' : 'Continue managing your brand knowledge.'}</p>{mode === 'register' && <><label className="field-label">Workspace name<input required minLength={2} maxLength={160} value={form.workspace_name} onChange={e => change('workspace_name', e.target.value)} placeholder="e.g. GlowSerum Marketing" /></label><label className="field-label">Your full name<input required minLength={2} value={form.full_name} onChange={e => change('full_name', e.target.value)} placeholder="Full name" /></label></>}<label className="field-label">Work email<input required type="email" value={form.email} onChange={e => change('email', e.target.value)} placeholder="you@company.com" autoComplete="email" /></label><label className="field-label">Password<div className="password-input"><input required minLength={8} type={showPassword ? 'text' : 'password'} value={form.password} onChange={e => change('password', e.target.value)} placeholder="At least 8 characters" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label><div className="form-error-wrapper">{error && <div role="alert" className="form-error">{error}</div>}</div>
<button className="primary-button auth-submit" disabled={busy || demoBusy}>
  <span>{busy ? 'Please wait…' : mode === 'register' ? 'Create workspace' : 'Sign in'}</span>
  <ArrowRight size={16} />
</button>
{demoLoginEnabled && (
  <div className="demo-login-box" style={{ marginTop: '0.85rem', textAlign: 'center' }}>
    <button
      type="button"
      className="secondary-button demo-login-button"
      onClick={handleDemoLogin}
      disabled={busy || demoBusy}
      style={{
        width: '100%',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        padding: '0.65rem 1rem',
        fontWeight: 600,
        fontSize: '0.9rem',
        cursor: (busy || demoBusy) ? 'not-allowed' : 'pointer',
      }}
    >
      <Sparkles size={16} />
      <span>{demoBusy ? 'Preparing demo…' : 'Demo'}</span>
    </button>
    <p
      className="demo-login-caption"
      style={{
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        marginTop: '0.35rem',
        lineHeight: 1.35,
      }}
    >
      Explore a pre-filled fictional workspace. Shared and public; don't enter real data.
    </p>
  </div>
)}
<p className="auth-switch">
  <span>{mode === 'register' ? 'Already have a workspace?' : 'New to BrandCourt?'} </span>
  <button type="button" onClick={() => { setMode(mode === 'register' ? 'login' : 'register'); setError('') }}>
    {mode === 'register' ? 'Sign in' : 'Create a workspace'}
  </button>
</p><p className="auth-security"><ShieldCheck size={14} /> Your workspace data is separated by workspace membership.</p></motion.form></div></div>
}
