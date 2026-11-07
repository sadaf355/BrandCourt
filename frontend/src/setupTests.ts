import '@testing-library/react'

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock IntersectionObserver
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null
  readonly rootMargin: string = ''
  readonly thresholds: ReadonlyArray<number> = []
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}
Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
})

// Mock ResizeObserver
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: MockResizeObserver,
})

// Polyfill Map.groupBy for Node < 21 environments (e.g. CI on Node 20)
if (typeof (Map as any).groupBy !== 'function') {
  ;(Map as any).groupBy = function <K, T>(items: Iterable<T>, callbackfn: (value: T, index: number) => K): Map<K, T[]> {
    const map = new Map<K, T[]>()
    let i = 0
    for (const item of items) {
      const key = callbackfn(item, i++)
      const list = map.get(key)
      if (list) {
        list.push(item)
      } else {
        map.set(key, [item])
      }
    }
    return map
  }
}

