from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.database import get_db

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def list_signals(
    signal_type: Optional[str] = None,
    status: Optional[str] = "new",
    min_score: int = 1,
    limit: int = Query(50, le=200),
    offset: int = 0,
    adjacent: Optional[bool] = None,
    db=Depends(get_db),
):
    q = (
        db.table("signals")
        .select("*, companies(name, stage), contacts(name, job_title)")
        .gte("score", min_score)
        .order("score", desc=True)
        .order("detected_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if signal_type:
        q = q.eq("signal_type", signal_type)
    if status:
        q = q.eq("status", status)
    if adjacent is True:
        q = q.like("signal_subtype", "adjacent_%")
    else:
        # Default: exclude adjacent from main dashboard (covers adjacent=False and adjacent=None)
        q = q.not_.like("signal_subtype", "adjacent_%")

    result = q.execute()
    return {"data": result.data, "count": len(result.data)}


@router.get("/stats")
def get_stats(db=Depends(get_db)):
    total = db.table("signals").select("id", count="exact").execute()
    by_type = {}
    for t in ["job_change", "job_posting", "news"]:
        r = db.table("signals").select("id", count="exact").eq("signal_type", t).eq("status", "new").execute()
        by_type[t] = r.count or 0

    companies = db.table("companies").select("id", count="exact").execute()

    return {
        "total_signals": total.count or 0,
        "new_by_type": by_type,
        "total_companies": companies.count or 0,
    }


@router.get("/{signal_id}")
def get_signal(signal_id: str, db=Depends(get_db)):
    result = (
        db.table("signals")
        .select("*, companies(*), contacts(*)")
        .eq("id", signal_id)
        .single()
        .execute()
    )
    return result.data


@router.patch("/{signal_id}")
def update_signal_status(signal_id: str, body: dict, db=Depends(get_db)):
    allowed = {"new", "viewed", "actioned", "dismissed"}
    status = body.get("status")
    if status not in allowed:
        return {"error": f"status must be one of {allowed}"}

    update = {"status": status}
    if status == "actioned":
        from datetime import datetime, timezone
        update["actioned_at"] = datetime.now(timezone.utc).isoformat()

    result = db.table("signals").update(update).eq("id", signal_id).execute()
    return result.data
