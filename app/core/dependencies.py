from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.jeweller import Jeweller
from app.schemas.auth import TokenData

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    Token should be in Authorization header: Bearer <token>
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def get_current_jeweller(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Jeweller:
    """
    Dependency to get current jeweller from authenticated user
    Raises 403 if user is not a jeweller
    """
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot access jeweller endpoints"
        )
    
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == current_user.id).first()
    if jeweller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller profile not found"
        )
    
    if not jeweller.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Jeweller account pending approval"
        )
    
    if not jeweller.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Jeweller account is inactive"
        )
    
    return jeweller


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to verify current user is an admin
    Raises 403 if user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def create_token_data(user: User, jeweller: Jeweller = None) -> dict:
    """Create token payload data"""
    return {
        "user_id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "jeweller_id": jeweller.id if jeweller else None
    }
