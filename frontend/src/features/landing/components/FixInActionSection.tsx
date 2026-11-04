import { useEffect, useState } from 'react'
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion'
import { AlertCircle, CheckCircle2, FileCheck, Sparkles, ArrowRight } from 'lucide-react'

type DemoPhase = 'scanning' | 'flagged' | 'evidence' | 'fixed'

export function FixInActionSection() {
  const shouldReduceMotion = useReducedMotion()
  const [phase, setPhase] = useState<DemoPhase>('scanning')

  useEffect(() => {
    if (shouldReduceMotion) {
      setPhase('fixed')
      return
    }

    let isMounted = true
    const cycle = () => {
      if (!isMounted) return
      setPhase('scanning')
      const t1 = setTimeout(() => {
        if (!isMounted) return
        setPhase('flagged')
      }, 1600)
      const t2 = setTimeout(() => {
        if (!isMounted) return
        setPhase('evidence')
      }, 3400)
      const t3 = setTimeout(() => {
        if (!isMounted) return
        setPhase('fixed')
      }, 5400)
      const t4 = setTimeout(() => {
        if (!isMounted) return
        cycle()
      }, 8600)

      return () => {
        clearTimeout(t1)
        clearTimeout(t2)
        clearTimeout(t3)
        clearTimeout(t4)
      }
    }

    const cancel = cycle()
    return () => {
      isMounted = false
      if (cancel) cancel()
    }
  }, [shouldReduceMotion])

  return (
    <section className="landing-section fix-section" id="the-fix" aria-labelledby="fix-heading">
      <div className="landing-container">
        <div className="landing-section-head">
          <div className="landing-kicker">
            <span className="landing-kicker__icon"><Sparkles size={13} /></span>
            <span>INTELLIGENT VERIFICATION</span>
          </div>
          <h2 id="fix-heading" className="landing-section-title">
            The fix in action<span className="brand-period">.</span>
          </h2>
          <p className="landing-section-subline">
            Watch BrandCourt catch an unsubstantiated timeline claim, connect it to the official clinical study, and propose verified phrasing that protects brand reputation.
          </p>
        </div>

        {/* Demo container with clear sample disclosure */}
        <div className="demo-canvas-card">
          <div className="demo-card-header">
            <div className="demo-badge-group">
              <span className="sample-disclosure-pill">Sample data, not live results</span>
              <span className="brand-context-tag">Fictional Brand · GlowSerum</span>
            </div>
            <div className="demo-phase-indicator">
              <span className={`phase-step ${phase === 'scanning' ? 'active' : ''}`}>1. Scan</span>
              <span className={`phase-step ${phase === 'flagged' ? 'active' : ''}`}>2. Flag</span>
              <span className={`phase-step ${phase === 'evidence' ? 'active' : ''}`}>3. Evidence</span>
              <span className={`phase-step ${phase === 'fixed' ? 'active' : ''}`}>4. Verified</span>
            </div>
          </div>

          <div className="demo-stage-grid">
            {/* Left: Content Draft Card */}
            <div className="demo-pane demo-pane--editor">
              <div className="demo-pane__title">
                <span className="pane-icon"><FileCheck size={16} /></span>
                <div>
                  <strong>Marketing Copy Draft</strong>
                  <small>Instagram & Paid Social · v1 Revision</small>
                </div>
              </div>

              <div className="demo-editor-box">
                {/* Scan line effect */}
                {!shouldReduceMotion && phase === 'scanning' && (
                  <motion.div
                    className="demo-scan-line"
                    initial={{ top: 0, opacity: 0 }}
                    animate={{ top: ['0%', '100%'], opacity: [0, 1, 1, 0] }}
                    transition={{ duration: 1.5, ease: 'easeInOut' }}
                  />
                )}

                <p className="demo-caption-text">
                  Transform your skin texture.{' '}
                  {phase === 'fixed' ? (
                    <motion.span
                      className="demo-text-fixed"
                      initial={{ backgroundColor: 'rgba(45, 212, 191, 0.25)' }}
                      animate={{ backgroundColor: 'rgba(45, 212, 191, 0.12)' }}
                      transition={{ duration: 0.8 }}
                    >
                      visible results in 4 weeks
                    </motion.span>
                  ) : (
                    <span
                      className={`demo-claim-target ${
                        phase === 'flagged' || phase === 'evidence' ? 'flagged-red' : ''
                      }`}
                    >
                      Results in 7 days
                    </span>
                  )}{' '}
                  with daily application.
                </p>

                <div className="demo-editor-footer">
                  <span className="demo-caption-meta">Word count: 12 · Target channel: Instagram</span>
                  <AnimatePresence>
                    {phase === 'fixed' && (
                      <motion.span
                        className="intent-chip"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                      >
                        <CheckCircle2 size={13} />
                        <span>Intent preserved</span>
                      </motion.span>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>

            {/* Middle: Dynamic Connector */}
            <div className="demo-connector-column" aria-hidden="true">
              <svg className="demo-connector-svg" viewBox="0 0 120 200" preserveAspectRatio="none">
                <path
                  d="M 10 100 C 60 100, 60 100, 110 100"
                  fill="none"
                  stroke={phase === 'scanning' ? 'var(--border)' : phase === 'fixed' ? '#10b981' : '#f43f5e'}
                  strokeWidth="2.5"
                  strokeDasharray={phase === 'scanning' ? '4 4' : 'none'}
                />
              </svg>
            </div>

            {/* Right: Evidence & Court Findings Card */}
            <div className="demo-pane demo-pane--court">
              <div className="demo-pane__title">
                <span className="pane-icon pane-icon--teal"><Sparkles size={16} /></span>
                <div>
                  <strong>Claim Court Evidence</strong>
                  <small>Workspace Knowledge match</small>
                </div>
              </div>

              <div className="demo-court-card">
                <div className="court-finding-header">
                  <span className={`finding-status-badge finding-status-badge--${phase}`}>
                    {phase === 'scanning' && 'Scanning against rules…'}
                    {phase === 'flagged' && 'Contradicted claim'}
                    {phase === 'evidence' && 'Evidence matched'}
                    {phase === 'fixed' && 'Verified & compliant'}
                  </span>
                  <span className="finding-severity-tag">
                    {phase === 'fixed' ? 'Resolved' : 'High severity'}
                  </span>
                </div>

                <div className="court-finding-body">
                  <div className="court-evidence-row">
                    <span className="court-evidence-label">Matched Truth Source</span>
                    <strong className="court-evidence-code">Approved fact FACT-014 (v3)</strong>
                  </div>

                  <blockquote className="court-evidence-excerpt">
                    "Clinical study GS-2024: Visible skin texture improvement observed in <strong>4 weeks</strong> of consistent application."
                  </blockquote>

                  <div className="court-resolution-box">
                    <span className="court-resolution-heading">
                      {phase === 'fixed' ? 'Applied correction' : 'Recommended action'}
                    </span>
                    <div className="court-fix-proposal">
                      <span className="diff-del">"Results in 7 days"</span>
                      <ArrowRight size={13} className="diff-arrow" />
                      <span className="diff-ins">"visible results in 4 weeks"</span>
                    </div>
                  </div>
                </div>

                <div className="court-footer-note">
                  <AlertCircle size={13} className="court-note-icon" />
                  <span>Rule check: IN-5 Advisory · Heuristic check, human signs off</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
