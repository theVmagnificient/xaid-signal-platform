'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { fetchCompany, updateSignalStatus, type CompanyDetail, type SignalStatus } from '@/lib/api'
import { useToast } from '@/components/ToastProvider'
import SignalCard from '@/components/SignalCard'
import { getStageBadgeClass } from '@/lib/utils'

type Tab = 'signals' | 'contacts'

interface PageProps {
  params: { id: string }
}

export default function CompanyDetailPage({ params }: PageProps) {
  const { id } = params

  const { addToast } = useToast()
  const [detail, setDetail]   = useState<CompanyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('signals')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchCompany(id)
      setDetail(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load company.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  async function handleStatusChange(signalId: string, status: SignalStatus) {
    try {
      const updated = await updateSignalStatus(signalId, status)
      setDetail((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          signals: prev.signals.map((s) => (s.id === signalId ? { ...s, ...updated } : s)),
        }
      })
      addToast('Status updated.', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to update signal.', 'error')
      throw err  // re-throw so SignalCard can revert optimistic update
    }
  }

  if (loading) return <DetailSkeleton />

  if (error) {
    return (
      <div className="card border-red-200 p-10 text-center">
        <p className="text-sm text-red-700 mb-4">{error}</p>
        <div className="flex gap-2 justify-center">
          <button onClick={load} className="btn-secondary">Retry</button>
          <Link href="/companies" className="btn-ghost">Back to Companies</Link>
        </div>
      </div>
    )
  }

  if (!detail) return null

  const { company, signals, contacts } = detail

  // Sort signals by score desc, date desc
  const sortedSignals = [...signals].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
  })

  const newSignalCount    = signals.filter((s) => s.status === 'new').length
  const stageBadgeClass   = getStageBadgeClass(company.stage ?? '')

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-500 mb-4">
        <Link href="/companies" className="hover:text-blue-600 transition-colors">Companies</Link>
        <ChevronIcon className="w-3.5 h-3.5 text-gray-400" />
        <span className="text-gray-800 font-medium">{company.name}</span>
      </nav>

      {/* Company header */}
      <div className="card px-5 py-4 mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{company.name}</h1>
            {company.stage && (
              <span className={`badge ${stageBadgeClass}`}>{company.stage}</span>
            )}
          </div>
          {company.description && (
            <p className="text-sm text-gray-500 max-w-xl leading-relaxed">{company.description}</p>
          )}
          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1 mt-1.5"
            >
              <ExternalLinkIcon className="w-3.5 h-3.5" />
              {company.website.replace(/^https?:\/\//, '')}
            </a>
          )}
        </div>

        {/* Quick stats */}
        <div className="flex gap-4">
          <MiniStat label="Total signals" value={signals.length} />
          <MiniStat label="New" value={newSignalCount} highlight={newSignalCount > 0} />
          <MiniStat label="Contacts" value={contacts.length} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        <TabButton
          active={activeTab === 'signals'}
          onClick={() => setActiveTab('signals')}
          count={signals.length}
        >
          Signals
        </TabButton>
        <TabButton
          active={activeTab === 'contacts'}
          onClick={() => setActiveTab('contacts')}
          count={contacts.length}
        >
          Contacts
        </TabButton>
      </div>

      {/* Tab content */}
      {activeTab === 'signals' ? (
        sortedSignals.length === 0 ? (
          <div className="card p-10 text-center">
            <div className="text-3xl mb-3">📭</div>
            <p className="text-sm text-gray-500">No signals collected yet for this company.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {sortedSignals.map((signal) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        )
      ) : (
        /* Contacts tab */
        contacts.length === 0 ? (
          <div className="card p-10 text-center">
            <div className="text-3xl mb-3">👤</div>
            <p className="text-sm text-gray-500">No contacts on file for this company.</p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Name</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Title</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Email</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">LinkedIn</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {contacts.map((contact) => (
                    <tr key={contact.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{contact.name}</td>
                      <td className="px-4 py-3 text-gray-600">{contact.job_title || '—'}</td>
                      <td className="px-4 py-3">
                        {contact.email ? (
                          <a
                            href={`mailto:${contact.email}`}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            {contact.email}
                          </a>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {contact.linkedin_url ? (
                          <a
                            href={contact.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-blue-600 hover:text-blue-800"
                          >
                            <LinkedInIcon className="w-3.5 h-3.5" />
                            Profile
                          </a>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function MiniStat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="text-center">
      <div className={`text-xl font-bold tabular-nums ${highlight ? 'text-blue-600' : 'text-gray-800'}`}>
        {value}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  count,
  children,
}: {
  active: boolean
  onClick: () => void
  count?: number
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
        active
          ? 'border-blue-600 text-blue-700'
          : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
      }`}
    >
      {children}
      {count != null && (
        <span className={`text-xs rounded-full px-1.5 py-0.5 font-semibold ${active ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>
          {count}
        </span>
      )}
    </button>
  )
}

function DetailSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-4 w-32 bg-gray-200 rounded mb-4" />
      <div className="card px-5 py-4 mb-5">
        <div className="h-7 w-48 bg-gray-200 rounded mb-2" />
        <div className="h-4 w-full max-w-md bg-gray-200 rounded mb-1" />
        <div className="h-4 w-64 bg-gray-200 rounded" />
      </div>
      <div className="flex gap-4 mb-4 border-b border-gray-200 pb-0">
        <div className="h-10 w-24 bg-gray-200 rounded" />
        <div className="h-10 w-24 bg-gray-200 rounded" />
      </div>
      <div className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card score-border-gray p-4">
            <div className="flex gap-2 mb-3">
              <div className="h-5 w-12 bg-gray-200 rounded-full" />
              <div className="h-5 w-24 bg-gray-200 rounded-full" />
            </div>
            <div className="h-4 w-full bg-gray-200 rounded mb-1" />
            <div className="h-4 w-3/4 bg-gray-200 rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}

function ExternalLinkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  )
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
      <rect x="2" y="9" width="4" height="12" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  )
}
