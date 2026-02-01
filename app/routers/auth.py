from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    AdminRegisterRequest, LoginRequest, PhoneLoginRequest, OTPLoginRequest, 
    PhoneOTPRequest, OTPVerifyRequest, PhoneOTPVerifyRequest, RegisterRequest,
    Token, UserResponse, JewellerResponse
)
from app.config import settings
from app.models.user import User
from app.models.jeweller import Jeweller
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.dependencies import get_current_user, create_token_data
from app.utils.whatsapp import send_whatsapp_otp, validate_phone_number, normalize_phone_number
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_jeweller(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new jeweller account
    Returns JWT tokens after successful registration
    """
    # Normalize and validate phone number format
    normalized_phone = normalize_phone_number(request.phone_number)
    if not validate_phone_number(normalized_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format. Use 10 digits or +91 format"
        )
    
    # Check if phone already exists
    existing_user = db.query(User).filter(User.phone_number == normalized_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Check if email exists (optional field)
    if request.email:
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create user with phone as primary identifier
    hashed_password = get_password_hash(request.password)
    new_user = User(
        phone_number=normalized_phone,
        email=request.email,
        hashed_password=hashed_password,
        is_admin=False,
        is_active=True
    )
    db.add(new_user)
    db.flush()  # Get user.id
    
    # Create jeweller profile
    new_jeweller = Jeweller(
        user_id=new_user.id,
        business_name=request.business_name,
        phone_number=normalized_phone,
        is_approved=False,  # Requires admin approval
        is_active=True
    )
    db.add(new_jeweller)
    db.commit()
    db.refresh(new_user)
    db.refresh(new_jeweller)
    
    # Generate tokens
    token_data = create_token_data(new_user, new_jeweller)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)



@router.post("/register-admin", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_admin(
    request: AdminRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new admin account
    Requires valid access code
    """
    # Verify access code
    if request.access_code != settings.ADMIN_ACCESS_CODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid access code"
        )
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create admin user
    hashed_password = get_password_hash(request.password)
    new_user = User(
        email=request.email,
        hashed_password=hashed_password,
        is_admin=True,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate tokens
    token_data = create_token_data(new_user, None)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password (Admin)
    Returns JWT tokens
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Get jeweller if exists
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == user.id).first()
    
    # Generate tokens
    token_data = create_token_data(user, jeweller)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login/phone", response_model=Token)
def login_with_phone(
    request: PhoneLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with phone number and password (Jeweller)
    Returns JWT tokens
    """
    # Normalize and validate phone format
    normalized_phone = normalize_phone_number(request.phone_number)
    if not validate_phone_number(normalized_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    user = db.query(User).filter(User.phone_number == normalized_phone).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Get jeweller profile
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == user.id).first()
    
    # Generate tokens
    token_data = create_token_data(user, jeweller)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/otp/request")
def request_otp(
    request: OTPLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Request OTP for email-based login (Admin)
    Sends OTP to user's email (implementation needed)
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate 6-digit OTP
    otp_code = str(secrets.randbelow(900000) + 100000)
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    
    user.phone_otp_code = otp_code
    user.phone_otp_expiry = otp_expiry
    db.commit()
    
    # TODO: Send OTP via email service
    # For development, return OTP (remove in production)
    return {"message": "OTP sent to email", "otp": otp_code}


@router.post("/otp/request/phone")
async def request_phone_otp(
    request: PhoneOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Request OTP via WhatsApp (Jeweller)
    Sends OTP to user's WhatsApp number
    """
    # Normalize and validate phone format
    normalized_phone = normalize_phone_number(request.phone_number)
    if not validate_phone_number(normalized_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format. Use 10 digits or +91 format"
        )
    
    user = db.query(User).filter(User.phone_number == normalized_phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered"
        )
    
    # Generate 6-digit OTP
    otp_code = str(secrets.randbelow(900000) + 100000)
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    
    # Send OTP via WhatsApp
    result = await send_whatsapp_otp(normalized_phone, otp_code)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {result.get('error', 'Unknown error')}"
        )
    
    # Store OTP in database
    user.phone_otp_code = otp_code
    user.phone_otp_expiry = otp_expiry
    db.commit()
    
    # Return response (include OTP in dev mode only)
    response = {"message": "OTP sent to WhatsApp"}
    if settings.ENVIRONMENT == "development" and result.get("otp"):
        response["otp"] = otp_code  # For testing in dev mode
    
    return response


@router.post("/otp/verify", response_model=Token)
def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and login (Email - Admin)
    Returns JWT tokens on success
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.phone_otp_code or user.phone_otp_code != request.otp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP"
        )
    
    if user.phone_otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP expired"
        )
    
    # Clear OTP
    user.phone_otp_code = None
    user.phone_otp_expiry = None
    db.commit()
    
    # Get jeweller if exists
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == user.id).first()
    
    # Generate tokens
    token_data = create_token_data(user, jeweller)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/otp/verify/phone", response_model=Token)
def verify_phone_otp(
    request: PhoneOTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify WhatsApp OTP and login (Jeweller)
    Returns JWT tokens on success
    """
    # Normalize and validate phone format
    normalized_phone = normalize_phone_number(request.phone_number)
    if not validate_phone_number(normalized_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    user = db.query(User).filter(User.phone_number == normalized_phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered"
        )
    
    if not user.phone_otp_code or user.phone_otp_code != request.otp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP"
        )
    
    if user.phone_otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP expired"
        )
    
    # Clear OTP
    user.phone_otp_code = None
    user.phone_otp_expiry = None
    db.commit()
    
    # Get jeweller profile
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == user.id).first()
    
    # Generate tokens
    token_data = create_token_data(user, jeweller)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.get("/me/jeweller", response_model=JewellerResponse)
def get_current_jeweller_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current jeweller profile"""
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == current_user.id).first()
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller profile not found"
        )
    return jeweller

