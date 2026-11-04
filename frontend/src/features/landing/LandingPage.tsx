import { LandingNavbar } from './components/LandingNavbar'
import { HeroSection } from './components/HeroSection'
import { FixInActionSection } from './components/FixInActionSection'
import { HowItWorksSection } from './components/HowItWorksSection'
import { WhyTrustItSection } from './components/WhyTrustItSection'
import { CtaSection } from './components/CtaSection'
import './landing.css'

export function LandingPage() {
  return (
    <div className="landing-page-root">
      {/* Sticky Navbar */}
      <LandingNavbar />

      <main id="main-content">
        {/* Section 1: Hero with 3D Shield */}
        <HeroSection />

        {/* Section 2: The Fix in Action */}
        <FixInActionSection />

        {/* Section 3: How it Works */}
        <HowItWorksSection />

        {/* Section 4: Why Trust It */}
        <WhyTrustItSection />

        {/* Section 5: Final Call to Action and Footer */}
        <CtaSection />
      </main>
    </div>
  )
}
