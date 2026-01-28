from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    LoginRequest, OTPLoginRequest, OTPVerifyRequest, RegisterRequest,
    Token, UserResponse, JewellerResponse
)
from app.models.user import User
from app.models.jeweller import Jeweller
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.dependencies import get_current_user, create_token_data
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
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(request.password)
    new_user = User(
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
        phone_number=request.phone_number,
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


@router.post("/login", response_model=Token)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password
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


@router.post("/otp/request")
def request_otp(
    request: OTPLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Request OTP for email-based login
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
    
    user.otp_code = otp_code
    user.otp_expiry = otp_expiry
    db.commit()
    
    # TODO: Send OTP via email service
    # For development, return OTP (remove in production)
    return {"message": "OTP sent to email", "otp": otp_code}


@router.post("/otp/verify", response_model=Token)
def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and login
    Returns JWT tokens on success
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.otp_code or user.otp_code != request.otp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP"
        )
    
    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP expired"
        )
    
    # Clear OTP
    user.otp_code = None
    user.otp_expiry = None
    db.commit()
    
    # Get jeweller if exists
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == user.id).first()
    
    # Generate tokens
    token_data = create_token_data(user, jeweller)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    Request body: {"refresh_token": "..."}
    """
    refresh_token = request.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required"
        )
    
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Get jeweller if exists
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == user.id).first()
    
    # Generate new tokens
    token_data = create_token_data(user, jeweller)
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=new_refresh_token)


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
