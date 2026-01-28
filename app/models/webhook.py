from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Boolean, Index
from datetime import datetime
from app.database import Base


class WebhookEvent(Base):
    """WhatsApp webhook event storage for audit and debugging"""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=True, index=True)
    
    # Event identification
    event_type = Column(String, nullable=False, index=True)  # message_status, message_received, etc.
    whatsapp_message_id = Column(String, nullable=True, index=True)
    
    # Raw webhook payload
    payload = Column(Text, nullable=False)  # JSON payload from WhatsApp
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_event_type_received', 'event_type', 'received_at'),
        Index('idx_processed', 'processed', 'received_at'),
    )
