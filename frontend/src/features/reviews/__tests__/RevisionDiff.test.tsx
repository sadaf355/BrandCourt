import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RevisionDiff } from '../components/RevisionDiff'

describe('RevisionDiff Component', () => {
  it('highlights added and removed words distinctly', () => {
    const prev = 'cures acne in 28 days'
    const curr = 'reduces the appearance of acne blemishes in 28 days'

    render(<RevisionDiff previousText={prev} currentText={curr} />)

    expect(screen.getByTestId('revision-diff')).toBeDefined()
    expect(screen.getByText('Removed words')).toBeDefined()
    expect(screen.getByText('Added words')).toBeDefined()
    expect(screen.getByText('cures')).toBeDefined()
    expect(screen.getByText('reduces')).toBeDefined()
  })
})

