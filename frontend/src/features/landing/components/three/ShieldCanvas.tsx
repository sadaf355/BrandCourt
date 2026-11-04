import { Component, type ReactNode, useEffect, useRef, useState, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { ShieldScene } from './ShieldScene'
import { ShieldPoster } from './ShieldPoster'

type ErrorBoundaryProps = {
  children: ReactNode
  fallback: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
}

class ThreeErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error) {
    console.warn('Shield 3D Canvas error caught by boundary, falling back to static poster:', error)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback
    }
    return this.props.children
  }
}

export default function ShieldCanvas() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(true)
  const [isTabHidden, setIsTabHidden] = useState(false)

  useEffect(() => {
    const handleVisibility = () => {
      setIsTabHidden(document.hidden)
    }
    document.addEventListener('visibilitychange', handleVisibility)

    const observer = new IntersectionObserver(
      ([entry]) => {
        setInView(entry.isIntersecting)
      },
      { threshold: 0.1 }
    )

    if (containerRef.current) {
      observer.observe(containerRef.current)
    }

    return () => {
      document.removeEventListener('visibilitychange', handleVisibility)
      observer.disconnect()
    }
  }, [])

  const shouldAnimate = inView && !isTabHidden

  return (
    <div ref={containerRef} className="shield-3d-wrapper" data-testid="shield-3d-wrapper">
      <ThreeErrorBoundary fallback={<ShieldPoster />}>
        <div className="shield-canvas-container" aria-hidden="true">
          <Canvas
            frameloop={shouldAnimate ? 'always' : 'never'}
            dpr={[1, 1.75]}
            camera={{ position: [0, 0, 4.4], fov: 45 }}
            gl={{
              alpha: true,
              antialias: true,
              powerPreference: 'high-performance',
            }}
            style={{ width: '100%', height: '100%', pointerEvents: 'auto' }}
          >
            <Suspense fallback={null}>
              <ShieldScene />
            </Suspense>
          </Canvas>
        </div>
      </ThreeErrorBoundary>
    </div>
  )
}
