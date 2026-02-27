'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchSignals,
  fetchSignalStats,
  triggerSync,
  updateSignalStatus,
  type Signal,
  type SignalStats,
  type SignalStatus,
} from '@/lib/api'
import StatsBar from '@/components/StatsBar'
import FilterBar, { type FilterState } from '@/components/FilterBar'
import SignalCard from '@/components/SignalCard'

const DEFAULT_FILTERS: FilterState = {
  signal_type: '',
  status: 'new',
  min_score: 1,
}

const PAGE_SIZE = 50

export default function DashboardPage() {
  const [stats, setStats]         = useState<SignalStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const [signals, setSignals]     = useState<Signal[]>([])
  const [count, setCount]         = useState(0)
  const [signalsLoading, setSignalsLoading] = useState(true)
  const [error, setError]         = useState<string | null>(null)

  const [filters, setFilters]     = useState<FilterState>(DEFAULT_FILTERS)
  const [offset, setOffset]       = useState(0)
  const [hasMore, setHasMore]     = useState(false)

  const [syncing, setSyncing]     = useState(false)
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Abort controller for in-flight signal fetches
  const abortRef = useRef<AbortController | null>(null)

  // ── Load stats ─────────────────────────────────────────────────────────────
  const loadStats = useCallback(async () => {
    try {
      setStatsLoading(true)
      const data = await fetchSignalStats()
      setStats(data)
    } catch {
      // stats failure is non-fatal
    } finally {
      setStatsLoading(false)
    }
  }, [])

  // ── Load signals ───────────────────────────────────────────────────────────
  const loadSignals = useCallback(async (currentFilters: FilterState, currentOffset: number, append = false) => {
    // Cancel prior request
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    setSignalsLoading(true)
    setError(null)

    try {
      const res = await fetchSignals({
        signal_type: currentFilters.signal_type || undefined,
        status: currentFilters.status || undefined,
        min_score: currentFilters.min_score > 1 ? currentFilters.min_score : undefined,
        limit: PAGE_SIZE,
        offset: currentOffset,
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
      setSignalsLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    loadStats()
  }, [loadStats])

  // Reload when filters change
  useEffect(() => {
    setOffset(0)
    loadSignals(filters, 0, false)
  }, [filters, loadSignals])

  // ── Pagination ─────────────────────────────────────────────────────────────
  function loadMore() {
    const newOffset = offset + PAGE_SIZE
    setOffset(newOffset)
    loadSignals(filters, newOffset, true)
  }

  // ── Signal status update ───────────────────────────────────────────────────
  async function handleStatusChange(id: string, status: SignalStatus) {
    const updated = await updateSignalStatus(id, status)
    setSignals((prev) => prev.map((s) => (s.id === id ? { ...s, ...updated } : s)))
    // Refresh stats silently
    loadStats()
  }

  // ── Sync trigger ───────────────────────────────────────────────────────────
  async function handleSync() {
    setSyncing(true)
    setSyncMessage(null)
    try {
      await triggerSync('full')
      setSyncMessage({ type: 'success', text: 'Signal collection started in the background. Refresh in a minute.' })
    } catch (err) {
      setSyncMessage({ type: 'error', text: err instanceof Error ? err.message : 'Sync failed.' })
    } finally {
      setSyncing(false)
    }
  }

  // ── Sort signals: score desc, then date desc ───────────────────────────────
  const sorted = [...signals].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
  })

  return (
    <div>
      {/* Page title */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Signal Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Buying signals from radiology AI prospects — know when to reach out.
        </p>
      </div>

      {/* Sync notification */}
      {syncMessage && (
        <div
          className={`mb-4 rounded-lg px-4 py-3 text-sm flex items-center justify-between gap-3 ${
            syncMessage.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          <span>{syncMessage.text}</span>
          <button onClick={() => setSyncMessage(null)} className="text-current opacity-60 hover:opacity-100">
            <XIcon className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Stats bar */}
      <StatsBar
        stats={stats}
        loading={statsLoading}
        onSyncClick={handleSync}
        syncing={syncing}
      />

      {/* Filter bar */}
      <FilterBar
        filters={filters}
        onChange={setFilters}
        totalCount={count}
        loading={signalsLoading}
      />

      {/* Signal feed */}
      {error ? (
        <ErrorState message={error} onRetry={() => loadSignals(filters, 0)} />
      ) : signalsLoading && signals.length === 0 ? (
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

          {/* Load more */}
          {hasMore && (
            <div className="mt-6 flex justify-center">
              <button
                onClick={loadMore}
                disabled={signalsLoading}
                className="btn-secondary"
              >
                {signalsLoading ? 'Loading…' : `Load more (${count - signals.length} remaining)`}
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

// ─── Sub-components ───────────────────────────────────────────────────────────

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
      <h3 className="text-base font-semibold text-gray-700 mb-1">No signals found</h3>
      <p className="text-sm text-gray-500">
        Try adjusting filters or run a new signal collection.
      </p>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="card border-red-200 p-8 text-center">
      <div className="text-3xl mb-3">⚠️</div>
      <p className="text-sm text-red-700 mb-4">{message}</p>
      <button onClick={onRetry} className="btn-secondary">
        Retry
      </button>
    </div>
  )
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}
