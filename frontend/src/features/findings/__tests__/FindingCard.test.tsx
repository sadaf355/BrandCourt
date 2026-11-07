import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FindingCard } from '../components/FindingCard'
import { ClaimFinding } from '../../../types/api'

const sampleFinding: ClaimFinding = {
  id: 'fnd-test-1',
  claim_text: 'cures acne in 28 days',
  verdict: 'contradicted',
  severity: 'critical',
  layer: 'rules',
  analysis_method: 'rule_in_5',
  rationale: 'Cosmetic products cannot make medical cure claims under Indian law.',
  confidence: 0.99,
  state: 'open',
  suggested_fix: 'reduces the appearance of acne blemishes',
  intent_preserved: {
    purpose: 'Address blemish reduction',
    cta: 'None',
    claims_changed: ['Changed cure to appearance reduction'],
    safe: true,
  },
  evidence: [
    {
      source_type: 'rule',
      title: 'Rule IN-5: Medical claims prohibition',
      statement: 'No cosmetic shall claim to treat or cure skin disorders.',
    },
  ],
  created_at: new Date().toISOString(),
}

describe('FindingCard Component', () => {
  it('renders claim text, rationale, severity, and suggested fix', () => {
    render(<FindingCard finding={sampleFinding} />)
    expect(screen.getByText('"cures acne in 28 days"')).toBeDefined()
    expect(screen.getByText(sampleFinding.rationale)).toBeDefined()
    expect(screen.getByText('Critical')).toBeDefined()
    expect(screen.getByText('"reduces the appearance of acne blemishes"')).toBeDefined()
  })

  it('triggers accept action on button click', () => {
    const handleAccept = vi.fn()
    render(<FindingCard finding={sampleFinding} onAccept={handleAccept} />)
    const acceptBtn = screen.getByRole('button', { name: /accept finding/i })
    fireEvent.click(acceptBtn)
    expect(handleAccept).toHaveBeenCalledTimes(1)
  })

  it('allows creator to apply suggested safe fix', () => {
    const handleEdit = vi.fn()
    render(<FindingCard finding={sampleFinding} onEdit={handleEdit} />)
    const applyBtn = screen.getByRole('button', { name: /apply fix/i })
    fireEvent.click(applyBtn)
    expect(handleEdit).toHaveBeenCalledWith('reduces the appearance of acne blemishes')
  })
})

