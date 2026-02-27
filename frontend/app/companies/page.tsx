'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { fetchCompanies, type Company } from '@/lib/api'
import { getStageBadgeClass } from '@/lib/utils'

export default function CompaniesPage() {
  const [companies, setCompanies]   = useState<Company[]>([])
  const [count, setCount]           = useState(0)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [search, setSearch]         = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  const load = useCallback(async (q: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchCompanies(q || undefined, 100)
      // API may return CompaniesResponse or plain array — handle both
      if (Array.isArray(res)) {
        setCompanies(res as Company[])
        setCount((res as Company[]).length)
      } else {
        setCompanies(res.data)
        setCount(res.count)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load companies.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(debouncedSearch)
  }, [debouncedSearch, load])

  return (
    <div>
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          All radiology companies being tracked for signals.
        </p>
      </div>

      {/* Search */}
      <div className="mb-4 flex items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search companies…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-8"
          />
        </div>
        {!loading && (
          <span className="text-sm text-gray-500">
            {count.toLocaleString()} compan{count !== 1 ? 'ies' : 'y'}
          </span>
        )}
      </div>

      {/* Table */}
      {error ? (
        <div className="card border-red-200 p-8 text-center">
          <p className="text-sm text-red-700 mb-3">{error}</p>
          <button onClick={() => load(debouncedSearch)} className="btn-secondary">Retry</button>
        </div>
      ) : loading ? (
        <TableSkeleton />
      ) : companies.length === 0 ? (
        <div className="card p-10 text-center">
          <div className="text-3xl mb-3">🏢</div>
          <p className="text-sm text-gray-500">
            {search ? `No companies matching "${search}"` : 'No companies found.'}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Company</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Stage</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600">Signals</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {companies.map((company) => (
                  <CompanyRow key={company.id} company={company} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Table row ────────────────────────────────────────────────────────────────

function CompanyRow({ company }: { company: Company }) {
  const stageBadge = getStageBadgeClass(company.stage ?? '')

  return (
    <tr className="hover:bg-gray-50 transition-colors group cursor-pointer">
      <td className="px-4 py-3">
        <Link href={`/companies/${company.id}`} className="block">
          <span className="font-medium text-gray-900 group-hover:text-blue-700 transition-colors">
            {company.name}
          </span>
          {company.website && (
            <span className="block text-xs text-gray-400 truncate max-w-[220px]">
              {company.website.replace(/^https?:\/\//, '')}
            </span>
          )}
        </Link>
      </td>
      <td className="px-4 py-3">
        <Link href={`/companies/${company.id}`} className="block">
          {company.stage ? (
            <span className={`badge ${stageBadge}`}>{company.stage}</span>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </Link>
      </td>
      <td className="px-4 py-3 text-right">
        <Link href={`/companies/${company.id}`} className="block">
          {company.signal_count != null ? (
            <span className="font-semibold text-gray-700 tabular-nums">
              {company.signal_count}
            </span>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </Link>
      </td>
      <td className="px-4 py-3 text-right">
        <Link
          href={`/companies/${company.id}`}
          className="text-blue-600 hover:text-blue-800 opacity-0 group-hover:opacity-100 transition-opacity text-xs font-medium"
        >
          View →
        </Link>
      </td>
    </tr>
  )
}

// ─── Skeletons ────────────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Company</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Stage</th>
            <th className="text-right px-4 py-3 font-semibold text-gray-600">Signals</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {Array.from({ length: 8 }).map((_, i) => (
            <tr key={i} className="animate-pulse">
              <td className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-40" /></td>
              <td className="px-4 py-3"><div className="h-5 bg-gray-200 rounded-full w-20" /></td>
              <td className="px-4 py-3 text-right"><div className="h-4 bg-gray-200 rounded w-8 ml-auto" /></td>
              <td className="px-4 py-3" />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  )
}
