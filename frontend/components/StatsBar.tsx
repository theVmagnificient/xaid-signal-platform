'use client'

import type { SignalStats } from '@/lib/api'

interface StatsBarProps {
  stats: SignalStats | null
  loading?: boolean
  onSyncClick: () => void
  syncing?: boolean
}

export default function StatsBar({ stats, loading, onSyncClick, syncing }: StatsBarProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between mb-6">
      {/* Stat tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatTile
          label="Total Companies"
          value={stats?.total_companies}
          loading={loading}
          icon={<BuildingIcon />}
          accent="blue"
        />
        <StatTile
          label="New Job Changes"
          value={stats?.new_by_type.job_change}
          loading={loading}
          icon={<span className="text-base">🔄</span>}
          accent="purple"
        />
        <StatTile
          label="New Job Postings"
          value={stats?.new_by_type.job_posting}
          loading={loading}
          icon={<span className="text-base">💼</span>}
          accent="blue"
        />
        <StatTile
          label="New News"
          value={stats?.new_by_type.news}
          loading={loading}
          icon={<span className="text-base">📰</span>}
          accent="teal"
        />
      </div>

      {/* Sync button */}
      <button
        onClick={onSyncClick}
        disabled={syncing}
        className="btn-primary shrink-0 h-9"
      >
        {syncing ? (
          <>
            <SpinnerIcon className="w-4 h-4 animate-spin" />
            Running…
          </>
        ) : (
          <>
            <RefreshIcon className="w-4 h-4" />
            Run Signals Now
          </>
        )}
      </button>
    </div>
  )
}

// ─── Stat tile ────────────────────────────────────────────────────────────────

type Accent = 'blue' | 'purple' | 'teal' | 'orange'

const accentBg: Record<Accent, string> = {
  blue:   'bg-blue-50',
  purple: 'bg-purple-50',
  teal:   'bg-teal-50',
  orange: 'bg-orange-50',
}

const accentText: Record<Accent, string> = {
  blue:   'text-blue-700',
  purple: 'text-purple-700',
  teal:   'text-teal-700',
  orange: 'text-orange-700',
}

function StatTile({
  label,
  value,
  loading,
  icon,
  accent = 'blue',
}: {
  label: string
  value: number | undefined
  loading?: boolean
  icon: React.ReactNode
  accent?: Accent
}) {
  return (
    <div className="card px-4 py-3 flex items-center gap-3">
      <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${accentBg[accent]}`}>
        {icon}
      </div>
      <div>
        <div className={`text-xl font-bold tabular-nums ${accentText[accent]}`}>
          {loading ? (
            <span className="inline-block w-8 h-5 bg-gray-200 animate-pulse rounded" />
          ) : (
            (value ?? 0).toLocaleString()
          )}
        </div>
        <div className="text-xs text-gray-500 leading-tight">{label}</div>
      </div>
    </div>
  )
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function BuildingIcon() {
  return (
    <svg className="w-4 h-4 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18" />
      <path d="M9 21V9" />
    </svg>
  )
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  )
}

function SpinnerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" strokeLinecap="round" />
    </svg>
  )
}
