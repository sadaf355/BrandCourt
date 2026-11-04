import { useEffect, useState } from 'react'

export type DeviceCapabilities = {
  hasWebGL: boolean
  prefersReducedMotion: boolean
  isNarrowViewport: boolean
  isSaveData: boolean
  canRender3D: boolean
}

function checkWebGL(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    return Boolean(gl)
  } catch {
    return false
  }
}

export function useDeviceCapabilities(): DeviceCapabilities {
  const [capabilities, setCapabilities] = useState<DeviceCapabilities>(() => {
    const webgl = checkWebGL()
    const reducedMotion = typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false
    const narrow = typeof window !== 'undefined' ? window.innerWidth < 860 : false
    const nav = typeof navigator !== 'undefined' ? (navigator as unknown as { connection?: { saveData?: boolean } }) : undefined
    const saveData = Boolean(nav?.connection?.saveData)

    return {
      hasWebGL: webgl,
      prefersReducedMotion: reducedMotion,
      isNarrowViewport: narrow,
      isSaveData: saveData,
      canRender3D: webgl && !reducedMotion && !narrow && !saveData,
    }
  })

  useEffect(() => {
    if (typeof window === 'undefined') return

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const updateMotion = (e: MediaQueryListEvent) => {
      setCapabilities(prev => ({
        ...prev,
        prefersReducedMotion: e.matches,
        canRender3D: prev.hasWebGL && !e.matches && !prev.isNarrowViewport && !prev.isSaveData,
      }))
    }
    motionQuery.addEventListener('change', updateMotion)

    const updateResize = () => {
      const narrow = window.innerWidth < 860
      setCapabilities(prev => {
        if (prev.isNarrowViewport === narrow) return prev
        return {
          ...prev,
          isNarrowViewport: narrow,
          canRender3D: prev.hasWebGL && !prev.prefersReducedMotion && !narrow && !prev.isSaveData,
        }
      })
    }
    window.addEventListener('resize', updateResize)

    return () => {
      motionQuery.removeEventListener('change', updateMotion)
      window.removeEventListener('resize', updateResize)
    }
  }, [])

  return capabilities
}

