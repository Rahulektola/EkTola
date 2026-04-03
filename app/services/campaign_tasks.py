"""
Celery Tasks for Campaign Execution
Background jobs for sending WhatsApp messages
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session, joinedload

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.campaign import Campaign, CampaignRun
from app.models.message import Message
from app.models.contact import Contact
from app.models.template import Template
from app.utils.enums import CampaignStatus, MessageStatus, CampaignType, RecurrenceType
from app.services.whatsapp_service import whatsapp_service
from app.services.base_task import DatabaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=DatabaseTask, name='app.services.campaign_tasks.execute_campaign_run')
def execute_campaign_run(self, campaign_run_id: int):
    """
    Execute a campaign run - send messages to all target contacts
    
    Args:
        campaign_run_id: ID of the campaign run to execute
    """
    db = self.db
    
    try:
        # Get campaign run with campaign eagerly loaded (1 query instead of 2)
        campaign_run = db.query(CampaignRun).options(
            joinedload(CampaignRun.campaign)
        ).filter(
            CampaignRun.id == campaign_run_id
        ).first()
        
        if not campaign_run:
            logger.error(f"❌ Campaign run {campaign_run_id} not found")
            return
        
        campaign = campaign_run.campaign  # No extra query — already loaded via JOIN
        
        if not campaign:
            logger.error(f"❌ Campaign {campaign_run.campaign_id} not found")
            return
        
        logger.info(f"🚀 Starting campaign run {campaign_run_id} for campaign '{campaign.name}'")
        
        # Update run status
        campaign_run.status = CampaignStatus.RUNNING
        campaign_run.started_at = datetime.utcnow()
        db.commit()
        
        # Get target contacts based on segment
        query = db.query(Contact).filter(
            Contact.jeweller_id == campaign.jeweller_id,
            Contact.is_deleted == False
        )
        
        if campaign.target_segment:
            query = query.filter(Contact.segment == campaign.target_segment)
        
        contacts = query.all()
        
        if not contacts:
            logger.warning(f"⚠️ No contacts found for campaign {campaign.id}")
            campaign_run.status = CampaignStatus.COMPLETED
            campaign_run.completed_at = datetime.utcnow()
            campaign_run.total_sent = 0
            db.commit()
            return
        
        logger.info(f"📋 Found {len(contacts)} contacts to message")
        
        # Create message records in batch and queue sending tasks
        sent_count = 0
        failed_count = 0
        messages = []
        
        for contact in contacts:
            # Create message record
            message = Message(
                campaign_id=campaign.id,
                contact_id=contact.id,
                jeweller_id=campaign.jeweller_id,
                template_id=campaign.template_id,
                phone_number=contact.phone_number,
                status=MessageStatus.PENDING,
                scheduled_at=datetime.utcnow()
            )
            db.add(message)
            messages.append(message)
            sent_count += 1
        
        # Single batch commit for all messages instead of per-message commit
        db.commit()
        
        # Queue message sending tasks after commit (so IDs are available)
        for message in messages:
            send_campaign_message.delay(message.id)
        
        # Update campaign run statistics
        campaign_run.total_sent = sent_count
        campaign_run.total_failed = failed_count
        campaign_run.status = CampaignStatus.COMPLETED
        campaign_run.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Campaign run {campaign_run_id} completed: {sent_count} queued, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"❌ Error executing campaign run {campaign_run_id}: {str(e)}")
        
        # Mark campaign run as failed
        if campaign_run:
            campaign_run.status = CampaignStatus.FAILED
            campaign_run.completed_at = datetime.utcnow()
            db.commit()
        
        raise


@celery_app.task(bind=True, base=DatabaseTask, name='app.services.campaign_tasks.send_campaign_message')
def send_campaign_message(self, message_id: int):
    """
    Send a single campaign message via WhatsApp
    
    Args:
        message_id: ID of the message to send
    """
    db = self.db
    
    try:
        # Get message with related data eagerly loaded (1 query instead of 4)
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            logger.error(f"❌ Message {message_id} not found")
            return
        
        # Get related data in a single query via JOIN
        related = db.query(Campaign, Contact, Template).filter(
            Campaign.id == message.campaign_id,
            Contact.id == message.contact_id,
            Template.id == message.template_id
        ).first()
        
        if not related:
            logger.error(f"❌ Missing data for message {message_id}")
            message.status = MessageStatus.FAILED
            message.error_message = "Missing campaign, contact, or template data"
            db.commit()
            return
        
        campaign, contact, template = related
        
        # Update message status
        message.status = MessageStatus.SENDING
        db.commit()
        
        # Send message via WhatsApp
        result = asyncio.run(
            whatsapp_service.send_campaign_message(
                contact=contact,
                template=template,
                language=campaign.language,
                custom_variables=None,  # Auto-map from contact
                db=db
            )
        )
        
        if result.get("success"):
            # Message sent successfully
            message.status = MessageStatus.SENT
            message.whatsapp_message_id = result.get("message_id")
            message.sent_at = datetime.utcnow()
            logger.info(f"✅ Message {message_id} sent to {contact.phone_number}")
        else:
            # Message failed
            message.status = MessageStatus.FAILED
            message.error_message = result.get("error", "Unknown error")
            logger.error(f"❌ Message {message_id} failed: {message.error_message}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"❌ Error sending message {message_id}: {str(e)}")
        
        # Mark message as failed
        if message:
            message.status = MessageStatus.FAILED
            message.error_message = str(e)
            db.commit()
        
        # Retry logic
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=DatabaseTask, name='app.services.campaign_tasks.check_pending_campaigns')
def check_pending_campaigns(self):
    """
    Periodic task: Check for campaigns that should be executed now
    Runs every minute via Celery Beat
    """
    db = self.db
    
    try:
        now = datetime.utcnow()
        
        # Find active campaigns that are due for execution
        campaigns = db.query(Campaign).filter(
            Campaign.status == CampaignStatus.ACTIVE,
            Campaign.start_date <= now
        ).all()
        
        if not campaigns:
            logger.debug("No pending campaigns found")
            return
        
        logger.info(f"🔍 Checking {len(campaigns)} active campaigns")
        
        for campaign in campaigns:
            # Check if campaign should run now
            should_run = False
            
            # One-time campaigns
            if campaign.recurrence_type == RecurrenceType.ONCE:
                # Check if already executed
                existing_run = db.query(CampaignRun).filter(
                    CampaignRun.campaign_id == campaign.id
                ).first()
                
                if not existing_run and campaign.start_date <= now:
                    should_run = True
            
            # Daily recurring campaigns
            elif campaign.recurrence_type == RecurrenceType.DAILY:
                # Check if already ran today
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_run = db.query(CampaignRun).filter(
                    CampaignRun.campaign_id == campaign.id,
                    CampaignRun.scheduled_at >= today_start
                ).first()
                
                if not today_run:
                    should_run = True
            
            # Weekly recurring campaigns
            elif campaign.recurrence_type == RecurrenceType.WEEKLY:
                # Check if already ran this week
                week_start = now - timedelta(days=now.weekday())
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                week_run = db.query(CampaignRun).filter(
                    CampaignRun.campaign_id == campaign.id,
                    CampaignRun.scheduled_at >= week_start
                ).first()
                
                if not week_run:
                    should_run = True
            
            # Monthly recurring campaigns
            elif campaign.recurrence_type == RecurrenceType.MONTHLY:
                # Check if already ran this month
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_run = db.query(CampaignRun).filter(
                    CampaignRun.campaign_id == campaign.id,
                    CampaignRun.scheduled_at >= month_start
                ).first()
                
                if not month_run:
                    should_run = True
            
            # Create and execute campaign run
            if should_run:
                logger.info(f"📅 Scheduling campaign run for '{campaign.name}' (ID: {campaign.id})")
                
                campaign_run = CampaignRun(
                    campaign_id=campaign.id,
                    scheduled_at=now,
                    status=CampaignStatus.PENDING
                )
                db.add(campaign_run)
                db.commit()
                db.refresh(campaign_run)
                
                # Queue execution task
                execute_campaign_run.delay(campaign_run.id)
        
        logger.info("✅ Campaign check completed")
        
    except Exception as e:
        logger.error(f"❌ Error checking pending campaigns: {str(e)}")
        raise
