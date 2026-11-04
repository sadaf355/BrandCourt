export function ShieldPoster({ priority = false }: { priority?: boolean }) {
  return (
    <div className="shield-poster-container" data-testid="shield-poster">
      <img
        src="/landing/shield-poster.webp"
        alt="BrandCourt 3D Glass Security Shield showing evidence checks and active verification seals"
        width={500}
        height={500}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        className="shield-poster-image"
      />
    </div>
  )
}
