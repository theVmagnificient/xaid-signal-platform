"""
News signal collector.
Uses Google News RSS (free) + optional Exa.ai semantic search.
Detects: AI adoption, PACS upgrades, tech announcements.
"""

import feedparser
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional
from app.services.scorer import score_news
from app.config import get_settings

# Google News RSS base URL
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def _parse_date(entry) -> str:
    try:
        return entry.published
    except AttributeError:
        return datetime.now(timezone.utc).isoformat()


async def fetch_google_news(company_name: str, extra_query: str = "radiology AI") -> list[dict]:
    """Fetch Google News RSS for a company. Returns list of news items."""
    query = f'"{company_name}" {extra_query}'
    url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+").replace('"', '%22'))

    try:
        # feedparser works sync; run in thread
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, url)
        items = []
        for entry in feed.entries[:10]:
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "url": entry.get("link", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
                "published": _parse_date(entry),
            })
        return items
    except Exception:
        return []


async def fetch_exa_news(company_name: str, api_key: str) -> list[dict]:
    """Use Exa.ai for semantic news search. Optional — requires API key."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "query": f"{company_name} radiology AI adoption PACS technology",
                    "numResults": 5,
                    "type": "neural",
                    "useAutoprompt": True,
                    "startPublishedDate": "2024-01-01",
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = []
            for r in data.get("results", []):
                items.append({
                    "title": r.get("title", ""),
                    "summary": r.get("text", "")[:300],
                    "url": r.get("url", ""),
                    "source": "Exa.ai",
                    "published": r.get("publishedDate", ""),
                })
            return items
    except Exception:
        return []


async def collect_news_signals(
    companies: list[dict],
    db_client,
    run_id: str,
) -> int:
    """
    For each company, fetch news and store qualifying signals.
    Returns count of signals found.
    """
    settings = get_settings()
    signals_found = 0

    for company in companies:
        company_name = company["name"]
        company_id = company["id"]

        # Fetch from Google News (free)
        news_items = await fetch_google_news(company_name)

        # Optionally augment with Exa.ai
        if settings.exa_api_key:
            exa_items = await fetch_exa_news(company_name, settings.exa_api_key)
            news_items.extend(exa_items)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        for item in news_items:
            url = item.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            score, subtype = score_news(item["title"], item.get("summary", ""))
            if score == 0:
                continue

            # Check if we already have this signal (by URL)
            existing = (
                db_client.table("signals")
                .select("id")
                .eq("source_url", url)
                .eq("company_id", company_id)
                .execute()
            )
            if existing.data:
                continue

            signal = {
                "company_id": company_id,
                "signal_type": "news",
                "signal_subtype": subtype,
                "title": f"[News] {item['title']}",
                "description": item.get("summary", "")[:500],
                "score": score,
                "source_url": url,
                "source_name": item.get("source", ""),
                "raw_data": item,
                "status": "new",
            }
            db_client.table("signals").insert(signal).execute()
            signals_found += 1

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.3)

    return signals_found
