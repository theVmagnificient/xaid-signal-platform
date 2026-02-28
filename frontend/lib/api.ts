// ─── Types ───────────────────────────────────────────────────────────────────

export type SignalType = 'job_change' | 'job_posting' | 'news'
export type SignalStatus = 'new' | 'viewed' | 'actioned' | 'dismissed'

export interface Signal {
  id: string
  signal_type: SignalType
  signal_subtype: string | null
  title: string
  description: string | null
  score: number
  source_url: string | null
  source_name: string | null
  status: SignalStatus
  detected_at: string
  companies: { name: string; stage: string } | null
  contacts: { name: string; job_title: string } | null
}

export interface SignalsResponse {
  data: Signal[]
  count: number
}

export interface SignalStats {
  total_signals: number
  new_by_type: {
    job_change: number
    job_posting: number
    news: number
  }
  total_companies: number
}

export interface Company {
  id: string
  name: string
  stage: string
  website?: string | null
  description?: string | null
  signal_count?: number
}

export interface Contact {
  id: string
  name: string
  job_title: string
  email?: string | null
  linkedin_url?: string | null
}

export interface CompanyDetail {
  company: Company
  signals: Signal[]
  contacts: Contact[]
}

export interface CompaniesResponse {
  data: Company[]
  count: number
}

export interface SyncRun {
  id: string
  run_type: string
  status: string
  started_at: string
  finished_at: string | null
  signals_found: number | null
  error: string | null
}

export interface SignalsQueryParams {
  signal_type?: SignalType | ''
  status?: SignalStatus | ''
  min_score?: number
  limit?: number
  offset?: number
  adjacent?: boolean
  since_days?: number
}

// ─── API Client ──────────────────────────────────────────────────────────────

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })

  if (!res.ok) {
    let message = `API error ${res.status}`
    try {
      const body = await res.json()
      message = body?.detail ?? body?.message ?? message
    } catch {
      // ignore parse error
    }
    throw new Error(message)
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const q = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '' && value !== null) {
      q.set(key, String(value))
    }
  }
  const str = q.toString()
  return str ? `?${str}` : ''
}

// ─── Signals ─────────────────────────────────────────────────────────────────

export async function fetchSignals(params: SignalsQueryParams = {}): Promise<SignalsResponse> {
  const query = buildQuery({
    signal_type: params.signal_type,
    status: params.status,
    min_score: params.min_score,
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    adjacent: params.adjacent,
    since_days: params.since_days || undefined,
  })
  return request<SignalsResponse>(`/signals${query}`)
}

export async function fetchSignalStats(): Promise<SignalStats> {
  return request<SignalStats>('/signals/stats')
}

export async function updateSignalStatus(id: string, status: SignalStatus): Promise<Signal> {
  return request<Signal>(`/signals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

// ─── Companies ───────────────────────────────────────────────────────────────

export async function fetchCompanies(search?: string, limit = 50): Promise<CompaniesResponse> {
  const query = buildQuery({ search, limit })
  return request<CompaniesResponse>(`/companies${query}`)
}

export async function fetchCompany(id: string): Promise<CompanyDetail> {
  return request<CompanyDetail>(`/companies/${id}`)
}

// ─── Sync ─────────────────────────────────────────────────────────────────────

export async function triggerSync(runType: 'full' | 'partial' = 'full'): Promise<{ run_id: string; status: string }> {
  return request<{ run_id: string; status: string }>(`/sync/run?run_type=${runType}`, {
    method: 'POST',
  })
}

export async function fetchSyncRuns(): Promise<SyncRun[]> {
  return request<SyncRun[]>('/sync/runs')
}
