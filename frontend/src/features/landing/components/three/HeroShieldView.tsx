import { lazy, Suspense } from 'react'
import { useDeviceCapabilities } from './useDeviceCapabilities'
import { ShieldPoster } from './ShieldPoster'

const LazyShieldCanvas = lazy(() => import('./ShieldCanvas'))

export function HeroShieldView() {
  const { canRender3D } = useDeviceCapabilities()

  if (!canRender3D) {
    return <ShieldPoster priority />
  }

  return (
    <Suspense fallback={<ShieldPoster priority />}>
      <LazyShieldCanvas />
    </Suspense>
  )
}
