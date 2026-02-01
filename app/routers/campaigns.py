from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.core.dependencies import get_current_jeweller
from app.models.jeweller import Jeweller
from app.models.campaign import Campaign, CampaignRun
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignListResponse, CampaignRunResponse, CampaignStatsResponse
)
from app.utils.enums import CampaignType, CampaignStatus
from datetime import datetime

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    request: CampaignCreate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Create new campaign"""
    # Validate: UTILITY campaigns require sub_segment
    if request.campaign_type == CampaignType.UTILITY and not request.sub_segment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sub_segment is required for UTILITY campaigns"
        )
    
    # Create campaign
    new_campaign = Campaign(
        jeweller_id=current_jeweller.id,
        timezone=current_jeweller.timezone,
        **request.model_dump()
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    
    return new_campaign


@router.get("/", response_model=CampaignListResponse)
def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[CampaignStatus] = None,
    campaign_type: Optional[CampaignType] = None,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """List jeweller's campaigns"""
    query = db.query(Campaign).filter(
        Campaign.jeweller_id == current_jeweller.id
    )
    
    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    if campaign_type:
        query = query.filter(Campaign.campaign_type == campaign_type)
    
    total = query.count()
    campaigns = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return CampaignListResponse(
        campaigns=campaigns,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get campaign details"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    request: CampaignUpdate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Update campaign (affects future runs only)"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
def pause_campaign(
    campaign_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Pause an active campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ACTIVE campaigns can be paused"
        )
    
    campaign.status = CampaignStatus.PAUSED
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
def resume_campaign(
    campaign_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Resume a paused campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PAUSED campaigns can be resumed"
        )
    
    campaign.status = CampaignStatus.ACTIVE
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.post("/{campaign_id}/activate", response_model=CampaignResponse)
def activate_campaign(
    campaign_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Activate a draft campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT campaigns can be activated"
        )
    
    campaign.status = CampaignStatus.ACTIVE
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.get("/{campaign_id}/runs", response_model=List[CampaignRunResponse])
def get_campaign_runs(
    campaign_id: int,
    limit: int = Query(10, ge=1, le=100),
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get campaign run history"""
    # Verify campaign ownership
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    runs = db.query(CampaignRun).filter(
        CampaignRun.campaign_id == campaign_id
    ).order_by(CampaignRun.scheduled_at.desc()).limit(limit).all()
    
    return runs


@router.get("/{campaign_id}/stats", response_model=CampaignStatsResponse)
def get_campaign_stats(
    campaign_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get campaign performance statistics"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Aggregate stats from campaign runs
    from sqlalchemy import func
    stats = db.query(
        func.count(CampaignRun.id).label('total_runs'),
        func.sum(CampaignRun.messages_sent).label('total_sent'),
        func.sum(CampaignRun.messages_delivered).label('total_delivered'),
        func.sum(CampaignRun.messages_read).label('total_read'),
        func.sum(CampaignRun.messages_failed).label('total_failed'),
        func.max(CampaignRun.completed_at).label('last_run')
    ).filter(
        CampaignRun.campaign_id == campaign_id
    ).first()
    
    total_sent = stats.total_sent or 0
    total_delivered = stats.total_delivered or 0
    total_read = stats.total_read or 0
    
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
    read_rate = (total_read / total_delivered * 100) if total_delivered > 0 else 0
    
    # Get next scheduled run
    next_run = db.query(CampaignRun).filter(
        CampaignRun.campaign_id == campaign_id,
        CampaignRun.status == "PENDING",
        CampaignRun.scheduled_at > datetime.utcnow()
    ).order_by(CampaignRun.scheduled_at).first()
    
    return CampaignStatsResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        total_runs=stats.total_runs or 0,
        total_messages_sent=total_sent,
        total_delivered=total_delivered,
        total_read=total_read,
        total_failed=stats.total_failed or 0,
        delivery_rate=round(delivery_rate, 2),
        read_rate=round(read_rate, 2),
        last_run_at=stats.last_run,
        next_run_at=next_run.scheduled_at if next_run else None
    )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Delete campaign (only if DRAFT or COMPLETED)"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.jeweller_id == current_jeweller.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status in [CampaignStatus.ACTIVE, CampaignStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete ACTIVE or PAUSED campaigns. Pause first."
        )
    
    db.delete(campaign)
    db.commit()
    
    return None
