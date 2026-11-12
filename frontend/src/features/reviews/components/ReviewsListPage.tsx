import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { ContentItem } from '../../../types/api'
import { apiClient } from '../../../lib/api'
import { DataTable, Column } from '../../../components/common/DataTable'
import { StatusBadge } from '../../../components/common/StatusBadge'
import { Skeleton, ErrorState, EmptyState } from '../../../components/common/FeedbackStates'

export function ReviewsListPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ContentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiClient.listContent()
      setItems(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load reviews')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const columns: Column<ContentItem>[] = [
    {
      key: 'title',
      header: 'Title & Campaign',
      sortable: true,
      render: (item) => (
        <div>
          <strong style={{ fontSize: '0.9rem', color: 'var(--color-text-primary, #ffffff)' }}>
            {item.title}
          </strong>
          {item.campaign && (
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
              Campaign: {item.campaign}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'channel',
      header: 'Channel',
      sortable: true,
      render: (item) => (
        <span
          style={{
            textTransform: 'capitalize',
            padding: '0.15rem 0.5rem',
            borderRadius: '4px',
            backgroundColor: 'var(--color-bg-subtle, rgba(255, 255, 255, 0.08))',
            fontSize: '0.75rem',
          }}
        >
          {item.channel}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Review Status',
      sortable: true,
      render: (item) => <StatusBadge status={item.status} />,
    },
    {
      key: 'current_revision',
      header: 'Revision',
      render: (item) => <span style={{ fontSize: '0.8rem' }}>Rev {item.current_revision}</span>,
    },
    {
      key: 'updated_at',
      header: 'Last Updated',
      sortable: true,
      render: (item) => (
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
          {new Date(item.updated_at).toLocaleDateString()}
        </span>
      ),
    },
  ]

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>Content Reviews</h2>
          <p style={{ color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.875rem', margin: 0 }}>
            Inspect marketing creatives and copy through Claim Court before public release.
          </p>
        </div>

        <button
          onClick={() => navigate('/app/reviews/new')}
          className="landing-btn landing-btn--primary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem' }}
        >
          <Plus size={16} /> New Review
        </button>
      </div>

      {loading ? (
        <div>
          <Skeleton height="50px" />
          <div style={{ marginTop: '0.5rem' }}>
            <Skeleton height="200px" />
          </div>
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No reviews yet"
          description="Create your first marketing draft to run Claim Court checks against your brand rules and facts."
          actionLabel="Create First Review"
          onAction={() => navigate('/app/reviews/new')}
        />
      ) : (
        <DataTable
          data={items}
          columns={columns}
          searchPlaceholder="Search reviews by title, campaign, or channel..."
          onRowClick={(item) => navigate(`/app/reviews/${item.id}`)}
        />
      )}
    </div>
  )
}

