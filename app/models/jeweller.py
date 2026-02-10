from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.enums import ApprovalStatus


class Jeweller(Base):
    """Jeweller model - tenant entity"""
    __tablename__ = "jewellers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Business details
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=False)
    address = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    
    # WhatsApp Business Account details (per-jeweller WABA)
    waba_id = Column(String(100), nullable=True)
    phone_number_id = Column(String(100), nullable=True)
    webhook_verify_token = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)  # Encrypted in production
    is_whatsapp_business = Column(Boolean, default=False)  # Personal vs Business number
    meta_app_status = Column(Boolean, default=False)  # Green light when Meta App linked
    
    # Approval workflow
    is_approved = Column(Boolean, default=False)  # Kept for backward compat
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    # Admin internal notes (never visible to jeweller)
    admin_notes = Column(Text, nullable=True)
    
    # Settings
    timezone = Column(String(50), default="Asia/Kolkata")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="jeweller", foreign_keys=[user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    contacts = relationship("Contact", back_populates="jeweller", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="jeweller", cascade="all, delete-orphan")
