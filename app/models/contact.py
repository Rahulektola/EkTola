from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Index, Enum as SQLEnum, CheckConstraint
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
    phone_number = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    customer_id = Column(String(100), nullable=True)
    
    # Segmentation
    segment = Column(SQLEnum(SegmentType), nullable=False, index=True)
    
    # Language preference
    preferred_language = Column(SQLEnum(Language), nullable=False, default=Language.ENGLISH, index=True)
    
    # Consent & opt-out
    opted_out = Column(Boolean, default=False, index=True)
    opted_out_at = Column(DateTime, nullable=True)
    
    # ==================== PAYMENT SCHEDULING ====================
    # Day of month (1-31) when payment is due. NULL = no schedule = no reminder sent.
    sip_payment_day = Column(Integer, nullable=True)   # e.g. 5 means 5th of every month
    loan_payment_day = Column(Integer, nullable=True)   # e.g. 15 means 15th of every month
    
    # How many days before the due date to send a reminder (default 3)
    sip_reminder_days_before = Column(Integer, nullable=False, default=3)
    loan_reminder_days_before = Column(Integer, nullable=False, default=3)
    
    # Track last reminder sent to prevent duplicates within the same month
    last_sip_reminder_sent_at = Column(DateTime, nullable=True)
    last_loan_reminder_sent_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    jeweller = relationship("Jeweller", back_populates="contacts")
    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_jeweller_phone', 'jeweller_id', 'phone_number', unique=True),
        Index('idx_jeweller_segment', 'jeweller_id', 'segment'),
        Index('idx_jeweller_opted_out', 'jeweller_id', 'opted_out'),
        Index('idx_jeweller_deleted_opted', 'jeweller_id', 'is_deleted', 'opted_out'),
        Index('idx_jeweller_sip_day', 'jeweller_id', 'sip_payment_day'),
        Index('idx_jeweller_loan_day', 'jeweller_id', 'loan_payment_day'),
        CheckConstraint('sip_payment_day IS NULL OR (sip_payment_day >= 1 AND sip_payment_day <= 31)', name='ck_sip_day_range'),
        CheckConstraint('loan_payment_day IS NULL OR (loan_payment_day >= 1 AND loan_payment_day <= 31)', name='ck_loan_day_range'),
    )