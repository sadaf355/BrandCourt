import React from 'react'

interface RevisionDiffProps {
  previousText: string
  currentText: string
}

// Simple word-level diff calculation
function computeWordDiff(prev: string, curr: string) {
  const prevWords = prev.split(/\s+/).filter(Boolean)
  const currWords = curr.split(/\s+/).filter(Boolean)

  const diff: { text: string; type: 'added' | 'removed' | 'same' }[] = []

  let i = 0
  let j = 0

  while (i < prevWords.length || j < currWords.length) {
    if (i < prevWords.length && j < currWords.length && prevWords[i] === currWords[j]) {
      diff.push({ text: currWords[j], type: 'same' })
      i++
      j++
    } else {
      // Check if word was deleted or added
      if (i < prevWords.length && (!currWords.includes(prevWords[i]) || j >= currWords.length)) {
        diff.push({ text: prevWords[i], type: 'removed' })
        i++
      } else if (j < currWords.length) {
        diff.push({ text: currWords[j], type: 'added' })
        j++
      } else {
        diff.push({ text: prevWords[i], type: 'removed' })
        i++
      }
    }
  }

  return diff
}

export function RevisionDiff({ previousText, currentText }: RevisionDiffProps) {
  const diffWords = computeWordDiff(previousText || '', currentText || '')

  return (
    <div
      className="revision-diff-view"
      style={{
        padding: '1rem',
        borderRadius: '8px',
        backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.25))',
        border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
        fontSize: '0.9rem',
        lineHeight: 1.6,
      }}
      data-testid="revision-diff"
    >
      <div
        style={{
          display: 'flex',
          gap: '1rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          marginBottom: '0.75rem',
          borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          paddingBottom: '0.4rem',
        }}
      >
        <span style={{ color: '#ef4444', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', backgroundColor: '#ef4444', borderRadius: '50%' }} />
          Removed words
        </span>
        <span style={{ color: '#22c55e', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', backgroundColor: '#22c55e', borderRadius: '50%' }} />
          Added words
        </span>
      </div>

      <div style={{ whiteSpace: 'pre-wrap' }}>
        {diffWords.map((item, index) => {
          if (item.type === 'removed') {
            return (
              <span
                key={index}
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  color: '#ef4444',
                  textDecoration: 'line-through',
                  padding: '0.1rem 0.25rem',
                  borderRadius: '3px',
                  marginRight: '0.25rem',
                }}
              >
                {item.text}
              </span>
            )
          }
          if (item.type === 'added') {
            return (
              <span
                key={index}
                style={{
                  backgroundColor: 'rgba(34, 197, 94, 0.2)',
                  color: '#22c55e',
                  padding: '0.1rem 0.25rem',
                  borderRadius: '3px',
                  marginRight: '0.25rem',
                  fontWeight: 600,
                }}
              >
                {item.text}
              </span>
            )
          }
          return <span key={index} style={{ marginRight: '0.25rem' }}>{item.text}</span>
        })}
      </div>
    </div>
  )
}

