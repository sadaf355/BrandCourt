import { useMemo, useRef, useEffect, useState } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Environment, Lightformer, Html } from '@react-three/drei'

function createShieldShape(s = 1): THREE.Shape {
  const shape = new THREE.Shape()
  shape.moveTo(0, 1.4 * s)
  shape.quadraticCurveTo(0.72 * s, 1.43 * s, 1.18 * s, 1.15 * s)
  shape.bezierCurveTo(1.24 * s, 0.42 * s, 0.96 * s, -0.62 * s, 0, -1.48 * s)
  shape.bezierCurveTo(-0.96 * s, -0.62 * s, -1.24 * s, 0.42 * s, -1.18 * s, 1.15 * s)
  shape.quadraticCurveTo(-0.72 * s, 1.43 * s, 0, 1.4 * s)
  return shape
}

function OrbitCard({
  label,
  sublabel,
  radius,
  speed,
  phase,
  yOffset,
  badgeColor = '#2dd4bf',
}: {
  label: string
  sublabel?: string
  radius: number
  speed: number
  phase: number
  yOffset: number
  badgeColor?: string
}) {
  const ref = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (!ref.current) return
    const t = state.clock.elapsedTime * speed + phase
    const x = Math.sin(t) * radius
    const z = Math.cos(t) * radius * 0.75
    ref.current.position.set(x, yOffset + Math.sin(t * 1.5) * 0.12, z)
    ref.current.rotation.y = -t * 0.45
  })

  return (
    <group ref={ref}>
      <Html transform center distanceFactor={4.8} zIndexRange={[10, 0]}>
        <div
          className="orbit-evidence-badge"
          style={{
            borderColor: `${badgeColor}55`,
            boxShadow: `0 8px 24px rgba(0, 0, 0, 0.25), 0 0 16px ${badgeColor}22`,
          }}
        >
          <span className="orbit-badge-dot" style={{ background: badgeColor }} />
          <div className="orbit-badge-text">
            <strong>{label}</strong>
            {sublabel && <small>{sublabel}</small>}
          </div>
        </div>
      </Html>
    </group>
  )
}

export function ShieldScene() {
  const shieldGroupRef = useRef<THREE.Group>(null)
  const [isDark, setIsDark] = useState<boolean>(() =>
    typeof document !== 'undefined' ? document.documentElement.classList.contains('dark') : true
  )

  useEffect(() => {
    if (typeof document === 'undefined') return
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'))
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  // Geometries for shield layers
  const { rimGeometry, trimGeometry, glassGeometry } = useMemo(() => {
    const rimShape = createShieldShape(1.03)
    const trimShape = createShieldShape(1.0)
    const glassShape = createShieldShape(0.96)

    const rimGeo = new THREE.ExtrudeGeometry(rimShape, {
      depth: 0.14,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: 0.04,
      bevelThickness: 0.04,
    })
    const trimGeo = new THREE.ExtrudeGeometry(trimShape, {
      depth: 0.13,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: 0.03,
      bevelThickness: 0.03,
    })
    const glassGeo = new THREE.ExtrudeGeometry(glassShape, {
      depth: 0.11,
      bevelEnabled: true,
      bevelSegments: 5,
      steps: 1,
      bevelSize: 0.04,
      bevelThickness: 0.04,
    })

    // Center geometries
    rimGeo.center()
    trimGeo.center()
    glassGeo.center()

    return { rimGeometry: rimGeo, trimGeometry: trimGeo, glassGeometry: glassGeo }
  }, [])

  // Scroll listener for scroll tilt
  const scrollRef = useRef(0)
  useEffect(() => {
    const onScroll = () => {
      scrollRef.current = window.scrollY
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useFrame((state, delta) => {
    if (!shieldGroupRef.current) return
    const time = state.clock.elapsedTime

    // Gentle idle float
    const idleY = Math.sin(time * 1.1) * 0.07
    const idleYaw = Math.sin(time * 0.5) * 0.06

    // Interactive mouse tilt with smooth damping
    const targetRotX = -state.pointer.y * 0.28 + (scrollRef.current * 0.0003)
    const targetRotY = state.pointer.x * 0.38 + idleYaw
    const targetRotZ = -state.pointer.x * 0.08

    shieldGroupRef.current.position.y = THREE.MathUtils.damp(shieldGroupRef.current.position.y, idleY, 4, delta)
    shieldGroupRef.current.rotation.x = THREE.MathUtils.damp(shieldGroupRef.current.rotation.x, targetRotX, 4, delta)
    shieldGroupRef.current.rotation.y = THREE.MathUtils.damp(shieldGroupRef.current.rotation.y, targetRotY, 4, delta)
    shieldGroupRef.current.rotation.z = THREE.MathUtils.damp(shieldGroupRef.current.rotation.z, targetRotZ, 4, delta)
  })

  // Cleanup geometries on unmount
  useEffect(() => {
    return () => {
      rimGeometry.dispose()
      trimGeometry.dispose()
      glassGeometry.dispose()
    }
  }, [rimGeometry, trimGeometry, glassGeometry])

  return (
    <>
      {/* Lighting with local Lightformers - no external HDRI or CDN */}
      <ambientLight intensity={isDark ? 0.35 : 0.65} />
      <directionalLight position={[4, 5, 5]} intensity={1.3} color="#f8fafc" />
      <pointLight
        position={[-3.5, 2, -1.8]}
        intensity={isDark ? 5.5 : 3.0}
        color="#2dd4bf"
        distance={12}
      />
      <pointLight position={[2, -3, 2]} intensity={1.2} color="#0f766e" distance={8} />

      <Environment resolution={256}>
        <group rotation={[-Math.PI / 4, -0.4, 0]}>
          <Lightformer form="rect" intensity={3} position={[3, 5, 4]} scale={[6, 6, 1]} color="#ffffff" />
          <Lightformer form="rect" intensity={4} position={[-4, -2, 2]} scale={[4, 4, 1]} color="#2dd4bf" />
          <Lightformer form="circle" intensity={2} position={[0, -4, -3]} scale={[4, 4, 1]} color="#0f766e" />
        </group>
      </Environment>

      {/* Main Shield and orbiting elements */}
      <group position={[0, 0, 0]}>
        <group ref={shieldGroupRef}>
          {/* Teal emissive outer rim */}
          <mesh geometry={rimGeometry} position={[0, 0, -0.015]}>
            <meshStandardMaterial
              color="#0f766e"
              emissive="#2dd4bf"
              emissiveIntensity={isDark ? 0.95 : 0.45}
              roughness={0.25}
              metalness={0.4}
            />
          </mesh>

          {/* Thin metallic bezel / trim */}
          <mesh geometry={trimGeometry} position={[0, 0, 0.0]}>
            <meshStandardMaterial
              color={isDark ? '#1e293b' : '#334155'}
              metalness={0.92}
              roughness={0.18}
            />
          </mesh>

          {/* Midnight-ink physical glass body with transmission and clearcoat */}
          <mesh geometry={glassGeometry} position={[0, 0, 0.025]}>
            <meshPhysicalMaterial
              color={isDark ? '#0b1622' : '#0f1f2e'}
              transmission={0.78}
              roughness={0.09}
              ior={1.52}
              thickness={0.8}
              clearcoat={1.0}
              clearcoatRoughness={0.06}
              attenuationColor="#0f766e"
              attenuationDistance={0.7}
              transparent
              opacity={0.96}
            />
          </mesh>

          {/* Embossed check-mark seal */}
          <group position={[0, 0, 0.12]}>
            {/* Outer metallic seal ring */}
            <mesh position={[0, 0, 0]}>
              <ringGeometry args={[0.34, 0.42, 48]} />
              <meshStandardMaterial
                color="#2dd4bf"
                emissive="#2dd4bf"
                emissiveIntensity={isDark ? 0.6 : 0.25}
                metalness={0.8}
                roughness={0.2}
              />
            </mesh>
            {/* Dark glass inner seal disc */}
            <mesh position={[0, 0, -0.005]}>
              <circleGeometry args={[0.34, 48]} />
              <meshStandardMaterial
                color="#0f2631"
                roughness={0.2}
                metalness={0.5}
              />
            </mesh>
            {/* Embossed check-mark seal front */}
            <group position={[0, 0, 0.015]}>
              <mesh position={[-0.14, -0.11, 0]} rotation={[0, 0, Math.PI / 4]}>
                <boxGeometry args={[0.07, 0.26, 0.03]} />
                <meshStandardMaterial color="#f0fdfa" emissive="#2dd4bf" emissiveIntensity={0.4} roughness={0.2} />
              </mesh>
              <mesh position={[0.09, -0.02, 0]} rotation={[0, 0, -Math.PI / 3.4]}>
                <boxGeometry args={[0.07, 0.46, 0.03]} />
                <meshStandardMaterial color="#f0fdfa" emissive="#2dd4bf" emissiveIntensity={0.4} roughness={0.2} />
              </mesh>
            </group>
          </group>
        </group>

        {/* Orbiting evidence cards at different depths and speeds */}
        <OrbitCard
          label="Fact v3"
          sublabel="Source verified"
          radius={2.1}
          speed={0.48}
          phase={0}
          yOffset={0.45}
          badgeColor="#2dd4bf"
        />
        <OrbitCard
          label="Rule IN-4"
          sublabel="Policy check"
          radius={2.45}
          speed={-0.38}
          phase={2.2}
          yOffset={-0.2}
          badgeColor="#5eead4"
        />
        <OrbitCard
          label="Approved"
          sublabel="Snapshot locked"
          radius={1.9}
          speed={0.62}
          phase={4.4}
          yOffset={-0.7}
          badgeColor="#34d399"
        />
      </group>
    </>
  )
}
