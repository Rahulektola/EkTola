"""
Admin Dashboard Schemas
Request/Response models for admin endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from app.utils.enums import ApprovalStatus, SegmentType, Language, CampaignType, CampaignStatus


# ============ Jeweller Management Schemas ============

class JewellerDetailResponse(BaseModel):
    """Full jeweller profile for admin view (includes admin-only fields)"""
    id: int
    user_id: int
    business_name: str
    owner_name: Optional[str] = None
    phone_number: str
    address: Optional[str] = None
    location: Optional[str] = None
    
    # WhatsApp integration
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    is_whatsapp_business: bool = False
    meta_app_status: bool = False
    
    # Approval
    is_approved: bool
    approval_status: ApprovalStatus
    rejection_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by_user_id: Optional[int] = None
    
    is_active: bool
    
    # Admin-only fields
    admin_notes: Optional[str] = None
    
    # Settings
    timezone: str
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Aggregates (populated by endpoint)
    total_contacts: int = 0
    total_campaigns: int = 0
    total_messages: int = 0
    
    # User email (from related User)
    email: Optional[str] = None
    
    class Config:
        from_attributes = True


class JewellerListResponse(BaseModel):
    """Paginated jeweller list with filters"""
    jewellers: List[JewellerDetailResponse]
    total: int
    page: int
    page_size: int
    # Status counts for filter badges
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0


class JewellerUpdateRequest(BaseModel):
    """Admin can edit any jeweller field"""
    business_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    is_whatsapp_business: Optional[bool] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class AdminNotesRequest(BaseModel):
    """Update admin internal notes for a jeweller"""
    admin_notes: str = Field(..., description="Internal notes about the jeweller (not visible to jeweller)")


class MetaStatusUpdateRequest(BaseModel):
    """Update Meta WhatsApp integration details"""
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    is_whatsapp_business: Optional[bool] = None
    meta_app_status: Optional[bool] = None


class RejectJewellerRequest(BaseModel):
    """Rejection requires a mandatory reason"""
    rejection_reason: str = Field(
        ..., 
        min_length=5,
        description="Mandatory reason for rejection. Stored and shown to the jeweller."
    )


class ApproveJewellerResponse(BaseModel):
    """Response after approval/rejection"""
    id: int
    business_name: str
    approval_status: ApprovalStatus
    rejection_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    message: str
    
    class Config:
        from_attributes = True


# ============ Admin Contact Management Schemas ============

class AdminContactListResponse(BaseModel):
    """Contact list for admin view (includes jeweller context)"""
    id: int
    jeweller_id: int
    phone_number: str
    name: Optional[str] = None
    customer_id: Optional[str] = None
    segment: SegmentType
    preferred_language: Language
    opted_out: bool
    notes: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AdminContactsPageResponse(BaseModel):
    """Paginated contacts for admin"""
    contacts: List[AdminContactListResponse]
    total: int
    page: int
    page_size: int
    jeweller_id: int
    jeweller_name: str


# ============ Admin Campaign Management Schemas ============

class AdminCampaignCreateRequest(BaseModel):
    """Admin creates campaign on behalf of a jeweller"""
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    sub_segment: Optional[SegmentType] = None
    template_id: int
    recurrence_type: str  # RecurrenceType value
    start_date: str  # ISO date
    start_time: str  # ISO time
    end_date: Optional[str] = None
    variable_mapping: Optional[Dict[str, str]] = None


class AdminCampaignListResponse(BaseModel):
    """Campaign list for admin view"""
    id: int
    jeweller_id: int
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    sub_segment: Optional[SegmentType] = None
    status: CampaignStatus
    template_id: int
    recurrence_type: str
    start_date: str
    start_time: str
    end_date: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_runs: int = 0
    total_messages_sent: int = 0
    
    class Config:
        from_attributes = True


class AdminCampaignsPageResponse(BaseModel):
    """Paginated campaigns for admin"""
    campaigns: List[AdminCampaignListResponse]
    total: int
    page: int
    page_size: int
    jeweller_id: int
    jeweller_name: str


# ============ Admin Message History Schemas ============

class AdminMessageResponse(BaseModel):
    """Message record for admin view"""
    id: int
    jeweller_id: int
    contact_id: int
    phone_number: str
    template_name: str
    language: str
    message_body: str
    status: str
    whatsapp_message_id: Optional[str] = None
    queued_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class AdminMessagesPageResponse(BaseModel):
    """Paginated messages for admin"""
    messages: List[AdminMessageResponse]
    total: int
    page: int
    page_size: int
    jeweller_id: int


# ============ Impersonation Schema ============

class ImpersonateResponse(BaseModel):
    """Token returned for impersonation mode (admin sees jeweller's dashboard)"""
    access_token: str
    token_type: str = "bearer"
    jeweller_id: int
    jeweller_name: str
    message: str


# ============ Admin Analytics Drill-down ============

class JewellerAnalyticsResponse(BaseModel):
    """Single jeweller drill-down analytics for admin"""
    jeweller_id: int
    business_name: str
    total_contacts: int
    opted_out_contacts: int
    total_campaigns: int
    active_campaigns: int
    total_messages: int
    messages_last_30_days: int
    delivery_rate: float
    read_rate: float
    campaign_success_rates: List[Dict]
    daily_message_volume: List[Dict]


# ============ WhatsApp Status Schemas ============

class WhatsAppStatusResponse(BaseModel):
    """WhatsApp connection status for a jeweller"""
    connected: bool
    waba_id: Optional[str] = None
    waba_name: Optional[str] = None
    phone_number_id: Optional[str] = None
    phone_display_number: Optional[str] = None
    business_verification_status: Optional[str] = None
    connected_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
    token_expires_in_days: Optional[int] = None
    last_token_refresh: Optional[datetime] = None
    fb_app_scoped_user_id: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============ Contact Purge & Restore Schemas ============

class DeletedContactResponse(BaseModel):
    """Deleted contact details for restore view"""
    id: int
    jeweller_id: int
    phone_number: str
    name: Optional[str] = None
    customer_id: Optional[str] = None
    segment: SegmentType
    preferred_language: Language
    deleted_at: Optional[datetime] = None
    days_since_deletion: int = 0
    
    class Config:
        from_attributes = True


class DeletedContactsListResponse(BaseModel):
    """Paginated list of soft-deleted contacts"""
    contacts: List[DeletedContactResponse]
    total: int
    page: int
    page_size: int
    jeweller_id: Optional[int] = None  # None = all jewellers
    jeweller_name: Optional[str] = None


class ContactPurgeRequest(BaseModel):
    """Request to purge old deleted contacts"""
    older_than_days: int = Field(
        30,
        ge=1,
        le=365,
        description="Permanently delete contacts that were soft-deleted more than X days ago"
    )
    jeweller_id: Optional[int] = Field(
        None,
        description="Purge only for specific jeweller (None = all jewellers)"
    )


class ContactPurgeResponse(BaseModel):
    """Response after purging contacts"""
    purged_count: int
    message: str
    jeweller_id: Optional[int] = None
    older_than_days: int


class ContactRestoreRequest(BaseModel):
    """Request to restore deleted contacts"""
    contact_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of contact IDs to restore"
    )


class ContactRestoreResponse(BaseModel):
    """Response after restoring contacts"""
    restored_count: int
    failed_count: int
    message: str
    restored_ids: List[int]
    failed_ids: List[int]
