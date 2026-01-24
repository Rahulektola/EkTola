from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.utils.enums import SegmentType, Language


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
