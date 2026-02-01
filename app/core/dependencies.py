from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_token
from app.models.jeweller import Jeweller
from app.models.admin import Admin
from typing import Union

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Union[Jeweller, Admin]:
    """
    Dependency to get current authenticated user (Jeweller or Admin) from JWT token
    Token should be in Authorization header: Bearer <token>
    
    Returns either Jeweller or Admin instance based on user_type in token
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_type = payload.get("type")
    user_id_str = payload.get("sub")
    
    if not user_type or not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user based on type
    if user_type == "jeweller":
        user = db.query(Jeweller).filter(Jeweller.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Jeweller not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Jeweller account is inactive"
            )
    elif user_type == "admin":
        user = db.query(Admin).filter(Admin.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is inactive"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_jeweller(
    current_user: Union[Jeweller, Admin] = Depends(get_current_user)
) -> Jeweller:
    """
    Dependency to ensure current user is a Jeweller
    Raises 403 if user is not a jeweller
    """
    if not isinstance(current_user, Jeweller):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Jeweller access required"
        )
    
    if not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval"
        )
    
    return current_user


def get_current_admin(
    current_user: Union[Jeweller, Admin] = Depends(get_current_user)
) -> Admin:
    """
    Dependency to ensure current user is an Admin
    Raises 403 if user is not an admin
    """
    if not isinstance(current_user, Admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
