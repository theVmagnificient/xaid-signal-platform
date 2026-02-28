"""
Apollo.io job change tracker.

Strategy:
- Match contacts by email via Apollo /v1/people/match (much more accurate than by name)
- Store apollo_title + apollo_company in contacts table as snapshot
- On subsequent runs: if title or company changed → create job_change signal
- Prioritizes high-value contacts (CMO, COO, CFO, Radiologist, etc.)
- Processes up to --limit contacts per run (default 500) to stay within API quota

Usage:
    cd signal_platform
    python3 worker/apollo_tracker.py              # process 500 contacts, oldest-checked first
    python3 worker/apollo_tracker.py --limit 100  # process 100
    python3 worker/apollo_tracker.py --dry-run    # print what would be done, no API calls
"""

import os
import sys
import time
import json
import argparse
import httpx
from dotenv import load_dotenv
from supabase import create_client

# ── Add backend to path for scorer ────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
try:
    from app.services.scorer import score_job_change
except ImportError:
    # Fallback if backend not on path
    def score_job_change(title: str) -> tuple[int, str]:
        t = title.lower() if title else ""
        TIER1 = ["head of radiology", "chief of radiology", "radiology chair",
                 "chair of radiology", "chief medical officer", "cmo",
                 "chief technology officer", "cto", "chief operations officer", "coo",
                 "vp of radiology", "vp radiology", "director of radiology",
                 "medical director of radiology"]
        TIER2 = ["radiologist", "medical director", "director of imaging",
                 "imaging director", "pacs administrator", "it director", "cio"]
        for kw in TIER1:
            if kw in t:
                return 10, "tier1_clevel"
        for kw in TIER2:
            if kw in t:
                return 7, "tier2_radiology_lead"
        return 0, ""

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Contacts checked more than this many days ago will be re-checked
RECHECK_DAYS = 30

# Only contacts with these keywords in job_title are tracked — saves credits
RELEVANT_KEYWORDS = [
    "chief", "cmo", "coo", "cfo", "cto", "ceo",
    "director", "radiolog", "vp ", "vice president",
    "head of", "medical director", "pacs", "president",
]

# Within relevant contacts, these are processed first
PRIORITY_KEYWORDS = [
    "chief medical officer", "cmo", "chief operating officer", "coo",
    "chief financial officer", "cfo", "chief executive officer", "ceo",
    "radiology chair", "radiologist", "director of radiology",
    "head of radiology", "vp of radiology", "medical director",
    "director of imaging", "director of imaging services",
]


def check_columns(db) -> bool:
    """Return True if apollo tracking columns exist."""
    try:
        db.table("contacts").select("apollo_title").limit(1).execute()
        return True
    except Exception as e:
        if "apollo_title" in str(e):
            return False
        raise


def is_relevant(contact: dict) -> bool:
    """Return True if contact's job_title is worth tracking."""
    title = (contact.get("job_title") or "").lower()
    if not title:
        return False
    return any(kw in title for kw in RELEVANT_KEYWORDS)


def get_contacts_to_check(db, limit: int) -> list[dict]:
    """
    Fetch relevant contacts (C-level, directors, radiologists) with emails
    that need Apollo checking.
    Priority order:
      1. Never checked (apollo_checked_at IS NULL)
      2. Checked more than RECHECK_DAYS ago
    Within each group, prioritize high-value titles.
    Fetches in pages of 1000 to handle Supabase's row limit.
    """
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RECHECK_DAYS)).isoformat()

    def fetch_page(base_query, page_size=1000):
        """Paginate through all results, filtering for relevant contacts."""
        results = []
        offset = 0
        while True:
            rows = base_query.range(offset, offset + page_size - 1).execute().data or []
            for row in rows:
                if is_relevant(row):
                    results.append(row)
            if len(rows) < page_size:
                break
            offset += page_size
        return results

    base_unchecked = (
        db.table("contacts")
        .select("id,name,email,job_title,apollo_title,apollo_company,company_id")
        .not_.is_("email", "null")
        .is_("apollo_checked_at", "null")
    )
    base_stale = (
        db.table("contacts")
        .select("id,name,email,job_title,apollo_title,apollo_company,company_id")
        .not_.is_("email", "null")
        .lt("apollo_checked_at", cutoff)
    )

    contacts = fetch_page(base_unchecked)
    if len(contacts) < limit:
        contacts += fetch_page(base_stale)

    # Sort: highest-priority titles first
    def priority(c):
        title = (c.get("job_title") or "").lower()
        for kw in PRIORITY_KEYWORDS:
            if kw in title:
                return 0
        return 1

    contacts.sort(key=priority)
    return contacts[:limit]


def match_by_email(email: str, api_key: str) -> dict | None:
    """
    Call Apollo /v1/people/match by email.
    Returns the 'person' dict or None.
    """
    try:
        resp = httpx.post(
            "https://api.apollo.io/v1/people/match",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": api_key,
            },
            json={
                "email": email,
                "reveal_personal_emails": False,
                "reveal_phone_number": False,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("person")
        if resp.status_code == 429:
            print("  ⚠  Rate limited — sleeping 60s")
            time.sleep(60)
        elif resp.status_code == 401:
            print("  ✗  Apollo API key invalid (401)")
        else:
            print(f"  ✗  Apollo returned {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  ✗  Apollo request error: {e}")
    return None


def upsert_signal(db, contact: dict, new_title: str, new_company: str, old_title: str, old_company: str, score: int, subtype: str):
    """Insert a job_change signal for a detected title/company change."""
    from datetime import datetime, timezone
    company_id = contact.get("company_id")
    contact_id = contact["id"]
    name = contact.get("name", "")

    title_changed = old_title and new_title and new_title.lower() != old_title.lower()
    company_changed = old_company and new_company and new_company.lower() != old_company.lower()

    if title_changed and company_changed:
        signal_title = f"[Job Change] {name} moved to {new_title} at {new_company}"
        description = f"Previously: {old_title} at {old_company}. Now: {new_title} at {new_company}."
    elif company_changed:
        signal_title = f"[Job Change] {name} moved to {new_company}"
        description = f"Previously at {old_company}. Now at {new_company} ({new_title or 'unknown role'})."
    else:
        signal_title = f"[Job Change] {name} is now {new_title}"
        description = f"Previously: {old_title}. Now: {new_title} at {new_company or old_company}."

    signal = {
        "company_id": company_id,
        "contact_id": contact_id,
        "signal_type": "job_change",
        "signal_subtype": subtype,
        "title": signal_title,
        "description": description,
        "score": score,
        "source_url": None,
        "source_name": "Apollo.io",
        "raw_data": {
            "apollo_new_title": new_title,
            "apollo_new_company": new_company,
            "old_title": old_title,
            "old_company": old_company,
        },
        "status": "new",
    }
    db.table("signals").insert(signal).execute()


def run(limit: int = 500, dry_run: bool = False):
    if not APOLLO_API_KEY:
        print("✗ APOLLO_API_KEY is not set in backend/.env")
        print("  Add it and re-run: APOLLO_API_KEY=your_key_here")
        sys.exit(1)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("✗ SUPABASE_URL or SUPABASE_SERVICE_KEY missing")
        sys.exit(1)

    db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Check columns exist
    if not check_columns(db):
        print("✗ Apollo tracking columns missing from contacts table.")
        print("  Run this SQL in your Supabase dashboard → SQL Editor:")
        print()
        print("  ALTER TABLE contacts")
        print("    ADD COLUMN IF NOT EXISTS apollo_title TEXT,")
        print("    ADD COLUMN IF NOT EXISTS apollo_company TEXT,")
        print("    ADD COLUMN IF NOT EXISTS apollo_checked_at TIMESTAMPTZ;")
        print("  CREATE INDEX IF NOT EXISTS idx_contacts_apollo_checked ON contacts(apollo_checked_at);")
        print()
        sys.exit(1)

    contacts = get_contacts_to_check(db, limit)
    print(f"Apollo tracker — processing {len(contacts)} contacts (dry_run={dry_run})")
    print(f"API key: {APOLLO_API_KEY[:8]}...")
    print()

    stats = {"checked": 0, "matched": 0, "signals": 0, "errors": 0, "skipped_no_change": 0}

    from datetime import datetime, timezone

    for i, contact in enumerate(contacts):
        email = contact.get("email", "")
        name = contact.get("name", "")
        old_title = contact.get("apollo_title") or contact.get("job_title") or ""
        old_company = contact.get("apollo_company") or ""

        print(f"[{i+1}/{len(contacts)}] {name} <{email}>")

        if dry_run:
            print(f"  → dry-run, would call Apollo")
            stats["checked"] += 1
            continue

        person = match_by_email(email, APOLLO_API_KEY)
        stats["checked"] += 1

        if not person:
            # Update checked_at even on no match (to avoid re-checking too soon)
            db.table("contacts").update({
                "apollo_checked_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", contact["id"]).execute()
            print(f"  → not found in Apollo")
            time.sleep(1.0)
            continue

        stats["matched"] += 1
        new_title = person.get("title") or ""
        new_company = (person.get("organization") or {}).get("name") or ""
        linkedin = person.get("linkedin_url") or ""

        print(f"  → Apollo: {new_title} @ {new_company}")

        # Detect change
        title_changed = new_title and new_title.lower() != old_title.lower()
        company_changed = new_company and old_company and new_company.lower() != old_company.lower()

        changed = title_changed or company_changed
        is_first_check = not contact.get("apollo_title") and not old_company

        if changed and not is_first_check:
            score, subtype = score_job_change(new_title)
            if score == 0:
                # Still score by old title if new one is unknown
                score, subtype = score_job_change(old_title)
            if score == 0:
                score, subtype = 5, "job_change"  # minimal score for any detected change

            print(f"  ✓ CHANGE DETECTED! {old_title}@{old_company} → {new_title}@{new_company} (score={score})")
            upsert_signal(db, contact, new_title, new_company, old_title, old_company, score, subtype)
            stats["signals"] += 1
        elif is_first_check:
            print(f"  → first check, storing snapshot")
            stats["skipped_no_change"] += 1
        else:
            print(f"  → no change")
            stats["skipped_no_change"] += 1

        # Update contact snapshot
        update = {
            "apollo_title": new_title or None,
            "apollo_company": new_company or None,
            "apollo_checked_at": datetime.now(timezone.utc).isoformat(),
        }
        if linkedin and not contact.get("linkedin_url"):
            update["linkedin_url"] = linkedin

        db.table("contacts").update(update).eq("id", contact["id"]).execute()

        time.sleep(1.0)  # 1 req/sec — well within Apollo limits

    print()
    print("─" * 50)
    print(f"Done. checked={stats['checked']} matched={stats['matched']} "
          f"signals={stats['signals']} no_change={stats['skipped_no_change']} "
          f"errors={stats['errors']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apollo job change tracker")
    parser.add_argument("--limit", type=int, default=500, help="Max contacts to process (default 500)")
    parser.add_argument("--dry-run", action="store_true", help="No API calls, just print contacts")
    args = parser.parse_args()

    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    run(limit=args.limit, dry_run=args.dry_run)
