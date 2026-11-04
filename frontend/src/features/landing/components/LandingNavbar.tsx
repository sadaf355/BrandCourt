import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, ArrowRight } from 'lucide-react'
import { ThemeToggle } from '../../../components/ThemeToggle'

export function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`landing-navbar ${scrolled ? 'landing-navbar--scrolled' : ''}`}>
      <div className="landing-container landing-navbar__inner">
        {/* Logo */}
        <Link to="/" className="brand-lockup" aria-label="BrandCourt Home">
          <span className="brand-mark">
            <ShieldCheck size={20} strokeWidth={2.1} />
          </span>
          <span className="brand-word">
            BrandCourt<span className="brand-period">.</span>
            <small>CONTENT TRUST PLATFORM</small>
          </span>
        </Link>

        {/* Navigation Actions */}
        <div className="landing-navbar__actions">
          <ThemeToggle />
          <Link to="/login" className="landing-nav-link">
            Sign in
          </Link>
          <Link to="/signup" className="landing-btn landing-btn--primary landing-btn--compact">
            <span>Create workspace</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </header>
  )
}
