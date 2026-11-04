import { useRef } from 'react'
import { motion, useScroll, useTransform, useReducedMotion } from 'framer-motion'
import { ShieldAlert, Users, Lock, Sparkles, CheckCircle2, FileText, BadgeCheck } from 'lucide-react'

export function WhyTrustItSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const shouldReduceMotion = useReducedMotion()

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start end', 'end start'],
  })

  const photoY = useTransform(scrollYProgress, [0, 1], shouldReduceMotion ? [0, 0] : [-18, 18])

  return (
    <section className="landing-section trust-section" id="why-trust-it" ref={sectionRef} aria-labelledby="trust-heading">
      <div className="landing-container">
        <div className="landing-section-head">
          <div className="landing-kicker">
            <span className="landing-kicker__icon"><Sparkles size={13} /></span>
            <span>ACCOUNTABLE GOVERNANCE</span>
          </div>
          <h2 id="trust-heading" className="landing-section-title">
            Why trust it<span className="brand-period">.</span>
          </h2>
          <p className="landing-section-subline">
            Built from the ground up to prevent black-box hallucinations and maintain complete auditability for marketing, legal, and brand teams.
          </p>
        </div>

        <div className="trust-layout-grid">
          {/* Left Column: 3 Feature Cards */}
          <div className="trust-cards-column">
            {/* Feature 1 */}
            <motion.div
              className="trust-card"
              initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: shouldReduceMotion ? 0 : 0.45 }}
            >
              <div className="trust-card__header">
                <span className="trust-card__icon"><FileText size={18} /></span>
                <div>
                  <h3 className="trust-card__title">Evidence, not opinions</h3>
                  <p className="trust-card__tag">No source means no error flag</p>
                </div>
              </div>
              <p className="trust-card__desc">
                BrandCourt never flags content on subjective whim. If there is no approved fact or active policy rule on file, it reports “Unverifiable” rather than inventing a contradiction.
              </p>
              <div className="trust-micro-visual">
                <div className="micro-source-tag">
                  <CheckCircle2 size={12} className="teal-icon" />
                  <span>FACT-002: Clinical Study v2</span>
                </div>
                <div className="micro-connector-line" />
                <div className="micro-verdict-tag">
                  <span>Supported claim (100% trace)</span>
                </div>
              </div>
            </motion.div>

            {/* Feature 2 */}
            <motion.div
              className="trust-card"
              initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: shouldReduceMotion ? 0 : 0.45, delay: shouldReduceMotion ? 0 : 0.1 }}
            >
              <div className="trust-card__header">
                <span className="trust-card__icon"><Users size={18} /></span>
                <div>
                  <h3 className="trust-card__title">Humans decide</h3>
                  <p className="trust-card__tag">Written reason required for overrides</p>
                </div>
              </div>
              <p className="trust-card__desc">
                AI and heuristic rules offer suggestions; team reviewers and managers make the call. Any override requires a non-empty rationale permanently stored in the audit trail.
              </p>
              <div className="trust-micro-visual">
                <div className="micro-audit-badge">
                  <span className="micro-audit-dot" />
                  <strong>Override signed by Reviewer</strong>
                  <small>"Legal counsel reviewed disclaimer in footnote"</small>
                </div>
              </div>
            </motion.div>

            {/* Feature 3 */}
            <motion.div
              className="trust-card"
              initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: shouldReduceMotion ? 0 : 0.45, delay: shouldReduceMotion ? 0 : 0.2 }}
            >
              <div className="trust-card__header">
                <span className="trust-card__icon"><Lock size={18} /></span>
                <div>
                  <h3 className="trust-card__title">Privacy by design</h3>
                  <p className="trust-card__tag">PII masked before external evaluation</p>
                </div>
              </div>
              <p className="trust-card__desc">
                Personal contact details and sensitive metadata are scrubbed locally before analysis. Every immutable review report explicitly lists which AI services were invoked.
              </p>
              <div className="trust-micro-visual">
                <div className="micro-privacy-strip">
                  <span className="privacy-pill privacy-pill--masked">[CONTACT_REDACTED]</span>
                  <span className="privacy-arrow">→</span>
                  <span className="privacy-pill privacy-pill--clean">Local Heuristic Validator</span>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Column: Wide Photo with Gentle Parallax and UI Fragments */}
          <div className="trust-photo-column">
            <motion.div className="trust-photo-wrapper" style={{ y: photoY }}>
              <div className="trust-photo-frame">
                <img
                  src="/landing/team.webp"
                  alt="Marketing team collaboratively reviewing content on a laptop with BrandCourt"
                  width={800}
                  height={600}
                  loading="lazy"
                  decoding="async"
                  className="trust-photo-img"
                />
                <div className="trust-photo-overlay" aria-hidden="true" />
              </div>

              {/* Floating UI Fragment 1: Top Right */}
              <motion.div
                className="floating-ui-card floating-ui-card--top"
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.4, delay: 0.25 }}
              >
                <div className="float-card-head">
                  <BadgeCheck size={14} className="teal-icon" />
                  <strong>Guideline Health: Clean</strong>
                </div>
                <small>0 unverified critical claims</small>
              </motion.div>

              {/* Floating UI Fragment 2: Bottom Left */}
              <motion.div
                className="floating-ui-card floating-ui-card--bottom"
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.4, delay: 0.35 }}
              >
                <div className="float-card-head">
                  <ShieldAlert size={14} className="teal-icon" />
                  <strong>Audit Log: Review Completed</strong>
                </div>
                <small>Manager sign-off locked at 16:40</small>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
