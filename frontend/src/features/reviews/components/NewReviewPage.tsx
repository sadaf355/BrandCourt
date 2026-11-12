import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Upload, AlertTriangle, ArrowLeft } from 'lucide-react'
import { Channel } from '../../../types/api'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'

const reviewSchema = z.object({
  title: z.string().min(2, 'Title must be at least 2 characters').max(200, 'Title cannot exceed 200 characters'),
  channel: z.enum([
    'website',
    'instagram',
    'facebook',
    'linkedin',
    'email',
    'paid_ad',
    'packaging',
    'other',
  ]),
  campaign: z.string().max(200, 'Campaign name cannot exceed 200 characters').optional(),
  caption: z.string().min(5, 'Caption must be at least 5 characters').max(30000, 'Caption exceeds maximum length'),
  alt_text: z.string().max(3000, 'Alt text exceeds maximum length').optional(),
  is_ai_media: z.boolean(),
  is_paid_gifted: z.boolean(),
})

type ReviewFormData = z.infer<typeof reviewSchema>

export function NewReviewPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [creativePreview, setCreativePreview] = useState<string | null>(null)
  const [creativeFile, setCreativeFile] = useState<File | null>(null)
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ReviewFormData>({
    resolver: zodResolver(reviewSchema),
    defaultValues: {
      title: 'GlowSerum Launch Instagram Reel',
      channel: 'instagram',
      campaign: 'Festive Radiance 2026',
      caption:
        "Experience India's #1 radiant skin formula! Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results.",
      alt_text: 'Bottle of Aurora GlowSerum with saffron dropper and botanical elements',
      is_ai_media: false,
      is_paid_gifted: true,
    },
  })

  const captionText = watch('caption')

  // Client-side quick language heuristic
  const isHindiScript = /[\u0900-\u097F]/.test(captionText || '')
  const detectedLanguage = isHindiScript ? 'Hindi/Marathi (Devanagari script)' : 'English or other Latin-script text'

  const handleCreativeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setCreativeFile(file)
    setSubmitError('')
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setCreativePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    } else {
      setCreativePreview(null)
    }
  }

  const onSubmit = async (data: ReviewFormData) => {
    if (submitting) return
    setSubmitting(true)
    setSubmitError('')
    try {
      const created = await apiClient.createContent({
        title: data.title,
        channel: data.channel as Channel,
        campaign: data.campaign,
        caption: data.caption,
        alt_text: data.alt_text,
        is_ai_media: data.is_ai_media,
        paid_gifted: data.is_paid_gifted,
      })

      if (creativeFile) {
        try {
          await apiClient.uploadCreative(created.id, creativeFile)
        } catch (uploadErr: any) {
          const msg = uploadErr?.message || 'Creative image upload failed.'
          setSubmitError(`Draft created, but creative upload failed: ${msg}`)
          showToast(msg, 'error')
          return
        }
      }

      showToast('Review created successfully! Redirecting to Claim Court workbench...', 'success')
      navigate(`/app/reviews/${created.id}`)
    } catch (err: any) {
      const msg = err?.message || 'Failed to create review'
      setSubmitError(msg)
      showToast(msg, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ maxWidth: '860px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <button
        type="button"
        onClick={() => navigate('/app/reviews')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.85rem',
          color: 'var(--color-text-muted, #94a3b8)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          marginBottom: '1.25rem',
        }}
      >
        <ArrowLeft size={16} /> Back to reviews
      </button>

      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.6rem', fontWeight: 700, margin: '0 0 0.4rem 0' }}>New Content Review</h2>
        <p style={{ color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.9rem', margin: 0 }}>
          Submit marketing copy and creative media to verify brand guidelines and legal claims before publication.
        </p>
      </div>

      {isHindiScript && <div role="status" aria-live="polite" className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
        <strong>Limited language support:</strong> Devanagari content may include Hindi or Marathi. Automated language and claim checks have limited coverage for Marathi and mixed-language phrasing. Please have a fluent reviewer verify nuance, idioms and claim meaning before approval.
      </div>}

      {submitError && (
        <div role="alert" className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <div
          style={{
            backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.6))',
            borderRadius: '12px',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
            padding: '1.75rem',
            marginBottom: '1.5rem',
          }}
        >
          {/* Title & Channel */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '1.25rem' }}>
            <div>
              <label htmlFor="review-title" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                Content Title *
              </label>
              <input
                id="review-title"
                {...register('title')}
                placeholder="e.g. Festive Launch Instagram Reel"
                style={{
                  width: '100%',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                  border: `1px solid ${errors.title ? '#ef4444' : 'var(--color-border, rgba(148, 163, 184, 0.25))'}`,
                  color: 'var(--color-text-primary, #ffffff)',
                  fontSize: '0.9rem',
                }}
              />
              {errors.title && <span style={{ color: '#ef4444', fontSize: '0.75rem' }}>{errors.title.message}</span>}
            </div>

            <div>
              <label htmlFor="review-channel" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                Target Channel *
              </label>
              <select
                id="review-channel"
                {...register('channel')}
                style={{
                  width: '100%',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                  border: '1px solid var(--color-border, rgba(148, 163, 184, 0.25))',
                  color: 'var(--color-text-primary, #ffffff)',
                  fontSize: '0.9rem',
                }}
              >
                <option value="instagram">Instagram</option>
                <option value="website">Website / Landing Page</option>
                <option value="paid_ad">Paid Digital Ad</option>
                <option value="facebook">Facebook</option>
                <option value="linkedin">LinkedIn</option>
                <option value="email">Email Newsletter</option>
                <option value="packaging">Packaging / Print</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          {/* Campaign */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label htmlFor="review-campaign" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              Campaign Name (Optional)
            </label>
            <input
              id="review-campaign"
              {...register('campaign')}
              placeholder="e.g. Q4 Festive Radiance"
              style={{
                width: '100%',
                padding: '0.65rem 0.85rem',
                borderRadius: '6px',
                backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.25))',
                color: 'var(--color-text-primary, #ffffff)',
                fontSize: '0.9rem',
              }}
            />
          </div>

          {/* Caption Text Area */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label htmlFor="review-caption" style={{ fontSize: '0.85rem', fontWeight: 600 }}>Caption / Marketing Copy *</label>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
                Detected Language: <strong>{detectedLanguage}</strong>
              </div>
            </div>
            <textarea
              id="review-caption"
              {...register('caption')}
              rows={5}
              placeholder="Write or paste marketing copy here..."
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '6px',
                backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                border: `1px solid ${errors.caption ? '#ef4444' : 'var(--color-border, rgba(148, 163, 184, 0.25))'}`,
                color: 'var(--color-text-primary, #ffffff)',
                fontSize: '0.9rem',
                lineHeight: 1.5,
              }}
            />
            {errors.caption && <span style={{ color: '#ef4444', fontSize: '0.75rem' }}>{errors.caption.message}</span>}

            {isHindiScript && (
              <div
                style={{
                  marginTop: '0.5rem',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(234, 179, 8, 0.1)',
                  border: '1px solid rgba(234, 179, 8, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.775rem',
                  color: '#eab308',
                }}
              >
                <AlertTriangle size={15} />
                <span>
                  Limited support notice: Semantic claim comparison is optimized for English text. Devanagari/Hindi will
                  undergo token screening with human review recommendation.
                </span>
              </div>
            )}
          </div>

          {/* Creative Media Upload & Preview */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              Creative Media (Image / Poster)
            </label>
            <div
              style={{
                border: '2px dashed var(--color-border, rgba(148, 163, 184, 0.25))',
                borderRadius: '8px',
                padding: '1.5rem',
                textAlign: 'center',
                backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.15))',
              }}
            >
              <input
                type="file"
                id="creative-upload"
                accept="image/*"
                onChange={handleCreativeChange}
                style={{ display: 'none' }}
              />
              <label
                htmlFor="creative-upload"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--color-bg-subtle, rgba(255, 255, 255, 0.1))',
                  border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
                  color: 'var(--color-text-primary, inherit)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  marginBottom: '0.5rem',
                }}
              >
                <Upload size={16} /> Choose Image File
              </label>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
                PNG, JPG, or WEBP. Embedded text will be extracted via OCR during analysis.
              </div>

              {creativePreview && (
                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center' }}>
                  <img
                    src={creativePreview}
                    alt="Creative Preview"
                    style={{
                      maxHeight: '180px',
                      borderRadius: '6px',
                      border: '1px solid rgba(148, 163, 184, 0.3)',
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Alt text */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label htmlFor="review-alt-text" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              Accessibility Alt Text
            </label>
            <input
              id="review-alt-text"
              {...register('alt_text')}
              placeholder="Describe creative image for visually impaired readers..."
              style={{
                width: '100%',
                padding: '0.65rem 0.85rem',
                borderRadius: '6px',
                backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.25))',
                color: 'var(--color-text-primary, #ffffff)',
                fontSize: '0.9rem',
              }}
            />
          </div>

          {/* Declarations: Paid/Gifted & AI Media */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
              padding: '1rem',
              borderRadius: '8px',
              backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
            }}
          >
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input type="checkbox" {...register('is_paid_gifted')} style={{ width: '16px', height: '16px' }} />
              <span>
                <strong>Paid partnership or gifted collaboration</strong> (ensures compliance with disclosure rules)
              </span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input type="checkbox" {...register('is_ai_media')} style={{ width: '16px', height: '16px' }} />
              <span>
                <strong>Contains synthetic / AI-generated media</strong> (requires synthetic disclosure badge)
              </span>
            </label>
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
          <button
            type="button"
            onClick={() => navigate('/app/reviews')}
            style={{
              padding: '0.65rem 1.25rem',
              borderRadius: '6px',
              backgroundColor: 'transparent',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
              color: 'var(--color-text-primary, #ffffff)',
              fontSize: '0.9rem',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="landing-btn landing-btn--primary"
            style={{ fontSize: '0.9rem', padding: '0.65rem 1.5rem' }}
          >
            {submitting ? 'Creating draft...' : 'Create Review & Open Claim Court'}
          </button>
        </div>
      </form>
    </div>
  )
}
