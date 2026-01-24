from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.utils.enums import CampaignType, SegmentType, Language


# ============ Template Schemas (Admin only) ============

class TemplateTranslationCreate(BaseModel):
    """Create template translation"""
    language: Language
    header_text: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = None


class TemplateTranslationResponse(BaseModel):
    """Template translation response"""
    id: int
    template_id: int
    language: Language
    header_text: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = None
    whatsapp_template_id: Optional[str] = None
    approval_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    """Create WhatsApp template (admin only)"""
    template_name: str
    display_name: str
    campaign_type: CampaignType
    sub_segment: Optional[SegmentType] = None
    description: Optional[str] = None
    category: str  # UTILITY, MARKETING, etc.
    variable_count: int = 0
    variable_names: Optional[List[str]] = None
    translations: List[TemplateTranslationCreate]
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "gold_loan_reminder",
                "display_name": "Gold Loan Monthly Reminder",
                "campaign_type": "UTILITY",
                "sub_segment": "GOLD_LOAN",
                "category": "UTILITY",
                "variable_count": 2,
                "variable_names": ["customer_name", "due_date"],
                "translations": [
                    {
                        "language": "en",
                        "body_text": "Dear {{1}}, your gold loan payment is due on {{2}}."
                    }
                ]
            }
        }


class TemplateUpdate(BaseModel):
    """Update template"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Template response"""
    id: int
    template_name: str
    display_name: str
    campaign_type: CampaignType
    sub_segment: Optional[SegmentType] = None
    description: Optional[str] = None
    category: str
    is_active: bool
    variable_count: int
    variable_names: Optional[str] = None
    translations: List[TemplateTranslationResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Template list for jeweller selection"""
    templates: List[TemplateResponse]
    total: int
