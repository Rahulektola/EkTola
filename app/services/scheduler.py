"""
Campaign Scheduler Service
Manages campaign execution scheduling and triggering
"""
import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.campaign import Campaign, CampaignRun
from app.utils.enums import CampaignStatus, RecurrenceType
from app.tasks.campaign_tasks import execute_campaign_run

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """Service for scheduling and triggering campaign execution"""
    
    def __init__(self):
        self.db: Session = SessionLocal()
    
    def check_and_trigger_campaigns(self) -> int:
        """
        Check for campaigns that should run now and trigger them
        
        Returns:
            int: Number of campaigns triggered
        """
        try:
            now = datetime.utcnow()
            triggered_count = 0
            
            # Find active campaigns ready to execute
            campaigns = self.db.query(Campaign).filter(
                Campaign.status == CampaignStatus.ACTIVE,
                Campaign.start_date <= now
            ).all()
            
            logger.info(f"🔍 Checking {len(campaigns)} active campaigns")
            
            for campaign in campaigns:
                if self._should_execute_campaign(campaign, now):
                    # Create campaign run
                    campaign_run = CampaignRun(
                        campaign_id=campaign.id,
                        scheduled_at=now,
                        status=CampaignStatus.PENDING
                    )
                    self.db.add(campaign_run)
                    self.db.commit()
                    self.db.refresh(campaign_run)
                    
                    # Trigger execution via Celery
                    execute_campaign_run.delay(campaign_run.id)
                    
                    logger.info(f"✅ Triggered campaign '{campaign.name}' (Run ID: {campaign_run.id})")
                    triggered_count += 1
            
            return triggered_count
            
        except Exception as e:
            logger.error(f"❌ Error in campaign scheduler: {str(e)}")
            raise
        finally:
            self.db.close()
    
    def _should_execute_campaign(self, campaign: Campaign, now: datetime) -> bool:
        """
        Determine if a campaign should execute now
        
        Args:
            campaign: Campaign to check
            now: Current datetime
            
        Returns:
            bool: True if campaign should execute
        """
        # Check if campaign is within execution window
        if campaign.end_date and now > campaign.end_date:
            # Campaign expired - mark as completed
            campaign.status = CampaignStatus.COMPLETED
            self.db.commit()
            return False
        
        # One-time campaigns
        if campaign.recurrence_type == RecurrenceType.ONCE:
            # Check if already executed
            existing_run = self.db.query(CampaignRun).filter(
                CampaignRun.campaign_id == campaign.id,
                CampaignRun.status.in_([CampaignStatus.COMPLETED, CampaignStatus.RUNNING])
            ).first()
            
            return existing_run is None
        
        # Recurring campaigns - check if already executed in current period
        return not self._has_run_in_current_period(campaign, now)
    
    def _has_run_in_current_period(self, campaign: Campaign, now: datetime) -> bool:
        """
        Check if campaign has already run in the current recurrence period
        
        Args:
            campaign: Campaign to check
            now: Current datetime
            
        Returns:
            bool: True if already ran in current period
        """
        from datetime import timedelta
        
        if campaign.recurrence_type == RecurrenceType.DAILY:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif campaign.recurrence_type == RecurrenceType.WEEKLY:
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif campaign.recurrence_type == RecurrenceType.MONTHLY:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return False
        
        # Check for existing run in this period
        existing_run = self.db.query(CampaignRun).filter(
            CampaignRun.campaign_id == campaign.id,
            CampaignRun.scheduled_at >= period_start,
            CampaignRun.status.in_([CampaignStatus.COMPLETED, CampaignStatus.RUNNING])
        ).first()
        
        return existing_run is not None


# Singleton instance
campaign_scheduler = CampaignScheduler()
