from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.database import get_db

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def list_companies(
    limit: int = Query(50, le=200),
    offset: int = 0,
    search: Optional[str] = None,
    db=Depends(get_db),
):
    q = db.table("companies").select("*").order("name").range(offset, offset + limit - 1)
    if search:
        q = q.ilike("name", f"%{search}%")
    result = q.execute()
    return {"data": result.data, "count": len(result.data)}


@router.get("/{company_id}")
def get_company(company_id: str, db=Depends(get_db)):
    company = (
        db.table("companies").select("*").eq("id", company_id).single().execute()
    )
    signals = (
        db.table("signals")
        .select("*")
        .eq("company_id", company_id)
        .order("detected_at", desc=True)
        .execute()
    )
    contacts = (
        db.table("contacts")
        .select("*")
        .eq("company_id", company_id)
        .execute()
    )
    return {
        "company": company.data,
        "signals": signals.data,
        "contacts": contacts.data,
    }
