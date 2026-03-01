from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Jeweller(Base):
    """Jeweller model - tenant entity"""
    __tablename__ = "jewellers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Business details
    business_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=False)
    
    # WhatsApp Business Account details
    waba_id = Column(String(255), nullable=True)
    phone_number_id = Column(String(255), nullable=True)
    webhook_verify_token = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)  # Encrypted token
    
    # Facebook/Meta Integration (Embedded Signup)
    fb_app_scoped_user_id = Column(String(255), nullable=True)  # Facebook User ID
    access_token_expires_at = Column(DateTime, nullable=True)  # Token expiry
    waba_name = Column(String(255), nullable=True)  # Business name from Meta
    phone_display_number = Column(String(50), nullable=True)  # Human-readable phone
    business_verification_status = Column(String(50), nullable=True)  # verified|pending|unverified
    whatsapp_connected_at = Column(DateTime, nullable=True)  # Connection timestamp
    last_token_refresh = Column(DateTime, nullable=True)  # Last refresh time
    
    # Status
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Admin notes (private, internal use only)
    admin_notes = Column(Text, nullable=True)
    
    # Settings
    timezone = Column(String(50), default="Asia/Kolkata")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="jeweller")
    contacts = relationship("Contact", back_populates="jeweller", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="jeweller", cascade="all, delete-orphan")