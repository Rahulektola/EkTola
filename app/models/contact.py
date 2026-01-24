from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.enums import SegmentType, Language


class Contact(Base):
    """Contact model - tenant-isolated customer data"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    
    # Contact information
    phone_number = Column(String, nullable=False)  # E.164 format
    name = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    
    # Segmentation (MVP locked - one segment per contact)
    segment = Column(SQLEnum(SegmentType), nullable=False, index=True)
    
    # Language preference
    preferred_language = Column(SQLEnum(Language), nullable=False, default=Language.ENGLISH, index=True)
    
    # Consent & opt-out
    opted_out = Column(Boolean, default=False, index=True)
    opted_out_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON or comma-separated
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    jeweller = relationship("Jeweller", back_populates="contacts")
    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    
    # Composite unique constraint: phone_number unique per jeweller
    __table_args__ = (
        Index('idx_jeweller_phone', 'jeweller_id', 'phone_number', unique=True),
        Index('idx_jeweller_segment', 'jeweller_id', 'segment'),
        Index('idx_jeweller_opted_out', 'jeweller_id', 'opted_out'),
    )
