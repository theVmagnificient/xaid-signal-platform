-- xAID Signal Platform — Initial Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Companies (from Pipedrive Prereads US pipeline)
CREATE TABLE companies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pipedrive_id    INTEGER UNIQUE,
  name            TEXT NOT NULL,
  website         TEXT,
  domain          TEXT,
  linkedin_url    TEXT,
  stage           TEXT,
  deal_status     TEXT,
  deal_id         INTEGER,
  radiologist_count INTEGER,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_pipedrive ON companies(pipedrive_id);
CREATE INDEX idx_companies_domain ON companies(domain);

-- Contacts (people associated with companies)
CREATE TABLE contacts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pipedrive_id    INTEGER UNIQUE,
  company_id      UUID REFERENCES companies(id) ON DELETE SET NULL,
  name            TEXT NOT NULL,
  first_name      TEXT,
  last_name       TEXT,
  email           TEXT,
  job_title       TEXT,
  linkedin_url    TEXT,
  phone           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_company ON contacts(company_id);
CREATE INDEX idx_contacts_pipedrive ON contacts(pipedrive_id);

-- Signals — the core of the platform
CREATE TABLE signals (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
  contact_id      UUID REFERENCES contacts(id) ON DELETE SET NULL,
  signal_type     TEXT NOT NULL CHECK (signal_type IN ('job_change', 'job_posting', 'news')),
  signal_subtype  TEXT,    -- e.g. 'tier1_clevel', 'ct_radiologist', 'ai_adoption'
  title           TEXT NOT NULL,
  description     TEXT,
  score           INTEGER DEFAULT 5 CHECK (score BETWEEN 1 AND 10),
  source_url      TEXT,
  source_name     TEXT,
  raw_data        JSONB,
  status          TEXT DEFAULT 'new' CHECK (status IN ('new', 'viewed', 'actioned', 'dismissed')),
  detected_at     TIMESTAMPTZ DEFAULT NOW(),
  actioned_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_company ON signals(company_id);
CREATE INDEX idx_signals_type ON signals(signal_type);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_score ON signals(score DESC);
CREATE INDEX idx_signals_detected ON signals(detected_at DESC);

-- Signal collection run logs
CREATE TABLE signal_runs (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_type          TEXT NOT NULL,  -- 'job_postings' | 'news' | 'job_changes' | 'full'
  started_at        TIMESTAMPTZ DEFAULT NOW(),
  completed_at      TIMESTAMPTZ,
  companies_checked INTEGER DEFAULT 0,
  signals_found     INTEGER DEFAULT 0,
  errors            JSONB DEFAULT '[]'
);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated BEFORE UPDATE ON companies
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_contacts_updated BEFORE UPDATE ON contacts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
