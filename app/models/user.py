from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    """User model for authentication - can be jeweller or admin"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=True, index=True)  # Optional for jewellers, required for admins
    phone_number = Column(String, unique=True, nullable=True, index=True)  # Primary identifier for jewellers
    hashed_password = Column(String, nullable=True)  # Nullable for OTP-only auth
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # OTP fields for phone verification
    phone_otp_code = Column(String, nullable=True)
    phone_otp_expiry = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to jeweller (one-to-one)
    jeweller = relationship("Jeweller", back_populates="user", uselist=False)
