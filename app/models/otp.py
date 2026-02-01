from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from app.database import Base
import enum
import secrets


class OTPPurpose(enum.Enum):
    """Purpose of OTP"""
    LOGIN = "login"
    SIGNUP = "signup"
    RESET_PASSWORD = "reset_password"


class OTP(Base):
    """OTP model for WhatsApp authentication"""
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True, nullable=False)
    otp_code = Column(String(6), nullable=False)
    purpose = Column(SQLEnum(OTPPurpose), nullable=False, default=OTPPurpose.LOGIN)
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_expired = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    def is_valid(self) -> bool:
        """Check if OTP is still valid"""
        now = datetime.utcnow()
        return (
            not self.is_expired 
            and not self.is_verified 
            and self.attempts < self.max_attempts
            and now < self.expires_at
        )
    
    def __repr__(self):
        return f"<OTP {self.phone_number} ({self.purpose.value})>"
