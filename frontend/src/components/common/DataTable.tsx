import React, { useState, useMemo } from 'react'
import { Search, ChevronDown, ChevronUp, ChevronLeft, ChevronRight } from 'lucide-react'

export interface Column<T> {
  key: string
  header: string
  render?: (item: T) => React.ReactNode
  sortable?: boolean
}

interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  searchPlaceholder?: string
  searchFilter?: (item: T, query: string) => boolean
  emptyMessage?: string
  pageSize?: number
  onRowClick?: (item: T) => void
}

export function DataTable<T extends { id?: string | number }>({
  data,
  columns,
  searchPlaceholder = 'Search records...',
  searchFilter,
  emptyMessage = 'No matching records found',
  pageSize = 10,
  onRowClick,
}: DataTableProps<T>) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(1)

  // Filter
  const filteredData = useMemo(() => {
    if (!search.trim()) return data
    if (searchFilter) {
      return data.filter((item) => searchFilter(item, search.trim().toLowerCase()))
    }
    // Default search over all string/number fields
    return data.filter((item) =>
      Object.values(item as any).some((val) =>
        String(val).toLowerCase().includes(search.trim().toLowerCase())
      )
    )
  }, [data, search, searchFilter])

  // Sort
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData
    return [...filteredData].sort((a: any, b: any) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      if (aVal === bVal) return 0
      if (aVal === undefined || aVal === null) return 1
      if (bVal === undefined || bVal === null) return -1
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
      return sortDirection === 'asc' ? 1 : -1
    })
  }, [filteredData, sortKey, sortDirection])

  // Pagination
  const totalPages = Math.ceil(sortedData.length / pageSize) || 1
  const paginatedData = useMemo(() => {
    const start = (page - 1) * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, page, pageSize])

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  return (
    <div className="datatable-container" style={{ width: '100%' }}>
      {/* Search and control bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div
          style={{
            position: 'relative',
            flex: '1',
            minWidth: '220px',
            maxWidth: '380px',
          }}
        >
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '0.875rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--color-text-muted, #94a3b8)',
            }}
          />
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder}
            style={{
              width: '100%',
              padding: '0.5rem 0.75rem 0.5rem 2.4rem',
              borderRadius: '8px',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
              backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.4))',
              color: 'var(--color-text-primary, #ffffff)',
              fontSize: '0.85rem',
            }}
          />
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted, #94a3b8)' }}>
          Showing <strong>{paginatedData.length}</strong> of <strong>{filteredData.length}</strong> results
        </div>
      </div>

      {/* Table presentation */}
      <div
        style={{
          overflowX: 'auto',
          borderRadius: '10px',
          border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
          backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.2))',
        }}
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
            fontSize: '0.85rem',
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
                backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.15))',
              }}
            >
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && toggleSort(col.key)}
                  style={{
                    padding: '0.875rem 1rem',
                    fontWeight: 600,
                    color: 'var(--color-text-secondary, #cbd5e1)',
                    cursor: col.sortable ? 'pointer' : 'default',
                    userSelect: 'none',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>{col.header}</span>
                    {col.sortable && sortKey === col.key && (
                      <span>{sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{
                    padding: '3rem 1rem',
                    textAlign: 'center',
                    color: 'var(--color-text-muted, #94a3b8)',
                  }}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginatedData.map((row, idx) => (
                <tr
                  key={row.id ?? idx}
                  onClick={() => onRowClick && onRowClick(row)}
                  style={{
                    borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.1))',
                    cursor: onRowClick ? 'pointer' : 'default',
                    transition: 'background-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (onRowClick) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-bg-subtle, rgba(255, 255, 255, 0.04))'
                  }}
                  onMouseLeave={(e) => {
                    if (onRowClick) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'
                  }}
                >
                  {columns.map((col) => (
                    <td key={col.key} style={{ padding: '0.875rem 1rem' }}>
                      {col.render ? col.render(row) : (row as any)[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination control */}
      {totalPages > 1 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '0.5rem',
            marginTop: '1rem',
          }}
        >
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            aria-label="Previous page"
            style={{
              padding: '0.4rem 0.6rem',
              borderRadius: '6px',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
              backgroundColor: 'transparent',
              color: page === 1 ? 'var(--color-text-muted, #64748b)' : 'var(--color-text-primary, #ffffff)',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
            }}
          >
            <ChevronLeft size={16} />
          </button>
          <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary, #cbd5e1)' }}>
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            aria-label="Next page"
            style={{
              padding: '0.4rem 0.6rem',
              borderRadius: '6px',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
              backgroundColor: 'transparent',
              color: page === totalPages ? 'var(--color-text-muted, #64748b)' : 'var(--color-text-primary, #ffffff)',
              cursor: page === totalPages ? 'not-allowed' : 'pointer',
            }}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  )
}

