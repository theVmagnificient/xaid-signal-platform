import { formatDistanceToNow, parseISO } from 'date-fns'
import type { SignalType, SignalStatus } from './api'

// ─── Date helpers ─────────────────────────────────────────────────────────────

export function formatRelativeDate(dateStr: string): string {
  try {
    const date = parseISO(dateStr)
    return formatDistanceToNow(date, { addSuffix: true })
  } catch {
    return dateStr
  }
}

export function formatShortDate(dateStr: string): string {
  try {
    const date = parseISO(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

export function formatAbsoluteDate(dateStr: string): string {
  try {
    const date = parseISO(dateStr)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

// ─── Score helpers ────────────────────────────────────────────────────────────

export type ScoreLevel = 'critical' | 'high' | 'medium' | 'low'

export function getScoreLevel(score: number): ScoreLevel {
  if (score >= 9) return 'critical'
  if (score >= 7) return 'high'
  if (score >= 4) return 'medium'
  return 'low'
}

export const scoreBorderClass: Record<ScoreLevel, string> = {
  critical: 'score-border-red',
  high:     'score-border-orange',
  medium:   'score-border-yellow',
  low:      'score-border-gray',
}

export const scoreBadgeClass: Record<ScoreLevel, string> = {
  critical: 'bg-red-100 text-red-800',
  high:     'bg-orange-100 text-orange-800',
  medium:   'bg-yellow-100 text-yellow-700',
  low:      'bg-gray-100 text-gray-600',
}

export function getScoreBorder(score: number): string {
  return scoreBorderClass[getScoreLevel(score)]
}

export function getScoreBadge(score: number): string {
  return scoreBadgeClass[getScoreLevel(score)]
}

// ─── Signal type helpers ──────────────────────────────────────────────────────

export const signalTypeLabel: Record<SignalType, string> = {
  job_change:   'Job Change',
  job_posting:  'Job Posting',
  news:         'News',
}

export const signalTypeIcon: Record<SignalType, string> = {
  job_change:  '🔄',
  job_posting: '💼',
  news:        '📰',
}

export const signalTypeBadgeClass: Record<SignalType, string> = {
  job_change:  'bg-purple-100 text-purple-800',
  job_posting: 'bg-blue-100 text-blue-800',
  news:        'bg-teal-100 text-teal-800',
}

// ─── Status helpers ───────────────────────────────────────────────────────────

export const statusLabel: Record<SignalStatus, string> = {
  new:       'New',
  viewed:    'Viewed',
  actioned:  'Reached Out',
  dismissed: 'Dismissed',
}

export const statusBadgeClass: Record<SignalStatus, string> = {
  new:       'bg-blue-100 text-blue-800',
  viewed:    'bg-gray-100 text-gray-600',
  actioned:  'bg-green-100 text-green-800',
  dismissed: 'bg-red-100 text-red-600',
}

// ─── Stage helpers ────────────────────────────────────────────────────────────

export function getStageBadgeClass(stage: string): string {
  const s = stage?.toLowerCase() ?? ''
  if (s.includes('customer') || s.includes('closed')) return 'bg-green-100 text-green-800'
  if (s.includes('negotiat') || s.includes('proposal')) return 'bg-blue-100 text-blue-800'
  if (s.includes('demo') || s.includes('eval')) return 'bg-yellow-100 text-yellow-700'
  if (s.includes('prospect') || s.includes('lead')) return 'bg-gray-100 text-gray-700'
  return 'bg-gray-100 text-gray-600'
}

// ─── Misc ─────────────────────────────────────────────────────────────────────

export function clsx(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength).trimEnd() + '…'
}
