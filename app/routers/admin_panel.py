"""
Admin Panel Router

Endpoints for platform admins to manage jewellers and other admins
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from ..database import get_db
from ..models.jeweller import Jeweller
from ..models.admin import Admin
from ..schemas.auth import CreateAdminRequest, JewellerResponse, AdminResponse
from ..core.dependencies import get_current_admin
from ..core.security import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Panel"]
)


@router.get("/jewellers/pending", response_model=List[JewellerResponse])
async def get_pending_jewellers(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all jewellers awaiting approval"""
    jewellers = db.query(Jeweller).filter(
        Jeweller.is_approved == False
    ).all()
    
    return jewellers


@router.get("/jewellers/all", response_model=List[JewellerResponse])
async def get_all_jewellers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all jewellers with pagination"""
    jewellers = db.query(Jeweller).offset(skip).limit(limit).all()
    return jewellers


@router.post("/jewellers/{jeweller_id}/approve")
async def approve_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Approve a jeweller's account"""
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    jeweller.is_approved = True
    jeweller.is_active = True
    jeweller.subscription_status = "trial"
    db.commit()
    
    logger.info(f"Admin {current_admin.email} approved jeweller {jeweller.business_name}")
    
    return {
        "success": True,
        "message": f"Jeweller {jeweller.business_name} approved successfully"
    }


@router.post("/jewellers/{jeweller_id}/reject")
async def reject_jeweller(
    jeweller_id: int,
    reason: str = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Reject a jeweller's account"""
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    # Delete the jeweller account
    db.delete(jeweller)
    db.commit()
    
    logger.info(f"Admin {current_admin.email} rejected jeweller {jeweller.business_name}. Reason: {reason}")
    
    return {
        "success": True,
        "message": f"Jeweller {jeweller.business_name} rejected"
    }


@router.post("/jewellers/{jeweller_id}/activate")
async def activate_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Activate a jeweller's account"""
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    jeweller.is_active = True
    if jeweller.subscription_status == "suspended":
        jeweller.subscription_status = "active"
    db.commit()
    
    logger.info(f"Admin {current_admin.email} activated jeweller {jeweller.business_name}")
    
    return {
        "success": True,
        "message": f"Jeweller {jeweller.business_name} activated"
    }


@router.post("/jewellers/{jeweller_id}/deactivate")
async def deactivate_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Deactivate a jeweller's account"""
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    
    jeweller.is_active = False
    jeweller.subscription_status = "suspended"
    db.commit()
    
    logger.info(f"Admin {current_admin.email} deactivated jeweller {jeweller.business_name}")
    
    return {
        "success": True,
        "message": f"Jeweller {jeweller.business_name} deactivated"
    }


@router.post("/admins/create", response_model=AdminResponse)
async def create_admin(
    admin_data: CreateAdminRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create a new admin (only admins can create other admins)"""
    # Check if email already exists
    existing_admin = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone number already exists
    if admin_data.phone_number:
        existing_phone = db.query(Admin).filter(
            Admin.phone_number == admin_data.phone_number
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # Create new admin
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
    
    logger.info(f"Admin {current_admin.email} created new admin {new_admin.email}")
    
    return new_admin


@router.get("/admins/all", response_model=List[AdminResponse])
async def get_all_admins(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all admins"""
    admins = db.query(Admin).all()
    return admins
