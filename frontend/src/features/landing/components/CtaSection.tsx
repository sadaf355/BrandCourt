import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, ShieldCheck, Sparkles } from 'lucide-react'

export function CtaSection() {
  const shouldReduceMotion = useReducedMotion()

  return (
    <section className="landing-section cta-section" id="cta-band" aria-labelledby="cta-heading">
      <div className="landing-container">
        {/* Call to action band */}
        <motion.div
          className="cta-banner"
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: shouldReduceMotion ? 0 : 0.55 }}
        >
          <div className="cta-banner__glow" aria-hidden="true" />
          <div className="cta-banner__content">
            <div className="landing-kicker">
              <span className="landing-kicker__icon"><Sparkles size={13} /></span>
              <span>GET STARTED TODAY</span>
            </div>
            <h2 id="cta-heading" className="cta-banner__title">
              Ready to verify brand truth before publication?
            </h2>
            <p className="cta-banner__subline">
              Join marketing and governance teams who build on evidence rather than guesswork. Set up your workspace in minutes.
            </p>
            <div className="cta-banner__actions">
              <Link to="/signup" className="landing-btn landing-btn--primary">
                <span>Create workspace</span>
                <ArrowRight size={16} />
              </Link>
              <Link to="/login" className="landing-btn landing-btn--secondary">
                <span>Sign in</span>
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Minimal Footer */}
        <footer className="landing-footer" role="contentinfo">
          <div className="landing-footer__main">
            <div className="landing-footer__brand">
              <Link to="/" className="brand-lockup">
                <span className="brand-mark"><ShieldCheck size={20} strokeWidth={2.1} /></span>
                <span className="brand-word">
                  BrandCourt<span className="brand-period">.</span>
                  <small>CONTENT TRUST PLATFORM</small>
                </span>
              </Link>
              <p className="landing-footer__legal-notice">
                Starter India rules pack, not legal advice. Designed for brand guideline governance and team compliance oversight.
              </p>
            </div>

            <div className="landing-footer__links">
              <Link to="/login" className="landing-footer-link">Sign in</Link>
              <Link to="/signup" className="landing-footer-link">Create workspace</Link>
              <a href="#hero" className="landing-footer-link">Back to top</a>
            </div>
          </div>

          <div className="landing-footer__bottom">
            <span>© 2026 BrandCourt. Evidence-led brand governance.</span>
            <span>All rights reserved.</span>
          </div>
        </footer>
      </div>
    </section>
  )
}
