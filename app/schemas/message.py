from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.utils.enums import MessageStatus, Language


# ============ Message Schemas ============

class MessageResponse(BaseModel):
    """Individual message details"""
    id: int
    jeweller_id: int
    contact_id: int
    campaign_run_id: Optional[int] = None
    phone_number: str
    template_name: str
    language: Language
    whatsapp_message_id: Optional[str] = None
    status: MessageStatus
    queued_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int
    
    class Config:
        from_attributes = True


class MessageStatsResponse(BaseModel):
    """Message delivery statistics"""
    total_messages: int
    queued: int
    sent: int
    delivered: int
    read: int
    failed: int
    delivery_rate: float  # Percentage
    read_rate: float  # Percentage


class FailureBreakdown(BaseModel):
    """Message failure reasons breakdown"""
    failure_reason: str
    count: int
