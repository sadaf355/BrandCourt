import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../../providers/ThemeProvider'
import { LandingPage } from '../LandingPage'
import { HeroShieldView } from '../components/three/HeroShieldView'

// Avoid loading Three.js into jsdom
vi.mock('../components/three/ShieldCanvas', () => ({ default: () => null }))

describe('BrandCourt Public Landing Page', () => {
  beforeEach(() => {
    // Reset matchMedia to default (no reduced motion)
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders all 5 required sections on the landing page', () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </ThemeProvider>
    )

    // Section 1: Hero
    expect(screen.getByRole('heading', { level: 1, name: /every claim needs proof/i })).toBeDefined()

    // Section 2: The Fix in Action
    expect(screen.getByRole('heading', { level: 2, name: /the fix in action/i })).toBeDefined()
    expect(screen.getByText(/sample data, not live results/i)).toBeDefined()

    // Section 3: How It Works
    expect(screen.getByRole('heading', { level: 2, name: /how it works/i })).toBeDefined()
    expect(screen.getByText(/upload text or image/i)).toBeDefined()
    expect(screen.getByText(/three-layer check/i)).toBeDefined()

    // Section 4: Why Trust It
    expect(screen.getByRole('heading', { level: 2, name: /why trust it/i })).toBeDefined()
    expect(screen.getByText(/evidence, not opinions/i)).toBeDefined()
    expect(screen.getByText(/humans decide/i)).toBeDefined()
    expect(screen.getByText(/privacy by design/i)).toBeDefined()

    // Section 5: Final CTA and Footer
    expect(
      screen.getByRole('heading', { level: 2, name: /ready to verify brand truth before publication/i })
    ).toBeDefined()
    expect(screen.getByText(/starter india rules pack, not legal advice/i)).toBeDefined()
  })

  it('provides navigation links for both primary CTAs to /signup and /login', () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </ThemeProvider>
    )

    const createWorkspaceLinks = screen.getAllByRole('link', { name: /create workspace/i })
    expect(createWorkspaceLinks.length).toBeGreaterThan(0)
    expect(createWorkspaceLinks[0].getAttribute('href')).toBe('/signup')

    const signInLinks = screen.getAllByRole('link', { name: /sign in/i })
    expect(signInLinks.length).toBeGreaterThan(0)
    expect(signInLinks[0].getAttribute('href')).toBe('/login')
  })

  it('renders the static poster instead of 3D canvas when WebGL is unavailable', () => {
    // Mock getContext to fail for webgl
    const originalGetContext = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((contextId: string) => {
      if (contextId.includes('webgl')) return null
      return null
    })

    render(
      <ThemeProvider>
        <MemoryRouter>
          <HeroShieldView />
        </MemoryRouter>
      </ThemeProvider>
    )

    // Should render the static poster fallback with descriptive alt text
    const poster = screen.getByTestId('shield-poster')
    expect(poster).toBeDefined()
    const posterImg = screen.getByAltText(/brandcourt 3d glass security shield/i)
    expect(posterImg).toBeDefined()
    expect(posterImg.getAttribute('src')).toBe('/landing/shield-poster.webp')

    // Canvas wrapper should not be rendered
    expect(screen.queryByTestId('shield-3d-wrapper')).toBeNull()

    HTMLCanvasElement.prototype.getContext = originalGetContext
  })

  it('renders the static poster instead of 3D canvas when prefers-reduced-motion is enabled', () => {
    // Mock matchMedia to return true for reduced motion
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))

    render(
      <ThemeProvider>
        <MemoryRouter>
          <HeroShieldView />
        </MemoryRouter>
      </ThemeProvider>
    )

    const poster = screen.getByTestId('shield-poster')
    expect(poster).toBeDefined()
    expect(screen.queryByTestId('shield-3d-wrapper')).toBeNull()
  })
})
