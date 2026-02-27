"""
Job postings signal collector.
Primary: TheirStack API (315K+ sources: LinkedIn, Indeed, Glassdoor, ATS).
Fallback: Direct company career page scraping.
Detects: New radiologist openings → company is expanding → reach out.
"""

import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from app.services.scorer import score_job_posting
from app.config import get_settings

THEIRSTACK_API = "https://api.theirstack.com/v1/jobs/search"

# Radiology-related search queries
RADIOLOGY_QUERIES = [
    "radiologist",
    "body radiologist",
    "diagnostic radiologist",
    "neuroradiologist",
    "chest radiologist",
]


async def fetch_theirstack_jobs(
    company_name: str,
    api_key: str,
    days_back: int = 30,
) -> list[dict]:
    """Query TheirStack for new job postings at a specific company."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                THEIRSTACK_API,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "company_name_or": [company_name],
                    "job_title_or": RADIOLOGY_QUERIES,
                    "posted_at_gte": cutoff,
                    "limit": 20,
                    "order_by": [{"field": "date_posted", "desc": True}],
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("data", [])
    except Exception:
        return []


async def fetch_theirstack_by_keyword(
    api_key: str,
    days_back: int = 7,
    company_domains: list[str] | None = None,
) -> list[dict]:
    """
    Bulk fetch: search all radiology job postings from known company domains.
    More efficient than querying company by company.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    payload: dict = {
        "job_title_or": RADIOLOGY_QUERIES,
        "posted_at_gte": cutoff,
        "limit": 100,
        "order_by": [{"field": "date_posted", "desc": True}],
    }
    if company_domains:
        payload["company_website_domain_or"] = company_domains

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                THEIRSTACK_API,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code != 200:
                return []
            return resp.json().get("data", [])
    except Exception:
        return []


def _map_theirstack_to_signal(job: dict, company_id: str) -> dict | None:
    """Convert a TheirStack job posting to our signal format."""
    title = job.get("job_title", "")
    description = job.get("short_description", "") or job.get("description", "")

    score, subtype = score_job_posting(title, description)
    if score == 0:
        return None

    location = job.get("location", "")
    company_name = job.get("company_name", "")
    posted_at = job.get("date_posted", "")

    return {
        "company_id": company_id,
        "signal_type": "job_posting",
        "signal_subtype": subtype,
        "title": f"[Hiring] {title} @ {company_name}",
        "description": f"New opening: **{title}**\nLocation: {location}\nPosted: {posted_at}\n\n{description[:400]}",
        "score": score,
        "source_url": job.get("url", ""),
        "source_name": "TheirStack / LinkedIn Jobs",
        "raw_data": job,
        "status": "new",
    }


async def collect_job_posting_signals(
    companies: list[dict],
    db_client,
    run_id: str,
) -> int:
    """
    Collect job posting signals for all companies.
    Uses bulk domain query when possible.
    """
    settings = get_settings()
    signals_found = 0

    if not settings.theirstack_api_key:
        # No API key — skip (signals will just not appear)
        return 0

    # Build domain list for bulk query
    domains = [c["domain"] for c in companies if c.get("domain")]
    company_by_domain: dict[str, dict] = {c["domain"]: c for c in companies if c.get("domain")}
    company_by_name: dict[str, dict] = {c["name"].lower(): c for c in companies}

    # Bulk fetch for all domains at once
    jobs = await fetch_theirstack_by_keyword(settings.theirstack_api_key, days_back=7, company_domains=domains)

    for job in jobs:
        # Match job back to our company
        job_domain = job.get("company_website", "").replace("https://", "").replace("http://", "").split("/")[0]
        company = company_by_domain.get(job_domain) or company_by_name.get(
            job.get("company_name", "").lower()
        )
        if not company:
            continue

        source_url = job.get("url", "")

        # Deduplicate
        existing = (
            db_client.table("signals")
            .select("id")
            .eq("source_url", source_url)
            .eq("company_id", company["id"])
            .execute()
        )
        if existing.data:
            continue

        signal = _map_theirstack_to_signal(job, company["id"])
        if signal:
            db_client.table("signals").insert(signal).execute()
            signals_found += 1

    return signals_found
