from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, Integer, text
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.core.dependencies import get_current_jeweller, get_current_admin
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.models.campaign import Campaign, CampaignRun
from app.models.message import Message
from app.schemas.analytics import (
    JewellerDashboardResponse, AdminDashboardResponse, AdminAnalyticsResponse,
    JewellerUsageStats, LanguageDistribution, CampaignTypeDistribution
)
from app.schemas.contact import ContactSegmentStats
from app.schemas.campaign import CampaignStatsResponse
from app.schemas.message import FailureBreakdown
from app.utils.enums import MessageStatus, CampaignStatus

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ============ Jeweller Dashboard ============

@router.get("/dashboard", response_model=JewellerDashboardResponse)
def get_jeweller_dashboard(
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get jeweller's dashboard analytics"""
    # Total contacts
    total_contacts = db.query(func.count(Contact.id)).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).scalar()
    
    # Opted out contacts
    opted_out = db.query(func.count(Contact.id)).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.opted_out == True,
        Contact.is_deleted == False
    ).scalar()
    
    # Active campaigns
    active_campaigns = db.query(func.count(Campaign.id)).filter(
        Campaign.jeweller_id == current_jeweller.id,
        Campaign.status == CampaignStatus.ACTIVE
    ).scalar()
    
    # Total messages sent
    total_messages = db.query(func.count(Message.id)).filter(
        Message.jeweller_id == current_jeweller.id
    ).scalar()
    
    # Last 30 days stats
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_stats = db.query(
        func.count(Message.id).label('total'),
        func.sum(func.cast(Message.status == MessageStatus.DELIVERED, Integer)).label('delivered'),
        func.sum(func.cast(Message.status == MessageStatus.READ, Integer)).label('read')
    ).filter(
        Message.jeweller_id == current_jeweller.id,
        Message.created_at >= thirty_days_ago
    ).first()
    
    recent_total = recent_stats.total or 0
    recent_delivered = recent_stats.delivered or 0
    recent_read = recent_stats.read or 0
    recent_delivery_rate = (recent_delivered / recent_total * 100) if recent_total > 0 else 0
    recent_read_rate = (recent_read / recent_delivered * 100) if recent_delivered > 0 else 0
    
    # Contact distribution by segment
    contact_dist = db.query(
        Contact.segment,
        func.count(Contact.id).label('count'),
        func.sum(func.cast(Contact.opted_out, Integer)).label('opted_out_count')
    ).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).group_by(Contact.segment).all()
    
    # Recent campaign runs (top 5)
    recent_runs = db.query(CampaignRun).filter(
        CampaignRun.jeweller_id == current_jeweller.id,
        CampaignRun.status == "COMPLETED"
    ).order_by(CampaignRun.completed_at.desc()).limit(5).all()
    
    campaign_stats = []
    for run in recent_runs:
        campaign = db.query(Campaign).filter(Campaign.id == run.campaign_id).first()
        if campaign:
            delivery_rate = (run.messages_delivered / run.messages_sent * 100) if run.messages_sent > 0 else 0
            read_rate = (run.messages_read / run.messages_delivered * 100) if run.messages_delivered > 0 else 0
            
            campaign_stats.append(CampaignStatsResponse(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                total_runs=1,
                total_messages_sent=run.messages_sent,
                total_delivered=run.messages_delivered,
                total_read=run.messages_read,
                total_failed=run.messages_failed,
                delivery_rate=round(delivery_rate, 2),
                read_rate=round(read_rate, 2),
                last_run_at=run.completed_at,
                next_run_at=None
            ))
    
    return JewellerDashboardResponse(
        total_contacts=total_contacts,
        opted_out_contacts=opted_out,
        active_campaigns=active_campaigns,
        total_messages_sent=total_messages,
        recent_delivery_rate=round(recent_delivery_rate, 2),
        recent_read_rate=round(recent_read_rate, 2),
        contact_distribution=[
            ContactSegmentStats(
                segment=dist.segment,
                count=dist.count,
                opted_out_count=dist.opted_out_count or 0
            )
            for dist in contact_dist
        ],
        recent_campaign_runs=campaign_stats
    )


# ============ Admin Dashboard ============

@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin cross-jeweller dashboard"""
    # Total jewellers
    total_jewellers = db.query(func.count(Jeweller.id)).scalar()
    
    # Active jewellers (approved and active)
    active_jewellers = db.query(func.count(Jeweller.id)).filter(
        Jeweller.is_approved == True,
        Jeweller.is_active == True
    ).scalar()
    
    # Total contacts across all jewellers
    total_contacts = db.query(func.count(Contact.id)).filter(
        Contact.is_deleted == False
    ).scalar()
    
    # Total messages - use COUNT(*) to avoid loading model columns
    total_messages = db.execute(text("SELECT COUNT(*) FROM messages")).scalar() or 0
    
    # Messages last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    messages_30d = db.execute(text("SELECT COUNT(*) FROM messages WHERE created_at >= :date"), {"date": thirty_days_ago}).scalar() or 0
    
    # Overall delivery and read rates - use raw SQL to avoid model column issues
    overall_delivered = db.execute(text("SELECT COUNT(*) FROM messages WHERE status = 'DELIVERED'")).scalar() or 0
    overall_read = db.execute(text("SELECT COUNT(*) FROM messages WHERE status = 'READ'")).scalar() or 0
    overall_delivery_rate = (overall_delivered / total_messages * 100) if total_messages > 0 else 0
    overall_read_rate = (overall_read / overall_delivered * 100) if overall_delivered > 0 else 0
    
    # Per-jeweller stats
    jeweller_stats = []
    jewellers = db.query(Jeweller).all()
    
    for jeweller in jewellers:
        j_contacts = db.query(func.count(Contact.id)).filter(
            Contact.jeweller_id == jeweller.id,
            Contact.is_deleted == False
        ).scalar()
        
        j_campaigns = db.query(func.count(Campaign.id)).filter(
            Campaign.jeweller_id == jeweller.id
        ).scalar()
        
        # Use raw SQL for messages to avoid model column issues
        j_messages = db.execute(text("SELECT COUNT(*) FROM messages WHERE jeweller_id = :jid"), {"jid": jeweller.id}).scalar() or 0
        
        j_messages_30d = db.execute(text("SELECT COUNT(*) FROM messages WHERE jeweller_id = :jid AND created_at >= :date"), 
                                    {"jid": jeweller.id, "date": thirty_days_ago}).scalar() or 0
        
        j_delivered = db.execute(text("SELECT COUNT(*) FROM messages WHERE jeweller_id = :jid AND status = 'DELIVERED'"), 
                                {"jid": jeweller.id}).scalar() or 0
        j_read = db.execute(text("SELECT COUNT(*) FROM messages WHERE jeweller_id = :jid AND status = 'READ'"), 
                           {"jid": jeweller.id}).scalar() or 0
        
        j_delivery_rate = (j_delivered / j_messages * 100) if j_messages > 0 else 0
        j_read_rate = (j_read / j_delivered * 100) if j_delivered > 0 else 0
        
        # Last active (last message sent) - use raw SQL
        last_message_time = db.execute(text("SELECT MAX(created_at) FROM messages WHERE jeweller_id = :jid"), 
                                     {"jid": jeweller.id}).scalar()
        
        jeweller_stats.append(JewellerUsageStats(
            jeweller_id=jeweller.id,
            business_name=jeweller.business_name,
            total_contacts=j_contacts,
            total_campaigns=j_campaigns,
            total_messages_sent=j_messages,
            messages_last_30_days=j_messages_30d,
            delivery_rate=round(j_delivery_rate, 2),
            read_rate=round(j_read_rate, 2),
            last_active=last_message_time
        ))
    
    return AdminDashboardResponse(
        total_jewellers=total_jewellers,
        active_jewellers=active_jewellers,
        total_contacts_across_jewellers=total_contacts,
        total_messages_sent=total_messages,
        messages_last_30_days=messages_30d,
        overall_delivery_rate=round(overall_delivery_rate, 2),
        overall_read_rate=round(overall_read_rate, 2),
        jeweller_stats=jeweller_stats
    )


@router.get("/admin/detailed", response_model=AdminAnalyticsResponse)
def get_admin_detailed_analytics(
    days: int = Query(30, ge=1, le=365),
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed admin analytics with breakdowns"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total messages in period
    total_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= start_date
    ).scalar()
    
    # Language distribution
    lang_dist = db.query(
        Message.language,
        func.count(Message.id).label('count')
    ).filter(
        Message.created_at >= start_date
    ).group_by(Message.language).all()
    
    language_distribution = [
        LanguageDistribution(
            language=dist.language.value,
            message_count=dist.count,
            percentage=round((dist.count / total_messages * 100) if total_messages > 0 else 0, 2)
        )
        for dist in lang_dist
    ]
    
    # Campaign type distribution
    campaign_dist = db.query(
        Campaign.campaign_type,
        func.count(Campaign.id).label('count')
    ).group_by(Campaign.campaign_type).all()
    
    total_campaigns = sum(dist.count for dist in campaign_dist)
    campaign_type_distribution = [
        CampaignTypeDistribution(
            campaign_type=dist.campaign_type.value,
            count=dist.count,
            percentage=round((dist.count / total_campaigns * 100) if total_campaigns > 0 else 0, 2)
        )
        for dist in campaign_dist
    ]
    
    # Failure breakdown
    failure_breakdown = db.query(
        Message.failure_reason,
        func.count(Message.id).label('count')
    ).filter(
        Message.status == MessageStatus.FAILED,
        Message.created_at >= start_date,
        Message.failure_reason.isnot(None)
    ).group_by(Message.failure_reason).all()
    
    failure_list = [
        FailureBreakdown(
            failure_reason=fb.failure_reason,
            count=fb.count
        )
        for fb in failure_breakdown
    ]
    
    # Daily message volume
    daily_volume = db.query(
        func.date(Message.created_at).label('date'),
        func.count(Message.id).label('count')
    ).filter(
        Message.created_at >= start_date
    ).group_by(func.date(Message.created_at)).all()
    
    daily_message_volume = [
        {"date": dv.date.strftime("%Y-%m-%d"), "count": dv.count}
        for dv in daily_volume
    ]
    
    return AdminAnalyticsResponse(
        total_messages=total_messages,
        language_distribution=language_distribution,
        campaign_type_distribution=campaign_type_distribution,
        failure_breakdown=failure_list,
        daily_message_volume=daily_message_volume
    )
