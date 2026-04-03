from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.enums import MessageStatus, MessageType, Language


class Message(Base):
    """Individual WhatsApp message tracking"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    campaign_run_id = Column(Integer, ForeignKey("campaign_runs.id"), nullable=True, index=True)
    
    # Message type: distinguishes campaign messages from SIP/Loan reminders
    message_type = Column(
        SQLEnum(MessageType),
        default=MessageType.CAMPAIGN,
        nullable=False,
        index=True,
    )
    
    # Message content
    phone_number = Column(String, nullable=False)  # Denormalized for quick access
    template_name = Column(String, nullable=False)
    language = Column(SQLEnum(Language), nullable=False)
    message_body = Column(Text, nullable=False)  # Rendered message with variables filled
    
    # WhatsApp identifiers
    whatsapp_message_id = Column(String, nullable=True, unique=True, index=True)
    
    # Status tracking
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.QUEUED, nullable=False, index=True)
    
    # Scheduling – when the message should be sent (NULL = send immediately)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    
    # Timestamps for message lifecycle
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    contact = relationship("Contact", back_populates="messages")
    campaign_run = relationship("CampaignRun", back_populates="messages")
    
    __table_args__ = (
        Index('idx_jeweller_status', 'jeweller_id', 'status'),
        Index('idx_campaign_status', 'campaign_run_id', 'status'),
        Index('idx_status_queued', 'status', 'queued_at'),
        Index('idx_status_scheduled', 'status', 'scheduled_at'),
        Index('idx_type_status', 'message_type', 'status'),
        Index('idx_jeweller_created', 'jeweller_id', 'created_at'),
    )
