from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime


# ============ Authentication Schemas ============

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_type: Literal["jeweller", "admin"]
    user: dict


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: int
    user_type: Literal["jeweller", "admin"]


# ============ Jeweller Authentication (WhatsApp OTP) ============

class OTPRequest(BaseModel):
    """Request OTP for jeweller"""
    phone_number: str = Field(..., regex=r"^\+?[1-9]\d{1,14}$", description="Phone number in international format")


class OTPVerify(BaseModel):
    """Verify OTP"""
    phone_number: str = Field(..., regex=r"^\+?[1-9]\d{1,14}$")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class JewellerSignup(BaseModel):
    """Jeweller registration with phone verification"""
    phone_number: str = Field(..., regex=r"^\+?[1-9]\d{1,14}$")
    otp_code: str = Field(..., min_length=6, max_length=6, description="OTP received on WhatsApp")
    business_name: str = Field(..., min_length=2, max_length=200)
    owner_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


# ============ Admin Authentication (Password) ============

class AdminLogin(BaseModel):
    """Admin login with email and password"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None  # For first admin creation
    phone_number: Optional[str] = None  # For first admin creation


class CreateAdminRequest(BaseModel):
    """Create new admin"""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: Optional[str] = Field(None, regex=r"^\+?[1-9]\d{1,14}$")


# ============ Response Schemas ============

class JewellerResponse(BaseModel):
    """Jeweller profile response"""
    id: int
    business_name: str
    owner_name: Optional[str] = None
    email: str
    phone_number: str
    is_approved: bool
    is_active: bool
    is_verified: bool
    onboarding_completed: bool
    subscription_status: str
    timezone: str
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminResponse(BaseModel):
    """Admin profile response"""
    id: int
    full_name: str
    email: str
    phone_number: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
