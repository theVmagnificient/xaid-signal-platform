"""
Job change signal collector.
Detects when a key person (C-level, Head of Radiology, etc.) joins a new company
from our lead list — that's a warm outreach trigger.

Strategy:
- For contacts with LinkedIn URLs: use Exa.ai to search for recent mentions of
  "[Person Name] joins [Company]" or role changes.
- For contacts with Apollo API key: use People Enrichment to check current title/company.
"""

import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from app.services.scorer import score_job_change
from app.config import get_settings


async def check_exa_job_change(person_name: str, company_name: str, api_key: str) -> list[dict]:
    """
    Use Exa semantic search to find news about a person changing jobs.
    """
    queries = [
        f"{person_name} joins {company_name}",
        f"{person_name} appointed {company_name} radiology",
        f"{person_name} new role radiology",
    ]
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        for query in queries[:1]:  # Limit to 1 query per person to conserve credits
            try:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": api_key, "Content-Type": "application/json"},
                    json={
                        "query": query,
                        "numResults": 3,
                        "type": "neural",
                        "useAutoprompt": True,
                        "startPublishedDate": (
                            datetime.now(timezone.utc) - timedelta(days=90)
                        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                )
                if resp.status_code == 200:
                    for r in resp.json().get("results", []):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "summary": r.get("text", "")[:300],
                            "published": r.get("publishedDate", ""),
                        })
            except Exception:
                pass
    return results


async def check_apollo_person(person_name: str, company_name: str, api_key: str) -> dict | None:
    """
    Use Apollo.io People Search to get current job title & company.
    Compare with what we have stored to detect a job change.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/people/match",
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                json={
                    "api_key": api_key,
                    "name": person_name,
                    "organization_name": company_name,
                },
            )
            if resp.status_code == 200:
                return resp.json().get("person")
    except Exception:
        pass
    return None


async def collect_job_change_signals(
    contacts: list[dict],
    companies_by_id: dict[str, dict],
    db_client,
    run_id: str,
) -> int:
    """
    Check contacts for job changes.
    contacts: list of {id, name, job_title, company_id, linkedin_url, ...}
    """
    settings = get_settings()
    signals_found = 0

    # Only process contacts that have a job title we care about
    relevant_contacts = []
    for contact in contacts:
        title = contact.get("job_title", "") or ""
        score, subtype = score_job_change(title)
        if score >= 7:  # Tier 1 and Tier 2 only
            relevant_contacts.append((contact, score, subtype))

    for contact, stored_score, stored_subtype in relevant_contacts:
        contact_id = contact["id"]
        contact_name = contact.get("name", "")
        company_id = contact.get("company_id")
        company = companies_by_id.get(company_id, {})
        company_name = company.get("name", "")

        if not company_name:
            continue

        results = []

        # Try Exa.ai if available
        if settings.exa_api_key:
            results = await check_exa_job_change(contact_name, company_name, settings.exa_api_key)

        # Try Apollo if available and Exa found nothing
        if not results and settings.apollo_api_key:
            person_data = await check_apollo_person(contact_name, company_name, settings.apollo_api_key)
            if person_data:
                current_company = (person_data.get("organization", {}) or {}).get("name", "")
                if current_company and current_company.lower() != company_name.lower():
                    results.append({
                        "title": f"{contact_name} now at {current_company}",
                        "url": "",
                        "summary": f"Previously at {company_name}. Now: {person_data.get('title', '')} at {current_company}.",
                        "published": datetime.now(timezone.utc).isoformat(),
                    })

        for item in results:
            # Basic relevance check
            if not any(kw in item["title"].lower() for kw in ["join", "appoint", "hire", "new", "radiol"]):
                continue

            source_url = item.get("url", "")
            # Deduplicate
            if source_url:
                existing = (
                    db_client.table("signals")
                    .select("id")
                    .eq("source_url", source_url)
                    .execute()
                )
                if existing.data:
                    continue

            signal = {
                "company_id": company_id,
                "contact_id": contact_id,
                "signal_type": "job_change",
                "signal_subtype": stored_subtype,
                "title": f"[Job Change] {item['title']}",
                "description": item.get("summary", "")[:500],
                "score": stored_score,
                "source_url": source_url,
                "source_name": "Exa.ai / Apollo",
                "raw_data": item,
                "status": "new",
            }
            db_client.table("signals").insert(signal).execute()
            signals_found += 1

        await asyncio.sleep(0.2)

    return signals_found
