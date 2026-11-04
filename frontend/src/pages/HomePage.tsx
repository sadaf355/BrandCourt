import { motion } from 'framer-motion'
import { ArrowUpRight, BadgeCheck, BookOpenCheck, FileSearch, Layers3, ShieldCheck, Sparkles, Workflow } from 'lucide-react'
import { HealthStatus } from '../components/HealthStatus'

const foundations = [
  { icon: Layers3, title: 'Brand knowledge', desc: 'Guidelines, approved facts and brand assets will live in one trusted workspace.', tag: 'Phase 3' },
  { icon: FileSearch, title: 'Evidence-first review', desc: 'Every claim verdict will point back to a source, version and supporting excerpt.', tag: 'Phase 5' },
  { icon: ShieldCheck, title: 'Human approval', desc: 'Reviewers stay in control, with decisions and overrides captured in an audit trail.', tag: 'Phase 7' },
]

export function HomePage() {
  return (
    <main className="main-content">
      <motion.section className="hero-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: 'easeOut' }}>
        <div className="hero-card__glow hero-card__glow--one" /><div className="hero-card__glow hero-card__glow--two" />
        <div className="hero-card__content">
          <div className="hero-kicker"><span className="hero-kicker__spark"><Sparkles size={13} /></span> BRAND INTEGRITY, WITH EVIDENCE</div>
          <h1>Good content.<br /><span>Grounded in truth.</span></h1>
          <p className="hero-description">BrandCourt helps teams review marketing content against approved brand facts and guidelines — so every claim is accountable, explainable, and ready for human approval.</p>
          <div className="hero-pills"><span><BadgeCheck size={14} /> Evidence-backed</span><span><BookOpenCheck size={14} /> Guideline-aware</span><span><Workflow size={14} /> Human-led</span></div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="orbit orbit--outer" /><div className="orbit orbit--inner" />
          <div className="hero-core"><ShieldCheck size={35} strokeWidth={1.5} /></div>
          <div className="float-card float-card--top"><span className="float-card__check"><BadgeCheck size={15} /></span><span><b>Evidence linked</b><small>Source verified</small></span></div>
          <div className="float-card float-card--bottom"><span className="float-card__pulse" /><span><b>Human in control</b><small>Review before approval</small></span></div>
        </div>
      </motion.section>

      <div className="workspace-heading"><div><p className="eyebrow">YOUR WORKSPACE</p><h2>Foundation overview</h2><p className="muted-copy">The core project shell is in place. Feature workflows will be added phase by phase.</p></div><span className="phase-chip"><span className="phase-chip__dot" /> Phase 1 · Foundation</span></div>

      <section className="foundation-grid" aria-label="Product principles">
        {foundations.map((item, index) => {
          const Icon = item.icon
          return <motion.article className="foundation-card" key={item.title} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 * index, duration: 0.35 }}>
            <div className="foundation-card__top"><span className="feature-icon"><Icon size={19} /></span><span className="roadmap-tag">{item.tag}</span></div>
            <h3>{item.title}</h3><p>{item.desc}</p><div className="foundation-card__footer"><span>Planned capability</span><ArrowUpRight size={15} /></div>
          </motion.article>
        })}
      </section>
      <HealthStatus />
      <footer className="app-footer"><span>BrandCourt <span className="footer-separator">/</span> Foundation build</span><span>Built for accountable content decisions.</span></footer>
    </main>
  )
}
