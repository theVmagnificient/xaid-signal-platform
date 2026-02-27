"""
Sync endpoints — trigger signal collection and data import.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from datetime import datetime, timezone
from app.database import get_db
from app.services.signal_news import collect_news_signals
from app.services.signal_job_postings import collect_job_posting_signals
from app.services.signal_job_changes import collect_job_change_signals

router = APIRouter(prefix="/sync", tags=["sync"])


async def _run_signals(run_type: str, db):
    """Core signal collection logic — runs in background."""
    run = (
        db.table("signal_runs")
        .insert({"run_type": run_type})
        .execute()
        .data[0]
    )
    run_id = run["id"]

    # Load companies
    companies = db.table("companies").select("id, name, domain").execute().data
    total_found = 0
    errors = []

    try:
        if run_type in ("news", "full"):
            found = await collect_news_signals(companies, db, run_id)
            total_found += found
    except Exception as e:
        errors.append({"type": "news", "error": str(e)})

    try:
        if run_type in ("job_postings", "full"):
            found = await collect_job_posting_signals(companies, db, run_id)
            total_found += found
    except Exception as e:
        errors.append({"type": "job_postings", "error": str(e)})

    try:
        if run_type in ("job_changes", "full"):
            contacts = db.table("contacts").select("*").execute().data
            companies_by_id = {c["id"]: c for c in companies}
            found = await collect_job_change_signals(contacts, companies_by_id, db, run_id)
            total_found += found
    except Exception as e:
        errors.append({"type": "job_changes", "error": str(e)})

    # Update run record
    db.table("signal_runs").update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "companies_checked": len(companies),
        "signals_found": total_found,
        "errors": errors,
    }).eq("id", run_id).execute()


@router.post("/run")
async def trigger_signal_run(
    background_tasks: BackgroundTasks,
    run_type: str = "full",
    db=Depends(get_db),
):
    """Trigger signal collection. run_type: full | news | job_postings | job_changes"""
    allowed = {"full", "news", "job_postings", "job_changes"}
    if run_type not in allowed:
        return {"error": f"run_type must be one of {allowed}"}
    background_tasks.add_task(_run_signals, run_type, db)
    return {"status": "started", "run_type": run_type}


@router.get("/runs")
def list_runs(db=Depends(get_db)):
    result = (
        db.table("signal_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(20)
        .execute()
    )
    return {"data": result.data}
