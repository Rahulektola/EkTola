from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date, time
from app.utils.enums import CampaignType, CampaignStatus, RecurrenceType, SegmentType


# ============ Campaign Schemas ============

class CampaignCreate(BaseModel):
    """Create new campaign"""
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    sub_segment: Optional[SegmentType] = None  # Required if campaign_type is UTILITY
    template_id: int
    recurrence_type: RecurrenceType
    start_date: date
    start_time: time
    end_date: Optional[date] = None
    variable_mapping: Optional[Dict[str, str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Monthly Gold Loan Reminder",
                "campaign_type": "UTILITY",
                "sub_segment": "GOLD_LOAN",
                "template_id": 1,
                "recurrence_type": "MONTHLY",
                "start_date": "2026-02-01",
                "start_time": "10:00:00",
                "variable_mapping": {"customer_name": "name"}
            }
        }


class CampaignUpdate(BaseModel):
    """Update campaign (applies to future runs only)"""
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    variable_mapping: Optional[Dict[str, str]] = None


class CampaignResponse(BaseModel):
    """Campaign response"""
    id: int
    jeweller_id: int
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    sub_segment: Optional[SegmentType] = None
    template_id: int
    recurrence_type: RecurrenceType
    start_date: date
    start_time: time
    end_date: Optional[date] = None
    timezone: str
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Paginated campaign list"""
    campaigns: List[CampaignResponse]
    total: int
    page: int
    page_size: int


class CampaignRunResponse(BaseModel):
    """Campaign run details"""
    id: int
    campaign_id: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str
    total_contacts: int
    eligible_contacts: int
    messages_queued: int
    messages_sent: int
    messages_delivered: int
    messages_read: int
    messages_failed: int
    
    class Config:
        from_attributes = True


class CampaignStatsResponse(BaseModel):
    """Campaign performance statistics"""
    campaign_id: int
    campaign_name: str
    total_runs: int
    total_messages_sent: int
    total_delivered: int
    total_read: int
    total_failed: int
    delivery_rate: float  # Percentage
    read_rate: float  # Percentage
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
