"""
PubMed scientific paper signal collector.
Searches NCBI E-utilities for recent AI/radiology papers from target companies.
Only queries academic/hospital institutions (not teleradiology companies).
Free API — no key needed for <3 req/sec.
"""

import httpx
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

INSTITUTION_KEYWORDS = [
    "hospital", "medical center", "health system", "university",
    "clinic", "institute", "foundation", "healthcare",
]

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Search within past 365 days
_MINDATE = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y/%m/%d")
_MAXDATE = datetime.now(timezone.utc).strftime("%Y/%m/%d")


async def _esearch(client: httpx.AsyncClient, affiliation: str) -> list[str]:
    """Return up to 3 PMIDs matching an affiliation + AI radiology query."""
    query = f'("{affiliation}"[Affiliation]) AND (artificial intelligence OR machine learning) AND (radiology OR CT scan OR computed tomography)'
    try:
        resp = await client.get(
            ESEARCH_URL,
            params={
                "db": "pubmed",
                "term": query,
                "retmax": 3,
                "retmode": "json",
                "mindate": _MINDATE,
                "maxdate": _MAXDATE,
                "datetype": "pdat",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


async def _efetch(client: httpx.AsyncClient, pmids: list[str]) -> list[dict]:
    """Fetch article details for a list of PMIDs. Returns list of article dicts."""
    if not pmids:
        return []
    try:
        resp = await client.get(
            EFETCH_URL,
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            },
            timeout=20,
        )
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.text)
        articles = []
        for article_el in root.findall(".//PubmedArticle"):
            pmid_el = article_el.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            title_el = article_el.find(".//ArticleTitle")
            title = "".join(title_el.itertext()) if title_el is not None else ""

            abstract_parts = article_el.findall(".//AbstractText")
            abstract = " ".join("".join(el.itertext()) for el in abstract_parts)

            journal_el = article_el.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else ""

            author_els = article_el.findall(".//Author")
            authors = []
            for a in author_els[:3]:
                ln = a.findtext("LastName", "")
                fn = a.findtext("ForeName", "")
                if ln:
                    authors.append(f"{ln} {fn}".strip())
            author_str = ", ".join(authors) + (" et al." if len(author_els) > 3 else "")

            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract[:500],
                "journal": journal,
                "authors": author_str,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        return articles
    except Exception:
        return []


async def collect_publication_signals(
    companies: list[dict],
    db_client,
    run_id: str,
) -> int:
    """
    For each academic/hospital company, search PubMed for recent AI/CT papers.
    Returns count of signals inserted.
    """
    signals_found = 0

    async with httpx.AsyncClient() as client:
        for company in companies:
            name = company["name"]
            company_id = company["id"]

            # Only search institutional names, skip teleradiology/staffing firms
            name_lower = name.lower()
            if not any(kw in name_lower for kw in INSTITUTION_KEYWORDS):
                continue

            pmids = await _esearch(client, name)
            if not pmids:
                await asyncio.sleep(0.4)
                continue

            articles = await _efetch(client, pmids)
            for art in articles:
                url = art["url"]

                existing = (
                    db_client.table("signals")
                    .select("id")
                    .eq("source_url", url)
                    .execute()
                )
                if existing.data:
                    continue

                description = f"{art['authors']}\n{art['journal']}\n\n{art['abstract']}".strip()

                signal = {
                    "company_id": company_id,
                    "signal_type": "news",
                    "signal_subtype": "research_publication",
                    "title": f"[PubMed] {art['title']}",
                    "description": description[:500],
                    "score": 6,
                    "source_url": url,
                    "source_name": "PubMed",
                    "raw_data": art,
                    "status": "new",
                }
                db_client.table("signals").insert(signal).execute()
                signals_found += 1

            # Stay under 3 req/sec free limit
            await asyncio.sleep(0.4)

    return signals_found
