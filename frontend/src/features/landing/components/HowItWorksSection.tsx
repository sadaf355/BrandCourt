import { useRef } from 'react'
import { motion, useScroll, useSpring, useReducedMotion } from 'framer-motion'
import { UploadCloud, Layers, CheckSquare, Lock, Sparkles } from 'lucide-react'

const steps = [
  {
    number: '01',
    icon: UploadCloud,
    title: 'Upload text or image',
    description:
      'Paste campaign copy or attach creative visual assets. OCR automatically extracts text from raster images without manual transcription.',
    tag: 'Intake',
  },
  {
    number: '02',
    icon: Layers,
    title: 'Three-layer check',
    description:
      'Deterministic rules in code, factual evidence checked against your approved brand facts, and tone flags provided purely as advice.',
    tag: 'Claim Court',
  },
  {
    number: '03',
    icon: CheckSquare,
    title: 'Review and fix',
    description:
      'Accept suggestions, edit copy with real-time fix verification, or dispute findings with your team in an immutable comment thread.',
    tag: 'Collaboration',
  },
  {
    number: '04',
    icon: Lock,
    title: 'Manager approval with a locked report',
    description:
      'Unresolved critical flags prevent publishing. Once approved by a manager, an unalterable snapshot and disclosure report are archived.',
    tag: 'Governance',
  },
]

export function HowItWorksSection() {
  const containerRef = useRef<HTMLDivElement>(null)
  const shouldReduceMotion = useReducedMotion()

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start 75%', 'end 70%'],
  })

  const scaleY = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  })

  return (
    <section className="landing-section how-it-works-section" id="how-it-works" ref={containerRef} aria-labelledby="how-heading">
      <div className="landing-container">
        <div className="landing-section-head">
          <div className="landing-kicker">
            <span className="landing-kicker__icon"><Sparkles size={13} /></span>
            <span>SYSTEM ARCHITECTURE</span>
          </div>
          <h2 id="how-heading" className="landing-section-title">
            How it works<span className="brand-period">.</span>
          </h2>
          <p className="landing-section-subline">
            Four clear steps bridge the gap between creative teams and compliance owners before anything is pushed to public channels.
          </p>
        </div>

        <div className="how-steps-timeline">
          {/* Animated vertical track drawing on scroll */}
          {!shouldReduceMotion && (
            <div className="timeline-track-rail" aria-hidden="true">
              <motion.div
                className="timeline-track-progress"
                style={{ scaleY, transformOrigin: 'top' }}
              />
            </div>
          )}

          <div className="how-steps-grid">
            {steps.map((step, index) => {
              const Icon = step.icon
              return (
                <motion.div
                  key={step.number}
                  className="how-step-card"
                  initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{
                    duration: shouldReduceMotion ? 0 : 0.5,
                    delay: shouldReduceMotion ? 0 : index * 0.1,
                  }}
                >
                  <div className="step-card-top">
                    <span className="step-icon-wrap">
                      <Icon size={20} />
                    </span>
                    <span className="step-number-tag">{step.number}</span>
                  </div>

                  <span className="step-phase-badge">{step.tag}</span>
                  <h3 className="step-title">{step.title}</h3>
                  <p className="step-description">{step.description}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
