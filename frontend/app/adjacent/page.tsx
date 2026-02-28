'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchSignals,
  updateSignalStatus,
  type Signal,
  type SignalStatus,
} from '@/lib/api'
import { useToast } from '@/components/ToastProvider'
import SignalCard from '@/components/SignalCard'

type StatusFilter = SignalStatus | ''

const DEFAULT_STATUS: StatusFilter = 'new'
const PAGE_SIZE = 50

export default function AdjacentLeadsPage() {
  const [signals, setSignals]         = useState<Signal[]>([])
  const [count, setCount]             = useState(0)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState<string | null>(null)
  const [status, setStatus]           = useState<StatusFilter>(DEFAULT_STATUS)
  const [sinceDays, setSinceDays]     = useState(0)
  const [offset, setOffset]           = useState(0)
  const [hasMore, setHasMore]         = useState(false)

  const { addToast } = useToast()
  const abortRef = useRef<AbortController | null>(null)

  const loadSignals = useCallback(async (currentStatus: StatusFilter, currentOffset: number, append = false) => {
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    setLoading(true)
    setError(null)

    try {
      const res = await fetchSignals({
        adjacent: true,
        status: currentStatus || undefined,
        since_days: sinceDays || undefined,
        limit: PAGE_SIZE,
        offset: currentOffset,
        signal: abortRef.current.signal,
      })
      if (append) {
        setSignals((prev) => [...prev, ...res.data])
      } else {
        setSignals(res.data)
      }
      setCount(res.count)
      setHasMore(currentOffset + res.data.length < res.count)
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return
      setError(err instanceof Error ? err.message : 'Failed to load signals.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setOffset(0)
    loadSignals(status, 0, false)
  }, [status, sinceDays, loadSignals])

  function loadMore() {
    const newOffset = offset + PAGE_SIZE
    setOffset(newOffset)
    loadSignals(status, newOffset, true)
  }

  async function handleStatusChange(id: string, newStatus: SignalStatus) {
    try {
      const updated = await updateSignalStatus(id, newStatus)
      setSignals((prev) => prev.map((s) => (s.id === id ? { ...s, ...updated } : s)))
      addToast('Status updated.', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to update signal.', 'error')
      throw err  // re-throw so SignalCard can revert optimistic update
    }
  }

  const sorted = [...signals].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
  })

  return (
    <div>
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Adjacent Leads</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Orgs hiring for adjacent specialties (IR, MSK, imaging techs, oncology) — not primary targets today, but worth watching for pipeline expansion.
        </p>
      </div>

      {/* Filters + count */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="flex gap-1">
          {(['new', 'actioned', 'dismissed', ''] as StatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                status === s
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <select
          value={sinceDays}
          onChange={(e) => setSinceDays(Number(e.target.value))}
          className="input py-1 text-sm w-auto"
        >
          <option value={0}>Any time</option>
          <option value={1}>Today</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>

        {!loading && (
          <span className="text-sm text-gray-500 ml-auto">
            {count.toLocaleString()} signal{count !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Signal feed */}
      {error ? (
        <ErrorState message={error} onRetry={() => loadSignals(status, 0)} />
      ) : loading && signals.length === 0 ? (
        <LoadingSkeleton />
      ) : sorted.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {sorted.map((signal) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>

          {hasMore && (
            <div className="mt-6 flex justify-center">
              <button
                onClick={loadMore}
                disabled={loading}
                className="btn-secondary"
              >
                {loading ? 'Loading…' : `Load more (${count - signals.length} remaining)`}
              </button>
            </div>
          )}

          {!hasMore && signals.length > 0 && (
            <p className="text-center text-xs text-gray-400 mt-6">
              All {count.toLocaleString()} signals loaded
            </p>
          )}
        </>
      )}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="card score-border-gray p-4 animate-pulse">
          <div className="flex gap-2 mb-3">
            <div className="h-5 w-12 bg-gray-200 rounded-full" />
            <div className="h-5 w-24 bg-gray-200 rounded-full" />
          </div>
          <div className="h-4 w-32 bg-gray-200 rounded mb-2" />
          <div className="h-4 w-full bg-gray-200 rounded mb-1" />
          <div className="h-4 w-3/4 bg-gray-200 rounded" />
        </div>
      ))}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="card p-12 text-center">
      <div className="text-4xl mb-3">🔍</div>
      <h3 className="text-base font-semibold text-gray-700 mb-1">No adjacent signals found</h3>
      <p className="text-sm text-gray-500">
        Run bulk import with adjacent scoring to populate this feed.
      </p>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="card border-red-200 p-8 text-center">
      <div className="text-3xl mb-3">⚠️</div>
      <p className="text-sm text-red-700 mb-4">{message}</p>
      <button onClick={onRetry} className="btn-secondary">Retry</button>
    </div>
  )
}
