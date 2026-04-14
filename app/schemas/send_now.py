from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.utils.enums import SegmentType


class SendNowSingleRequest(BaseModel):
    """Send reminder to a single contact immediately"""
    contact_id: int


class SendNowBulkRequest(BaseModel):
    """Send reminder to multiple contacts immediately"""
    contact_ids: List[int] = Field(..., min_length=1, max_length=10)


class SendNowSegmentRequest(BaseModel):
    """Send reminder to all contacts in a segment immediately"""
    segment: SegmentType


class SendNowResponse(BaseModel):
    """Response after queuing send-now messages"""
    task_id: str
    total_queued: int
    message: str


class SendNowStatusResponse(BaseModel):
    """Status of a send-now batch"""
    task_id: str
    total: int
    sent: int
    failed: int
    pending: int
    status: str  # PENDING, IN_PROGRESS, COMPLETED
