#!/usr/bin/env python3
"""
Manual signal collection runner.
Can be invoked from CLI or via GitHub Actions.

Usage:
  python scripts/run_signals.py --type full
  python scripts/run_signals.py --type news
  python scripts/run_signals.py --type job_postings
  python scripts/run_signals.py --type job_changes
"""

import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.signal_news import collect_news_signals
from app.services.signal_job_postings import collect_job_posting_signals
from app.services.signal_job_changes import collect_job_change_signals
from datetime import datetime, timezone
from rich.console import Console

console = Console()


async def run(run_type: str):
    db = get_db()
    console.print(f"[bold blue]Starting signal run: {run_type}[/bold blue]")
    start = datetime.now(timezone.utc)

    run_record = db.table("signal_runs").insert({"run_type": run_type}).execute().data[0]
    run_id = run_record["id"]

    companies = db.table("companies").select("id, name, domain").execute().data
    console.print(f"Loaded {len(companies)} companies")

    total_found = 0
    errors = []

    if run_type in ("news", "full"):
        console.print("[yellow]Collecting news signals...[/yellow]")
        try:
            found = await collect_news_signals(companies, db, run_id)
            console.print(f"  [green]News signals: {found}[/green]")
            total_found += found
        except Exception as e:
            console.print(f"  [red]News error: {e}[/red]")
            errors.append({"type": "news", "error": str(e)})

    if run_type in ("job_postings", "full"):
        console.print("[yellow]Collecting job posting signals...[/yellow]")
        try:
            found = await collect_job_posting_signals(companies, db, run_id)
            console.print(f"  [green]Job posting signals: {found}[/green]")
            total_found += found
        except Exception as e:
            console.print(f"  [red]Job postings error: {e}[/red]")
            errors.append({"type": "job_postings", "error": str(e)})

    if run_type in ("job_changes", "full"):
        console.print("[yellow]Collecting job change signals...[/yellow]")
        try:
            contacts = db.table("contacts").select("*").execute().data
            companies_by_id = {c["id"]: c for c in companies}
            found = await collect_job_change_signals(contacts, companies_by_id, db, run_id)
            console.print(f"  [green]Job change signals: {found}[/green]")
            total_found += found
        except Exception as e:
            console.print(f"  [red]Job changes error: {e}[/red]")
            errors.append({"type": "job_changes", "error": str(e)})

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    db.table("signal_runs").update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "companies_checked": len(companies),
        "signals_found": total_found,
        "errors": errors,
    }).eq("id", run_id).execute()

    console.print(f"\n[bold green]✓ Done in {elapsed:.1f}s[/bold green]")
    console.print(f"  Companies checked: {len(companies)}")
    console.print(f"  New signals found: {total_found}")
    if errors:
        console.print(f"  [red]Errors: {len(errors)}[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="full", choices=["full", "news", "job_postings", "job_changes"])
    args = parser.parse_args()
    asyncio.run(run(args.type))
