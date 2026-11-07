import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { StatusBadge } from '../StatusBadge'
import { SeverityBadge } from '../SeverityBadge'
import { EmptyState, ErrorState, PermissionDeniedState } from '../FeedbackStates'
import { ConfirmDialog } from '../ConfirmDialog'

describe('Reusable Common UI Components', () => {
  it('renders StatusBadge with accessible text and proper status', () => {
    const { rerender } = render(<StatusBadge status="approved" />)
    expect(screen.getByTestId('status-badge')).toBeDefined()
    expect(screen.getByText('Approved')).toBeDefined()

    rerender(<StatusBadge status="submitted" />)
    expect(screen.getByText('Submitted')).toBeDefined()
  })

  it('renders SeverityBadge with both label and sublabel (never color alone)', () => {
    render(<SeverityBadge severity="critical" />)
    const badge = screen.getByTestId('severity-badge')
    expect(badge).toBeDefined()
    expect(screen.getByText('Critical')).toBeDefined()
    expect(screen.getByText('Blocks approval')).toBeDefined()
  })

  it('renders EmptyState with action button trigger', () => {
    const handleAction = vi.fn()
    render(
      <EmptyState
        title="No items found"
        description="Try creating one now"
        actionLabel="Create Item"
        onAction={handleAction}
      />
    )
    expect(screen.getByText('No items found')).toBeDefined()
    const btn = screen.getByRole('button', { name: 'Create Item' })
    fireEvent.click(btn)
    expect(handleAction).toHaveBeenCalledTimes(1)
  })

  it('renders ErrorState with retry trigger', () => {
    const handleRetry = vi.fn()
    render(<ErrorState message="Server connection failed" onRetry={handleRetry} />)
    expect(screen.getByText('Server connection failed')).toBeDefined()
    const retryBtn = screen.getByRole('button', { name: /retry/i })
    fireEvent.click(retryBtn)
    expect(handleRetry).toHaveBeenCalledTimes(1)
  })

  it('renders PermissionDeniedState with role requirements', () => {
    render(<PermissionDeniedState requiredRole="admin" />)
    expect(screen.getByRole('alert')).toBeDefined()
    expect(screen.getByText(/Access Restricted/i)).toBeDefined()
  })

  it('renders ConfirmDialog and responds to confirm/cancel', () => {
    const handleConfirm = vi.fn()
    const handleCancel = vi.fn()

    const { rerender } = render(
      <ConfirmDialog
        isOpen={true}
        title="Delete finding?"
        message="Are you sure?"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )

    expect(screen.getByRole('dialog')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(handleConfirm).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(handleCancel).toHaveBeenCalledTimes(1)

    rerender(
      <ConfirmDialog
        isOpen={false}
        title="Delete finding?"
        message="Are you sure?"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})

