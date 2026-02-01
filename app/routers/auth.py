"""
Authentication Router

Handles authentication for:
- Jewellers (WhatsApp OTP)
- Admins (Email/Password)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..schemas.auth import (
    OTPRequest, OTPVerify, JewellerSignup,
    AdminLogin, CreateAdminRequest,
    Token, JewellerResponse, AdminResponse
)
from ..models.jeweller import Jeweller
from ..models.admin import Admin
from ..services.otp_service import OTPService
from ..core.security import verify_password, get_password_hash, create_access_token
from ..core.dependencies import get_current_admin, get_current_jeweller
from ..config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


# ============ JEWELLER AUTHENTICATION (WhatsApp OTP) ============

@router.post("/jeweller/signup/request-otp")
async def request_signup_otp(
    request: OTPRequest,
    db: Session = Depends(get_db)
):
    """
    Request OTP for new jeweller registration
    
    Step 1 of jeweller signup flow. OTP will be sent via WhatsApp.
    Valid for 10 minutes, maximum 3 attempts.
    """
    # Check if phone number is already registered
    existing = db.query(Jeweller).filter(
        Jeweller.phone_number == request.phone_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    otp_service = OTPService(db)
    result = await otp_service.send_signup_otp(request.phone_number)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {
        "success": True,
        "message": result["message"],
        "expires_in_minutes": result.get("expires_in_minutes", 10)
    }


@router.post("/jeweller/signup/verify-and-register", response_model=Token)
async def verify_signup_and_register(
    signup_data: JewellerSignup,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and complete jeweller registration
    
    Step 2 of jeweller signup flow. Creates jeweller account pending admin approval.
    """
    # Verify OTP
    otp_service = OTPService(db)
    result = otp_service.verify_signup_otp(signup_data.phone_number, signup_data.otp_code)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    # Check if phone already registered (double-check)
    existing = db.query(Jeweller).filter(
        Jeweller.phone_number == signup_data.phone_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Check email uniqueness if provided
    if signup_data.email:
        existing_email = db.query(Jeweller).filter(
            Jeweller.email == signup_data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create jeweller account (pending admin approval)
    new_jeweller = Jeweller(
        business_name=signup_data.business_name,
        owner_name=signup_data.owner_name,
        email=signup_data.email,
        phone_number=signup_data.phone_number,
        whatsapp_business_account_id=signup_data.whatsapp_business_account_id,
        whatsapp_phone_number_id=signup_data.whatsapp_phone_number_id,
        address=signup_data.address,
        is_verified=True,  # Phone verified via OTP
        is_approved=False,  # Requires admin approval
        is_active=False,    # Will be activated upon approval
        subscription_status="trial"  # Start with trial
    )
    
    db.add(new_jeweller)
    db.commit()
    db.refresh(new_jeweller)
    
    logger.info(f"New jeweller registered: {signup_data.business_name} ({signup_data.phone_number})")
    
    # Generate access token (even though not approved, allows them to check status)
    access_token = create_access_token(
        data={
            "sub": str(new_jeweller.id),
            "type": "jeweller",
            "phone": new_jeweller.phone_number
        },
        expires_delta=timedelta(days=30)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_type="jeweller",
        user_data={
            "id": new_jeweller.id,
            "business_name": new_jeweller.business_name,
            "phone_number": new_jeweller.phone_number,
            "is_approved": new_jeweller.is_approved,
            "is_active": new_jeweller.is_active
        }
    )


@router.post("/jeweller/login/request-otp")
async def request_login_otp(
    request: OTPRequest,
    db: Session = Depends(get_db)
):
    """
    Request OTP for jeweller login
    
    Step 1 of jeweller login flow. Sends OTP via WhatsApp.
    """
    # Check if jeweller exists
    jeweller = db.query(Jeweller).filter(
        Jeweller.phone_number == request.phone_number
    ).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller account not found"
        )
    
    otp_service = OTPService(db)
    result = await otp_service.send_login_otp(request.phone_number)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {
        "success": True,
        "message": result["message"],
        "expires_in_minutes": result.get("expires_in_minutes", 10)
    }


@router.post("/jeweller/login/verify-otp", response_model=Token)
async def verify_login_otp(
    request: OTPVerify,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and login jeweller
    
    Step 2 of jeweller login flow. Returns JWT access token.
    """
    otp_service = OTPService(db)
    result = otp_service.verify_otp(request.phone_number, request.otp_code)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    jeweller = result.get("jeweller")
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller account not found"
        )
    
    # Update last login
    jeweller.last_login = datetime.utcnow()
    db.commit()
    
    logger.info(f"Jeweller logged in: {jeweller.business_name} ({jeweller.phone_number})")
    
    # Create access token (30 days for convenience)
    access_token = create_access_token(
        data={
            "sub": str(jeweller.id),
            "type": "jeweller",
            "phone": jeweller.phone_number
        },
        expires_delta=timedelta(days=30)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_type="jeweller",
        user_data={
            "id": jeweller.id,
            "business_name": jeweller.business_name,
            "phone_number": jeweller.phone_number,
            "email": jeweller.email,
            "is_verified": jeweller.is_verified,
            "is_approved": jeweller.is_approved,
            "is_active": jeweller.is_active,
            "subscription_status": jeweller.subscription_status
        }
    )


# ============ ADMIN AUTHENTICATION (Email/Password) ============

@router.post("/admin/login", response_model=Token)
def admin_login(
    credentials: AdminLogin,
    db: Session = Depends(get_db)
):
    """
    Admin login with email and password
    
    Token expires in 8 hours for security.
    """
    admin = db.query(Admin).filter(Admin.email == credentials.email).first()
    
    if not admin or not verify_password(credentials.password, admin.hashed_password):
        logger.warning(f"Failed admin login attempt: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last login
    admin.last_login = datetime.utcnow()
    db.commit()
    
    logger.info(f"Admin logged in: {admin.email}")
    
    # Create access token (8 hours for security)
    access_token = create_access_token(
        data={
            "sub": str(admin.id),
            "type": "admin",
            "email": admin.email
        },
        expires_delta=timedelta(hours=8)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_type="admin",
        user_data={
            "id": admin.id,
            "full_name": admin.full_name,
            "email": admin.email,
            "phone_number": admin.phone_number
        }
    )


@router.post("/admin/create-first-admin", response_model=AdminResponse)
def create_first_admin(
    admin_data: CreateAdminRequest,
    db: Session = Depends(get_db)
):
    """
    Create the first admin account (only works if no admins exist)
    
    This is a bootstrap endpoint for initial setup.
    Once an admin exists, use the admin panel to create more admins.
    """
    # Check if any admins exist
    existing_count = db.query(Admin).count()
    
    if existing_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts already exist. Use admin panel to create more admins."
        )
    
    # Check if email already exists (shouldn't happen, but check anyway)
    existing = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create first admin
    new_admin = Admin(
        full_name=admin_data.full_name,
        email=admin_data.email,
        phone_number=admin_data.phone_number,
        hashed_password=get_password_hash(admin_data.password),
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    logger.info(f"First admin created: {new_admin.email}")
    
    return new_admin


# ============ PROFILE ENDPOINTS ============

@router.get("/me/jeweller", response_model=JewellerResponse)
def get_jeweller_profile(
    current_jeweller: Jeweller = Depends(get_current_jeweller)
):
    """Get current jeweller profile"""
    return current_jeweller


@router.get("/me/admin", response_model=AdminResponse)
def get_admin_profile(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get current admin profile"""
    return current_admin
