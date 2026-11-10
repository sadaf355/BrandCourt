import { Link } from 'react-router-dom'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { ArrowRight, BadgeCheck, ShieldCheck, Sparkles, ChevronDown } from 'lucide-react'
import { HeroShieldView } from './three/HeroShieldView'

export function HeroSection() {
  const shouldReduceMotion = useReducedMotion()

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.12,
        delayChildren: shouldReduceMotion ? 0 : 0.05,
      },
    },
  }

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 18 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: shouldReduceMotion ? 0 : 0.55, ease: 'easeOut' },
    },
  }

  const scrollToDemo = (e: React.MouseEvent) => {
    e.preventDefault()
    const target = document.getElementById('the-fix')
    if (target) {
      target.scrollIntoView({ behavior: shouldReduceMotion ? 'auto' : 'smooth' })
    }
  }

  return (
    <section className="landing-hero" id="hero" aria-labelledby="hero-title">
      <div className="landing-hero__ambient-glow" aria-hidden="true" />
      <div className="landing-container landing-hero__grid">
        <motion.div
          className="landing-hero__copy"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div className="landing-kicker" variants={itemVariants}>
            <span className="landing-kicker__icon"><Sparkles size={13} /></span>
            <span>EVIDENCE-LED BRAND GOVERNANCE</span>
          </motion.div>

          <motion.h1 id="hero-title" className="landing-hero__title" variants={itemVariants}>
            Every claim needs proof<span className="brand-period">.</span>
          </motion.h1>

          <motion.p className="landing-hero__subline" variants={itemVariants}>
            BrandCourt checks your marketing content against your approved facts and brand rules before it goes live, shows the evidence behind every flag, and keeps a human in charge of the final decision.
          </motion.p>

          <motion.div className="landing-hero__cta-group" variants={itemVariants}>
            <Link to="/signup" className="landing-btn landing-btn--primary">
              <span>Create workspace</span>
              <ArrowRight size={16} />
            </Link>
            <a href="#the-fix" onClick={scrollToDemo} className="landing-btn landing-btn--secondary">
              <span>See how it works</span>
              <ChevronDown size={15} />
            </a>
          </motion.div>

          <motion.div className="landing-hero__trust-strip" variants={itemVariants}>
            <div className="landing-trust-item">
              <ShieldCheck size={15} className="teal-icon" />
              <span>Versioned evidence</span>
            </div>
            <div className="landing-trust-item">
              <BadgeCheck size={15} className="teal-icon" />
              <span>Immutable audit trail</span>
            </div>
            <div className="landing-trust-item">
              <span className="landing-trust-dot" />
              <span>Human in control</span>
            </div>
          </motion.div>
        </motion.div>

        <div className="landing-hero__visual" role="img" aria-label="Interactive 3D BrandCourt Shield">
          <HeroShieldView />
        </div>
      </div>
    </section>
  )
}
