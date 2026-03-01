"""
News signal collector.
Uses Google News RSS (free) + optional Brave Search News API.
Detects: AI adoption, PACS upgrades, tech announcements.
"""

import feedparser
import httpx
import asyncio
import re
import html as html_lib
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.services.scorer import score_news
from app.config import get_settings

NEWS_MAX_AGE_DAYS = 30


def _is_recent(entry, max_days: int = NEWS_MAX_AGE_DAYS) -> bool:
    """Return True if the feedparser entry was published within max_days. Allows through if date is missing."""
    parsed = getattr(entry, "published_parsed", None)
    if not parsed:
        return True
    try:
        pub_dt = datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return True
    return pub_dt >= datetime.now(timezone.utc) - timedelta(days=max_days)


def _parse_any_date(value: str) -> Optional[datetime]:
    """Try to parse a date string in ISO 8601 or RFC 2822 format. Returns None if unparseable."""
    if not value:
        return None
    # ISO 8601
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass
    # RFC 2822 (e.g. "Mon, 03 Feb 2025 08:00:00 GMT")
    try:
        import email.utils
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        pass
    return None


def _brave_is_recent(result: dict, max_days: int = NEWS_MAX_AGE_DAYS) -> bool:
    """Return True if the Brave Search result was published within max_days.
    Checks page_age (ISO) and age (ISO or RFC 2822) fields. Falls back to True if unparseable."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
    for field in ("page_age", "age"):
        pub_dt = _parse_any_date(result.get(field, ""))
        if pub_dt is not None:
            return pub_dt >= cutoff
        # Heuristic: Brave sometimes returns relative strings like "1 year ago"
        val = result.get(field, "").lower()
        if val and "year" in val:
            return False
    return True


def _strip_html(text: str) -> str:
    """Strip HTML tags and decode entities from a string."""
    if not text:
        return text
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities (&amp; &nbsp; &lt; etc.)
    text = html_lib.unescape(text)
    # Normalize whitespace
    return ' '.join(text.split()).strip()

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
        # feedparser works sync; run in thread with 10s timeout
        loop = asyncio.get_event_loop()
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url),
            timeout=5.0,
        )
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
    except (Exception, asyncio.TimeoutError):
        return []


async def fetch_brave_news(company_name: str, api_key: str) -> list[dict]:
    """Brave Search News API — keyword search, plain-text descriptions, no HTML."""
    try:
        query = f'"{company_name}" radiology implements OR adopts OR deploys AI OR backlog OR shortage OR "new imaging"'
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/news/search",
                headers={
                    "X-Subscription-Token": api_key,
                    "Accept": "application/json",
                },
                params={
                    "q": query,
                    "count": 5,
                    "freshness": "pm",  # past month
                    "country": "us",
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = []
            for r in data.get("results", []):
                if not _brave_is_recent(r):
                    continue
                source = r.get("meta_url", {}).get("hostname", "") or r.get("source", "Brave News")
                items.append({
                    "title": r.get("title", ""),
                    "summary": r.get("description", ""),
                    "url": r.get("url", ""),
                    "source": source,
                    "published": r.get("age", ""),
                })
            return items
    except Exception:
        return []


TRADE_RSS_FEEDS = [
    "https://www.auntminnie.com/rss/",
    "https://radiologybusiness.com/feed",
    "https://www.healthcaredive.com/feeds/news/",
]

GLOBAL_NEWS_QUERIES = [
    '"imaging center" opens OR "new radiology" OR "opens MRI" OR "opens CT"',
    '"hospital" OR "health system" OR "imaging center" "AI radiology" implements OR adopts OR deploys OR launches',
    '"radiology" backlog OR shortage "hospital" OR "imaging center"',
]

# Brave Search global queries — richer results, plain-text descriptions
BRAVE_GLOBAL_QUERIES = [
    "hospital implements AI radiology workflow",
    "health system adopts AI radiology reads",
    "imaging center deploys AI diagnostic",
    "hospital radiology backlog shortage AI",
]


async def collect_brave_global_signals(
    companies: list[dict],
    db_client,
    run_id: str,
    api_key: str,
) -> int:
    """
    Run global Brave Search queries for hospital/org AI adoption.
    Match articles to known companies by name substring.
    Returns count of signals inserted.
    """
    name_to_id = {c["name"]: c["id"] for c in companies if len(c["name"]) > 5}
    signals_found = 0

    for query in BRAVE_GLOBAL_QUERIES:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/news/search",
                    headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                    params={"q": query, "count": 10, "freshness": "pw", "country": "us"},
                )
            if resp.status_code != 200:
                continue
            results = resp.json().get("results", [])
        except Exception:
            continue

        for r in results:
            if not _brave_is_recent(r):
                continue

            title = r.get("title", "")
            summary = r.get("description", "")
            url = r.get("url", "")
            source = r.get("meta_url", {}).get("hostname", "") or "Brave News"

            if not url:
                continue

            score, subtype = score_news(title, summary)
            if score == 0:
                continue

            text = (title + " " + summary).lower()
            matched_ids = [cid for name, cid in name_to_id.items() if name.lower() in text]

            targets = [(cid,) for cid in matched_ids] if matched_ids else [(None,)]
            for (company_id,) in targets:
                existing = (
                    db_client.table("signals")
                    .select("id")
                    .eq("source_url", url)
                    .execute()
                )
                if existing.data:
                    continue
                signal = {
                    "company_id": company_id,
                    "signal_type": "news",
                    "signal_subtype": subtype,
                    "title": f"[News] {title}",
                    "description": summary[:500],
                    "score": score,
                    "source_url": url,
                    "source_name": source,
                    "raw_data": {"title": title, "summary": summary, "url": url, "query": query},
                    "status": "new",
                }
                db_client.table("signals").insert(signal).execute()
                signals_found += 1

        await asyncio.sleep(0.5)

    return signals_found


async def collect_trade_rss_signals(
    companies: list[dict],
    db_client,
    run_id: str,
) -> int:
    """
    Fetch trade publication RSS feeds (AuntMinnie, RadBusiness, HealthcareDive).
    Match articles to known companies by name substring.
    Returns count of signals inserted.
    """
    # Build name → id lookup (skip very short names to avoid false matches)
    name_to_id = {c["name"]: c["id"] for c in companies if len(c["name"]) > 5}
    signals_found = 0

    loop = asyncio.get_event_loop()

    for feed_url in TRADE_RSS_FEEDS:
        try:
            feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
        except Exception:
            continue

        for entry in feed.entries[:30]:
            if not _is_recent(entry):
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "")
            url = entry.get("link", "")
            source = feed.feed.get("title", feed_url)
            text = (title + " " + summary).lower()

            if not url:
                continue

            score, subtype = score_news(title, summary)
            if score == 0:
                continue

            # Find matching companies
            matched_ids: list[str] = []
            for name, cid in name_to_id.items():
                if name.lower() in text:
                    matched_ids.append(cid)

            # If no company match, skip (trade articles without company context aren't useful yet)
            if not matched_ids:
                continue

            for company_id in matched_ids:
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
                    "title": f"[Trade] {title}",
                    "description": _strip_html(summary)[:500],
                    "score": score,
                    "source_url": url,
                    "source_name": source,
                    "raw_data": {"title": title, "summary": summary, "url": url, "feed": feed_url},
                    "status": "new",
                }
                db_client.table("signals").insert(signal).execute()
                signals_found += 1

        await asyncio.sleep(0.5)

    return signals_found


async def collect_global_news_signals(
    companies: list[dict],
    db_client,
    run_id: str,
) -> int:
    """
    Run global news queries (not per-company).
    Uses Google News RSS + Brave Search global queries.
    Match articles to known companies by name substring.
    Returns count of signals inserted.
    """
    settings = get_settings()
    signals_found = 0

    # Brave global queries (primary — richer, plain-text results)
    if settings.brave_api_key:
        found = await collect_brave_global_signals(companies, db_client, run_id, settings.brave_api_key)
        signals_found += found

    name_to_id = {c["name"]: c["id"] for c in companies if len(c["name"]) > 5}
    loop = asyncio.get_event_loop()

    subtype_map = {
        GLOBAL_NEWS_QUERIES[0]: "new_clinic",
        GLOBAL_NEWS_QUERIES[1]: "ai_adoption",
        GLOBAL_NEWS_QUERIES[2]: "backlog",
    }

    for query in GLOBAL_NEWS_QUERIES:
        url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+").replace('"', '%22'))
        try:
            feed = await loop.run_in_executor(None, feedparser.parse, url)
        except Exception:
            await asyncio.sleep(1)
            continue

        for entry in feed.entries[:20]:
            if not _is_recent(entry):
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "")
            article_url = entry.get("link", "")
            text = (title + " " + summary).lower()

            if not article_url:
                continue

            score, subtype = score_news(title, summary)
            forced_subtype = subtype_map[query]
            # Use forced subtype if scorer didn't find one
            if score == 0:
                score = 5
                subtype = forced_subtype
            else:
                subtype = forced_subtype

            matched_ids: list[str] = []
            for name, cid in name_to_id.items():
                if name.lower() in text:
                    matched_ids.append(cid)

            if matched_ids:
                for company_id in matched_ids:
                    existing = (
                        db_client.table("signals")
                        .select("id")
                        .eq("source_url", article_url)
                        .eq("company_id", company_id)
                        .execute()
                    )
                    if existing.data:
                        continue
                    signal = {
                        "company_id": company_id,
                        "signal_type": "news",
                        "signal_subtype": subtype,
                        "title": f"[Global] {title}",
                        "description": _strip_html(summary)[:500],
                        "score": score,
                        "source_url": article_url,
                        "source_name": entry.get("source", {}).get("title", "Google News"),
                        "raw_data": {"title": title, "summary": summary, "url": article_url, "query": query},
                        "status": "new",
                    }
                    db_client.table("signals").insert(signal).execute()
                    signals_found += 1
            else:
                # Market intel with no company match — store with NULL company_id
                existing = (
                    db_client.table("signals")
                    .select("id")
                    .eq("source_url", article_url)
                    .is_("company_id", "null")
                    .execute()
                )
                if existing.data:
                    continue
                signal = {
                    "company_id": None,
                    "signal_type": "news",
                    "signal_subtype": subtype,
                    "title": f"[Global] {title}",
                    "description": _strip_html(summary)[:500],
                    "score": score,
                    "source_url": article_url,
                    "source_name": entry.get("source", {}).get("title", "Google News"),
                    "raw_data": {"title": title, "summary": summary, "url": article_url, "query": query},
                    "status": "new",
                }
                db_client.table("signals").insert(signal).execute()
                signals_found += 1

        await asyncio.sleep(1)

    return signals_found  # includes Brave global count from above


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

        # Per-company news via Brave Search (fast, no timeouts).
        # Google News RSS is skipped here — it hangs too often on per-company queries
        # and all market-wide coverage is handled by global_news + trade_rss runs.
        news_items: list[dict] = []
        if settings.brave_api_key:
            brave_items = await fetch_brave_news(company_name, settings.brave_api_key)
            news_items.extend(brave_items)

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
                "description": _strip_html(item.get("summary", ""))[:500],
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
