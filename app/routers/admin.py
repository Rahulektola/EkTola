from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.jeweller import Jeweller
from app.core.dependencies import get_current_admin
from app.schemas.auth import JewellerResponse, UserResponse
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/jewellers/pending", response_model=List[JewellerResponse])
def get_pending_jewellers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get all jewellers pending approval
    Admin access required
    """
    pending_jewellers = db.query(Jeweller).filter(
        Jeweller.is_approved == False
    ).all()
    
    return pending_jewellers


@router.get("/jewellers", response_model=List[JewellerResponse])
def get_all_jewellers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get all jewellers (approved and pending)
    Admin access required
    """
    jewellers = db.query(Jeweller).all()
    return jewellers


@router.post("/jewellers/{jeweller_id}/approve", response_model=JewellerResponse)
def approve_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Approve a jeweller account
    Admin access required
    """
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    if jeweller.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeweller is already approved"
        )
    
    # Approve the jeweller
    jeweller.is_approved = True
    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)
    
    return jeweller


@router.post("/jewellers/{jeweller_id}/reject", response_model=JewellerResponse)
def reject_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Reject/revoke approval for a jeweller account
    Admin access required
    """
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    # Reject/revoke approval
    jeweller.is_approved = False
    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)
    
    return jeweller


@router.delete("/jewellers/{jeweller_id}")
def delete_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Delete a jeweller account and associated user
    Admin access required
    """
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    # Delete jeweller (will cascade to contacts and campaigns)
    user_id = jeweller.user_id
    db.delete(jeweller)
    
    # Delete associated user
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
    
    db.commit()
    
    return {
        "message": "Jeweller deleted successfully",
        "jeweller_id": jeweller_id
    }
