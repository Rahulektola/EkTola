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
    business_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    
    # WhatsApp Business Account details
    waba_id = Column(String, nullable=True)
    phone_number_id = Column(String, nullable=True)
    webhook_verify_token = Column(String, nullable=True)
    access_token = Column(Text, nullable=True)  # Encrypted in production
    
    # Status
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Settings
    timezone = Column(String, default="Asia/Kolkata")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="jeweller")
    contacts = relationship("Contact", back_populates="jeweller", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="jeweller", cascade="all, delete-orphan")
