from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ============ Authentication Schemas ============

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Jeweller approval info (shown on login)
    approval_status: Optional[str] = None  # PENDING, APPROVED, REJECTED
    rejection_reason: Optional[str] = None  # Shown if rejected


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: int
    email: Optional[str] = None
    phone_number: Optional[str] = None
    is_admin: bool
    jeweller_id: Optional[int] = None


class LoginRequest(BaseModel):
    """Login with email and password (Admin)"""
    email: EmailStr
    password: str


class PhoneLoginRequest(BaseModel):
    """Login with phone and password (Jeweller)"""
    phone_number: str
    password: str


class OTPLoginRequest(BaseModel):
    """Request OTP for login (Email - Admin)"""
    email: EmailStr


class PhoneOTPRequest(BaseModel):
    """Request OTP via WhatsApp (Jeweller)"""
    phone_number: str


class OTPVerifyRequest(BaseModel):
    """Verify OTP code (Email - Admin)"""
    email: EmailStr
    otp_code: str


class PhoneOTPVerifyRequest(BaseModel):
    """Verify OTP code (WhatsApp - Jeweller)"""
    phone_number: str
    otp_code: str


class RegisterRequest(BaseModel):
    """Jeweller registration"""
    email: EmailStr
    password: str
    business_name: str
    phone_number: str


class UserResponse(BaseModel):
    """User profile response"""
    id: int
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class JewellerResponse(BaseModel):
    """Jeweller profile response (public - no admin_notes)"""
    id: int
    user_id: int
    business_name: str
    owner_name: Optional[str] = None
    phone_number: str
    address: Optional[str] = None
    location: Optional[str] = None
    is_approved: bool
    approval_status: Optional[str] = None
    rejection_reason: Optional[str] = None
    is_active: bool
    is_whatsapp_business: bool = False
    meta_app_status: bool = False
    timezone: str
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminRegisterRequest(BaseModel):
    """Admin registration with access code"""
    email: EmailStr
    password: str
    full_name: str
    access_code: str