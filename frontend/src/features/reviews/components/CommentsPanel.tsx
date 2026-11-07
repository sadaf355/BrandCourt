/**
 * CommentsPanel – B3 Requirement 3
 * Threaded comments per content item and per finding.
 * Short-polls every 10 s. Replies are supported; resolution is read-only until its API is available.
 */
import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, CheckCheck, Reply } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'
import type { Comment } from '../../../types/api'

interface CommentsPanelProps {
  contentId: string
  findingId?: string
  currentUserId: string
  currentUserName: string
}

export function CommentsPanel({
  contentId,
  findingId,
  currentUserId: _currentUserId,
  currentUserName: _currentUserName,
}: CommentsPanelProps) {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const [newBody, setNewBody] = useState('')
  const [replyTo, setReplyTo] = useState<{ id: string; name: string } | null>(null)

  const queryKey = ['comments', contentId, findingId ?? 'item']

  const { data: comments = [], isLoading } = useQuery({
    queryKey,
    queryFn: () => apiClient.listComments(contentId, findingId),
    refetchInterval: 10000,
  })

  const addMutation = useMutation({
    mutationFn: (body: string) =>
      apiClient.addComment(contentId, body, findingId, replyTo?.id),
    onSuccess: () => {
      setNewBody('')
      setReplyTo(null)
      qc.invalidateQueries({ queryKey })
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  const handleSubmit = useCallback(() => {
    const trimmed = newBody.trim()
    if (!trimmed) return
    addMutation.mutate(trimmed)
  }, [newBody, addMutation])

  return (
    <section aria-label={findingId ? 'Finding comments' : 'Item comments'} className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
        <MessageSquare className="w-4 h-4" aria-hidden="true" />
        Comments
        {comments.length > 0 && (
          <span className="ml-auto text-xs text-gray-400">{comments.length}</span>
        )}
      </h3>

      {isLoading && (
        <div className="space-y-2" role="status" aria-label="Loading comments">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && comments.length === 0 && (
        <p className="text-sm text-gray-400 italic">
          No comments yet. Be the first to leave one.
        </p>
      )}

      <ul className="space-y-3">
        {comments.map((comment) => (
          <CommentThread
            key={comment.id}
            comment={comment}
            onReply={(id, name) => {
              setReplyTo({ id, name })
              setNewBody(`@${name} `)
            }}
          />
        ))}
      </ul>

      {/* Compose area */}
      <div className="space-y-2 pt-2">
        {replyTo && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Reply className="w-3.5 h-3.5" aria-hidden="true" />
            Replying to <strong>{replyTo.name}</strong>
            <button
              onClick={() => { setReplyTo(null); setNewBody('') }}
              className="ml-1 underline hover:text-gray-700 dark:hover:text-gray-300"
              aria-label="Cancel reply"
            >
              Cancel
            </button>
          </div>
        )}
        <label htmlFor={`comment-input-${contentId}-${findingId ?? 'item'}`} className="sr-only">
          {replyTo ? `Reply to ${replyTo.name}` : 'Add a comment'}
        </label>
        <textarea
          id={`comment-input-${contentId}-${findingId ?? 'item'}`}
          rows={2}
          value={newBody}
          onChange={(e) => setNewBody(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit()
          }}
          placeholder={replyTo ? `Reply to @${replyTo.name}…` : 'Add a comment… (Ctrl+Enter to submit)'}
          className="w-full px-3 py-2 text-sm border rounded-lg
                     border-gray-200 dark:border-gray-600
                     bg-white dark:bg-gray-800
                     text-gray-900 dark:text-white
                     placeholder-gray-400 focus:ring-2 focus:ring-purple-500 outline-none resize-none"
        />
        <button
          onClick={handleSubmit}
          disabled={!newBody.trim() || addMutation.isPending}
          className="px-4 py-1.5 text-sm font-medium rounded-lg
                     bg-purple-600 hover:bg-purple-700 text-white
                     disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {addMutation.isPending ? 'Posting…' : replyTo ? 'Reply' : 'Comment'}
        </button>
      </div>
    </section>
  )
}

function CommentThread({
  comment,
  onReply,
}: {
  comment: Comment
  onReply: (id: string, name: string) => void
}) {
  return (
    <li className={`space-y-2 ${comment.resolved ? 'opacity-60' : ''}`}>
      <CommentBubble comment={comment} onReply={onReply} />
      {comment.replies && comment.replies.length > 0 && (
        <ul className="ml-6 space-y-2 border-l-2 border-gray-100 dark:border-gray-700 pl-3">
          {comment.replies.map((reply) => (
            <li key={reply.id}>
              <CommentBubble
                comment={reply}
                onReply={onReply}
              />
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

function CommentBubble({
  comment,
  onReply,
}: {
  comment: Comment
  onReply: (id: string, name: string) => void
}) {
  return (
    <article className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                        rounded-lg p-3 space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium text-gray-700 dark:text-gray-300">
            {comment.user_name}
          </span>
          <span className="capitalize text-gray-400">{comment.user_role}</span>
          <time dateTime={comment.created_at}>
            {new Date(comment.created_at).toLocaleString()}
          </time>
          {comment.resolved && (
            <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
              <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
              Resolved
            </span>
          )}
        </div>

      </div>
      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
        {comment.body}
      </p>
      {!comment.resolved && (
        <button
          onClick={() => onReply(comment.id, comment.user_name)}
          className="text-xs text-gray-400 hover:text-purple-600 dark:hover:text-purple-400
                     flex items-center gap-1 transition-colors"
          aria-label={`Reply to ${comment.user_name}`}
        >
          <Reply className="w-3.5 h-3.5" aria-hidden="true" />
          Reply
        </button>
      )}
    </article>
  )
}

