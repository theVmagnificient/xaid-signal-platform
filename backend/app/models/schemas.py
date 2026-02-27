from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class Company(BaseModel):
    id: Optional[UUID] = None
    pipedrive_id: Optional[int] = None
    name: str
    website: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    stage: Optional[str] = None
    deal_status: Optional[str] = None
    deal_id: Optional[int] = None
    radiologist_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Contact(BaseModel):
    id: Optional[UUID] = None
    pipedrive_id: Optional[int] = None
    company_id: Optional[UUID] = None
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None


class Signal(BaseModel):
    id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    signal_type: str  # job_change | job_posting | news
    signal_subtype: Optional[str] = None
    title: str
    description: Optional[str] = None
    score: int = 5
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    raw_data: Optional[dict] = None
    status: str = "new"
    detected_at: Optional[datetime] = None
    actioned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # Joined fields (not in DB)
    company_name: Optional[str] = None
    contact_name: Optional[str] = None


class SignalUpdate(BaseModel):
    status: str


class SignalRun(BaseModel):
    id: Optional[UUID] = None
    run_type: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    companies_checked: int = 0
    signals_found: int = 0
    errors: list = []
