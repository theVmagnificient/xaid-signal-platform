'use client'

import type { SignalType, SignalStatus } from '@/lib/api'

export interface FilterState {
  signal_type: SignalType | ''
  status: SignalStatus | ''
  min_score: number
  since_days: number
}

interface FilterBarProps {
  filters: FilterState
  onChange: (filters: FilterState) => void
  totalCount: number
  loading?: boolean
}

const TYPE_TABS: { value: SignalType | ''; label: string; icon: string }[] = [
  { value: '',            label: 'All',          icon: '⚡' },
  { value: 'job_change',  label: 'Job Changes',  icon: '🔄' },
  { value: 'job_posting', label: 'Job Postings', icon: '💼' },
  { value: 'news',        label: 'News',         icon: '📰' },
]

const STATUS_OPTIONS: { value: SignalStatus | ''; label: string }[] = [
  { value: '',          label: 'All statuses' },
  { value: 'new',       label: 'New' },
  { value: 'viewed',    label: 'Viewed' },
  { value: 'actioned',  label: 'Reached Out' },
  { value: 'dismissed', label: 'Dismissed' },
]

const SINCE_OPTIONS: { value: number; label: string }[] = [
  { value: 0,  label: 'Any time' },
  { value: 1,  label: 'Today' },
  { value: 7,  label: 'Last 7 days' },
  { value: 30, label: 'Last 30 days' },
  { value: 90, label: 'Last 90 days' },
]

export default function FilterBar({ filters, onChange, totalCount, loading }: FilterBarProps) {
  function set<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="card px-4 py-3 mb-4 flex flex-col gap-3">
      {/* Row 1: type tabs + result count */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Signal type tabs */}
        <div className="flex gap-1 flex-wrap">
          {TYPE_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => set('signal_type', tab.value)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
                filters.signal_type === tab.value
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Result count */}
        <span className="text-sm text-gray-500">
          {loading ? (
            <span className="inline-block w-20 h-4 bg-gray-200 animate-pulse rounded" />
          ) : (
            <>{totalCount.toLocaleString()} signal{totalCount !== 1 ? 's' : ''}</>
          )}
        </span>
      </div>

      {/* Row 2: status filter + score slider */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Status filter */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-gray-500 whitespace-nowrap">Status</label>
          <select
            value={filters.status}
            onChange={(e) => set('status', e.target.value as SignalStatus | '')}
            className="input py-1 text-sm w-auto"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date filter */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-gray-500 whitespace-nowrap">Since</label>
          <select
            value={filters.since_days}
            onChange={(e) => set('since_days', Number(e.target.value))}
            className="input py-1 text-sm w-auto"
          >
            {SINCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Score slider */}
        <div className="flex items-center gap-2 flex-1 min-w-[180px] max-w-xs">
          <label className="text-xs font-medium text-gray-500 whitespace-nowrap">
            Min score
          </label>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={filters.min_score}
            onChange={(e) => set('min_score', Number(e.target.value))}
            className="flex-1 accent-blue-600 cursor-pointer"
          />
          <span className="text-sm font-semibold text-gray-700 tabular-nums w-4 text-right">
            {filters.min_score}
          </span>
        </div>

        {/* Reset */}
        {(filters.signal_type !== '' || filters.status !== '' || filters.min_score > 1 || filters.since_days > 0) && (
          <button
            onClick={() => onChange({ signal_type: '', status: 'new', min_score: 1, since_days: 0 })}
            className="text-xs text-blue-600 hover:text-blue-800 underline underline-offset-2"
          >
            Reset filters
          </button>
        )}
      </div>
    </div>
  )
}
