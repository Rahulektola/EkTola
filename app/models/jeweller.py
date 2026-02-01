from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Jeweller(Base):
    """Jeweller model - tenant entity (authenticates via WhatsApp OTP)
    
    Jewellers:
    - Add contacts (customers)
    - Create and run WhatsApp campaigns
    - Manage their customer database
    - View campaign analytics
    
    Authentication: WhatsApp OTP only (no password)
    """
    __tablename__ = "jewellers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Business details
    business_name = Column(String, nullable=False)
    owner_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    
    # WhatsApp Business Account details
    waba_id = Column(String, nullable=True)
    phone_number_id = Column(String, nullable=True)
    webhook_verify_token = Column(String, nullable=True)
    access_token = Column(Text, nullable=True)  # Encrypted in production
    
    # Status
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # WhatsApp verified
    onboarding_completed = Column(Boolean, default=False)
    
    # Subscription (future use)
    subscription_status = Column(String, default="trial")  # trial, active, suspended
    
    # Settings
    timezone = Column(String, default="Asia/Kolkata")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    contacts = relationship("Contact", back_populates="jeweller", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="jeweller", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="jeweller", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Jeweller {self.business_name} ({self.phone_number})>"
