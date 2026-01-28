from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ============ Authentication Schemas ============

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: int
    email: str
    is_admin: bool
    jeweller_id: Optional[int] = None


class LoginRequest(BaseModel):
    """Login with email and password"""
    email: EmailStr
    password: str


class OTPLoginRequest(BaseModel):
    """Request OTP for login"""
    email: EmailStr


class OTPVerifyRequest(BaseModel):
    """Verify OTP code"""
    email: EmailStr
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
    """Jeweller profile response"""
    id: int
    user_id: int
    business_name: str
    phone_number: str
    is_approved: bool
    is_active: bool
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