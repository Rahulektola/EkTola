from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.enums import CampaignType, SegmentType


class Template(Base):
    """WhatsApp message template - admin managed"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Template identification
    template_name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    
    # Template categorization
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    sub_segment = Column(SQLEnum(SegmentType), nullable=True, index=True)  # For utility messages
    
    # Template metadata
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)  # WhatsApp category: UTILITY, MARKETING, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Variables placeholders (e.g., {{1}}, {{2}})
    variable_count = Column(Integer, default=0)
    variable_names = Column(Text, nullable=True)  # JSON array: ["customer_name", "amount"]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    translations = relationship("TemplateTranslation", back_populates="template", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="template")


class TemplateTranslation(Base):
    """Language-specific template content"""
    __tablename__ = "template_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False, index=True)
    
    # Language-specific content
    language = Column(SQLEnum(Language), nullable=False, index=True)
    header_text = Column(String, nullable=True)
    body_text = Column(Text, nullable=False)
    footer_text = Column(String, nullable=True)
    
    # WhatsApp approval status
    whatsapp_template_id = Column(String, nullable=True)  # From WhatsApp after approval
    approval_status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("Template", back_populates="translations")
