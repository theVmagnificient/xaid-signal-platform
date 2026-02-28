-- Apollo job change tracking columns on contacts

ALTER TABLE contacts
  ADD COLUMN IF NOT EXISTS apollo_title       TEXT,
  ADD COLUMN IF NOT EXISTS apollo_company     TEXT,
  ADD COLUMN IF NOT EXISTS apollo_checked_at  TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_contacts_apollo_checked ON contacts(apollo_checked_at);
