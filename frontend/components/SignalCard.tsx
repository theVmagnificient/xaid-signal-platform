'use client'

import { useState } from 'react'
import type { Signal, SignalStatus } from '@/lib/api'
import {
  formatRelativeDate,
  formatShortDate,
  getScoreBorder,
  getScoreBadge,
  signalTypeLabel,
  signalTypeIcon,
  signalTypeBadgeClass,
  statusLabel,
  statusBadgeClass,
} from '@/lib/utils'

interface SignalCardProps {
  signal: Signal
  onStatusChange?: (id: string, status: SignalStatus) => Promise<void>
}

export default function SignalCard({ signal, onStatusChange }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [updating, setUpdating] = useState<SignalStatus | null>(null)

  const borderClass = getScoreBorder(signal.score)
  const scoreBadge  = getScoreBadge(signal.score)
  const typeBadge   = signalTypeBadgeClass[signal.signal_type]

  const hasLongDescription = (signal.description?.length ?? 0) > 180

  async function handleStatusChange(status: SignalStatus) {
    if (!onStatusChange) return
    setUpdating(status)
    try {
      await onStatusChange(signal.id, status)
    } finally {
      setUpdating(null)
    }
  }

  return (
    <div className={`card ${borderClass} p-4 hover:shadow-md transition-shadow`}>
      {/* ── Header row ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start gap-2 mb-2">
        {/* Score badge */}
        <span className={`badge ${scoreBadge} font-bold text-xs tabular-nums`}>
          {signal.score}/10
        </span>

        {/* Signal type */}
        <span className={`badge ${typeBadge}`}>
          <span>{signalTypeIcon[signal.signal_type]}</span>
          {signalTypeLabel[signal.signal_type]}
          {signal.signal_subtype && (
            <span className="opacity-60 ml-0.5">· {signal.signal_subtype}</span>
          )}
        </span>

        {/* Non-new status badge */}
        {signal.status !== 'new' && (
          <span className={`badge ${statusBadgeClass[signal.status]} ml-auto`}>
            {statusLabel[signal.status]}
          </span>
        )}
      </div>

      {/* ── Company + Contact ──────────────────────────────────── */}
      <div className="flex flex-wrap gap-x-4 gap-y-0.5 mb-1.5">
        {signal.companies && (
          <span className="text-sm font-semibold text-gray-800">
            {signal.companies.name}
            {signal.companies.stage && (
              <span className="ml-1.5 text-xs font-normal text-gray-400">
                {signal.companies.stage}
              </span>
            )}
          </span>
        )}
        {signal.contacts && (
          <span className="text-sm text-gray-500">
            {signal.contacts.name}
            {signal.contacts.job_title && (
              <span className="text-gray-400"> · {signal.contacts.job_title}</span>
            )}
          </span>
        )}
      </div>

      {/* ── Title ─────────────────────────────────────────────── */}
      <p className="text-sm font-medium text-gray-900 leading-snug mb-1">
        {signal.title}
      </p>

      {/* ── Description ───────────────────────────────────────── */}
      {signal.description && (
        <div className="mb-2">
          <p className="text-sm text-gray-600 leading-relaxed">
            {expanded || !hasLongDescription
              ? signal.description
              : signal.description.slice(0, 180).trimEnd() + '…'}
          </p>
          {hasLongDescription && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-blue-600 hover:text-blue-800 mt-0.5 underline underline-offset-2"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      )}

      {/* ── Footer row ────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 mt-2 pt-2 border-t border-gray-100">
        {/* Source + date */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400">
          {signal.source_url ? (
            <a
              href={signal.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-blue-500 hover:text-blue-700 transition-colors"
              title={signal.source_name ?? signal.source_url}
            >
              <ExternalLinkIcon className="w-3 h-3" />
              {signal.source_name ?? 'Source'}
            </a>
          ) : signal.source_name ? (
            <span>{signal.source_name}</span>
          ) : null}

          <span
            title={formatRelativeDate(signal.detected_at)}
            className="flex items-center gap-1"
          >
            <ClockIcon className="w-3 h-3" />
            {formatShortDate(signal.detected_at)}
          </span>
        </div>

        {/* Action buttons */}
        {onStatusChange && (
          <div className="flex gap-1.5">
            {signal.status === 'new' || signal.status === 'viewed' ? (
              <>
                <button
                  disabled={updating !== null}
                  onClick={() => handleStatusChange('actioned')}
                  className="btn-success text-xs py-1"
                >
                  {updating === 'actioned' ? (
                    <SpinnerIcon className="w-3 h-3 animate-spin" />
                  ) : (
                    <CheckIcon className="w-3 h-3" />
                  )}
                  Mark Reached Out
                </button>
                <button
                  disabled={updating !== null}
                  onClick={() => handleStatusChange('dismissed')}
                  className="btn-danger text-xs py-1"
                >
                  {updating === 'dismissed' ? (
                    <SpinnerIcon className="w-3 h-3 animate-spin" />
                  ) : (
                    <XIcon className="w-3 h-3" />
                  )}
                  Dismiss
                </button>
              </>
            ) : signal.status === 'actioned' || signal.status === 'dismissed' ? (
              <button
                disabled={updating !== null}
                onClick={() => handleStatusChange('new')}
                className="btn-ghost text-xs py-1 text-gray-500"
              >
                Reopen
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function ExternalLinkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  )
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
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
