from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from app.utils.enums import SegmentType, Language


# ============ Payment Schedule Schemas ============

class PaymentScheduleUpdate(BaseModel):
    """Update SIP/Loan payment schedule for a single contact"""
    sip_payment_day: Optional[int] = Field(None, ge=1, le=31, description="Day of month for SIP payment (1-31). NULL to clear.")
    loan_payment_day: Optional[int] = Field(None, ge=1, le=31, description="Day of month for Loan payment (1-31). NULL to clear.")
    sip_reminder_days_before: Optional[int] = Field(None, ge=1, le=15, description="Days before SIP due date to send reminder")
    loan_reminder_days_before: Optional[int] = Field(None, ge=1, le=15, description="Days before Loan due date to send reminder")


class PaymentScheduleClear(BaseModel):
    """Explicitly clear payment schedule fields"""
    clear_sip: bool = False
    clear_loan: bool = False


class BulkPaymentScheduleItem(BaseModel):
    """Single item in a bulk payment schedule update"""
    contact_id: int
    sip_payment_day: Optional[int] = Field(None, ge=1, le=31)
    loan_payment_day: Optional[int] = Field(None, ge=1, le=31)
    sip_reminder_days_before: Optional[int] = Field(None, ge=1, le=15)
    loan_reminder_days_before: Optional[int] = Field(None, ge=1, le=15)


class BulkPaymentScheduleRequest(BaseModel):
    """Bulk update payment schedules for multiple contacts"""
    schedules: List[BulkPaymentScheduleItem] = Field(..., min_items=1, max_items=500)


class BulkPaymentScheduleResponse(BaseModel):
    """Response from bulk payment schedule update"""
    updated: int
    failed: int
    failure_details: List[dict] = Field(default_factory=list)
    message: str


class PaymentScheduleResponse(BaseModel):
    """Payment schedule info for a contact"""
    contact_id: int
    name: Optional[str]
    phone_number: str
    segment: SegmentType
    sip_payment_day: Optional[int]
    loan_payment_day: Optional[int]
    sip_reminder_days_before: int
    loan_reminder_days_before: int
    last_sip_reminder_sent_at: Optional[datetime]
    last_loan_reminder_sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaymentScheduleListResponse(BaseModel):
    """Paginated list of contacts with payment schedules"""
    contacts: List[PaymentScheduleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReminderPreviewResponse(BaseModel):
    """Preview of upcoming reminders"""
    sip_reminders_due_today: int
    loan_reminders_due_today: int
    sip_contacts: List[PaymentScheduleResponse]
    loan_contacts: List[PaymentScheduleResponse]


# ============ Dashboard Contact Schemas ============

class DashboardContactCreate(BaseModel):
    """Create single contact from dashboard (simplified format)"""
    name: str
    mobile: str
    purpose: str  # "SIP", "LOAN", or "BOTH"
    date: str  # Date string from form
    
    @validator('purpose')
    def validate_purpose(cls, v):
        valid_purposes = ['SIP', 'LOAN', 'BOTH']
        if v.upper() not in valid_purposes:
            raise ValueError(f'Purpose must be one of: {", ".join(valid_purposes)}')
        return v.upper()
    
    @validator('mobile')
    def validate_mobile(cls, v):
        # Basic validation - will be normalized in the router
        if not v or len(v.replace('+', '').replace(' ', '').replace('-', '')) < 10:
            raise ValueError('Invalid mobile number')
        return v


class DashboardContactResponse(BaseModel):
    """Contact response for dashboard"""
    id: int
    name: Optional[str]
    mobile: str
    purpose: str
    date: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DashboardBulkUploadReport(BaseModel):
    """Report after dashboard bulk upload"""
    total_rows: int
    imported: int
    updated: int
    merged: int = 0  # intra-CSV duplicates that were collapsed
    failed: int
    failure_details: List[dict] = Field(default_factory=list)
    message: str = "Upload completed"


# ============ Contact Upload Schemas ============

class ContactUploadRow(BaseModel):
    """Single contact from CSV/XLSX"""
    phone_number: str
    segment: SegmentType
    preferred_language: Language
    name: Optional[str] = None
    customer_id: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None


class ContactImportReport(BaseModel):
    """Report after bulk contact upload"""
    total_rows: int
    imported: int
    updated: int
    failed: int
    failure_details: List[dict] = Field(default_factory=list)
    # Example: [{"row": 5, "phone": "+1234", "reason": "Invalid segment"}]


class ContactCreate(BaseModel):
    """Create single contact"""
    phone_number: str
    segment: SegmentType
    preferred_language: Language = Language.ENGLISH
    name: Optional[str] = None
    customer_id: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None


class ContactUpdate(BaseModel):
    """Update contact details"""
    name: Optional[str] = None
    segment: Optional[SegmentType] = None
    preferred_language: Optional[Language] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    opted_out: Optional[bool] = None
    sip_payment_day: Optional[int] = Field(None, ge=1, le=31)
    loan_payment_day: Optional[int] = Field(None, ge=1, le=31)
    sip_reminder_days_before: Optional[int] = Field(None, ge=1, le=15)
    loan_reminder_days_before: Optional[int] = Field(None, ge=1, le=15)


class ContactResponse(BaseModel):
    """Contact response"""
    id: int
    jeweller_id: int
    phone_number: str
    name: Optional[str] = None
    customer_id: Optional[str] = None
    segment: SegmentType
    preferred_language: Language
    opted_out: bool
    sip_payment_day: Optional[int] = None
    loan_payment_day: Optional[int] = None
    sip_reminder_days_before: int = 3
    loan_reminder_days_before: int = 3
    last_sip_reminder_sent_at: Optional[datetime] = None
    last_loan_reminder_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Paginated contact list"""
    contacts: List[ContactResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ContactSegmentStats(BaseModel):
    """Contact distribution by segment"""
    segment: SegmentType
    count: int
    opted_out_count: int


class ContactBulkDelete(BaseModel):
    """Bulk delete contacts request"""
    contact_ids: List[int] = Field(..., min_items=1, description="List of contact IDs to delete")


class ContactBulkDeleteResponse(BaseModel):
    """Bulk delete contacts response"""
    deleted_count: int
    message: str = "Contacts deleted successfully"
