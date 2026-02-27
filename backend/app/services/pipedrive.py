"""
Pipedrive integration.
Syncs companies and contacts from Pipedrive (Prereads US pipeline)
into our Supabase database.
"""

import httpx
from app.config import get_settings

PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"


async def get_pipeline_id(token: str, pipeline_name: str) -> int | None:
    """Find pipeline ID by name."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PIPEDRIVE_BASE}/pipelines",
            params={"api_token": token},
        )
        for p in resp.json().get("data", []) or []:
            if p.get("name") == pipeline_name:
                return p["id"]
    return None


async def fetch_deals(token: str, pipeline_id: int) -> list[dict]:
    """Fetch all deals from a pipeline (paginated)."""
    deals = []
    start = 0
    limit = 500
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            resp = await client.get(
                f"{PIPEDRIVE_BASE}/deals",
                params={
                    "api_token": token,
                    "pipeline_id": pipeline_id,
                    "limit": limit,
                    "start": start,
                    "status": "open",
                },
            )
            data = resp.json()
            batch = data.get("data") or []
            deals.extend(batch)
            if not data.get("additional_data", {}).get("pagination", {}).get("more_items_in_collection"):
                break
            start += limit
    return deals


async def fetch_person(token: str, person_id: int) -> dict | None:
    """Fetch a person by ID from Pipedrive."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{PIPEDRIVE_BASE}/persons/{person_id}",
            params={"api_token": token},
        )
        return resp.json().get("data")


def extract_domain(website: str | None) -> str | None:
    if not website:
        return None
    website = website.replace("https://", "").replace("http://", "").replace("www.", "")
    return website.split("/")[0].strip() or None


def upsert_companies_from_xlsx(deals_rows: list[dict], db_client) -> dict[int, str]:
    """
    Upsert companies from xlsx export rows.
    Returns mapping: pipedrive_org_id → supabase company UUID.
    """
    id_map: dict[int, str] = {}
    seen_org_ids: set[int] = set()

    for row in deals_rows:
        org_id = row.get("Deal - Organization ID")
        org_name = row.get("Deal - Organization")
        if not org_id or not org_name or org_id in seen_org_ids:
            continue
        seen_org_ids.add(org_id)

        company_data = {
            "pipedrive_id": int(org_id),
            "name": str(org_name),
            "stage": str(row.get("Deal - Stage", "")),
            "deal_status": str(row.get("Deal - Status", "")),
            "deal_id": int(row.get("Deal - ID")) if row.get("Deal - ID") else None,
            "radiologist_count": int(row.get("Deal - Number of Radiologists")) if row.get("Deal - Number of Radiologists") else None,
        }

        result = (
            db_client.table("companies")
            .upsert(company_data, on_conflict="pipedrive_id")
            .execute()
        )
        if result.data:
            id_map[int(org_id)] = result.data[0]["id"]

    return id_map


def upsert_contacts_from_xlsx(people_rows: list[dict], company_id_map: dict[int, str], db_client) -> int:
    """
    Upsert contacts from xlsx export rows.
    Returns count of upserted contacts.
    """
    count = 0
    for row in people_rows:
        person_id = row.get("Person - ID")
        if not person_id:
            continue

        org_id = row.get("Person - Organization ID")
        company_uuid = company_id_map.get(int(org_id)) if org_id else None

        linkedin = row.get("Person - LinkedIn")

        contact_data = {
            "pipedrive_id": int(person_id),
            "company_id": company_uuid,
            "name": str(row.get("Person - Name", "")),
            "first_name": str(row.get("Person - First name", "")) or None,
            "last_name": str(row.get("Person - Last name", "")) or None,
            "email": str(row.get("Person - Email - Work", "")) or None,
            "job_title": str(row.get("Person - Job title", "")) or None,
            "linkedin_url": str(linkedin) if linkedin else None,
            "phone": str(row.get("Person - Phone - Work", "")) or None,
        }

        db_client.table("contacts").upsert(contact_data, on_conflict="pipedrive_id").execute()
        count += 1

    return count
