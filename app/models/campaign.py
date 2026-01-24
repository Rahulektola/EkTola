from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean, Date, Time, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.enums import CampaignType, CampaignStatus, RecurrenceType, SegmentType


class Campaign(Base):
    """Campaign model - jeweller-specific messaging campaigns"""
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False, index=True)
    
    # Campaign details
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Campaign type and targeting
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    sub_segment = Column(SQLEnum(SegmentType), nullable=True, index=True)  # Required for UTILITY
    
    # Scheduling
    recurrence_type = Column(SQLEnum(RecurrenceType), nullable=False)
    start_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_date = Column(Date, nullable=True)
    timezone = Column(String, default="Asia/Kolkata")
    
    # Status
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    
    # Template variables mapping (JSON)
    variable_mapping = Column(Text, nullable=True)  # {"customer_name": "{{name}}", "amount": "{{loan_amount}}"}
    
    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    jeweller = relationship("Jeweller", back_populates="campaigns")
    template = relationship("Template", back_populates="campaigns")
    campaign_runs = relationship("CampaignRun", back_populates="campaign", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_jeweller_status', 'jeweller_id', 'status'),
        Index('idx_jeweller_type', 'jeweller_id', 'campaign_type'),
    )


class CampaignRun(Base):
    """Individual execution instance of a campaign"""
    __tablename__ = "campaign_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    
    # Run scheduling
    scheduled_at = Column(DateTime, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Run status
    status = Column(String, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    
    # Audience snapshot at run time
    total_contacts = Column(Integer, default=0)
    eligible_contacts = Column(Integer, default=0)  # Excludes opted-out
    
    # Execution stats
    messages_queued = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    messages_delivered = Column(Integer, default=0)
    messages_read = Column(Integer, default=0)
    messages_failed = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_runs")
    messages = relationship("Message", back_populates="campaign_run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_scheduled', 'scheduled_at', 'status'),
    )
