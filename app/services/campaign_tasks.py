"""
Celery Tasks for Campaign Execution
Background jobs for sending WhatsApp messages
"""
import ast
import asyncio
import logging
from datetime import timedelta
from sqlalchemy.orm import joinedload

from app.celery_app import celery_app
from app.core.datetime_utils import now_utc
from app.models.campaign import Campaign, CampaignRun
from app.models.message import Message
from app.models.contact import Contact
from app.models.template import Template
from app.utils.enums import CampaignStatus, MessageStatus, MessageType, Language, RecurrenceType
from app.services.template_service import TemplateService
from app.services.whatsapp_service import whatsapp_service
from app.services.base_task import DatabaseTask

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, base=DatabaseTask, name='app.services.campaign_tasks.check_pending_campaigns')
def check_pending_campaigns(self):
    """
    Periodic task: Check for campaigns that should be executed now.
    Runs every minute via Celery Beat.
    """
    db = self.db

    try:
        now = now_utc()
        campaigns = _get_active_campaigns(db, now)

        if not campaigns:
            logger.debug("No pending campaigns found")
            return

        logger.info(f"🔍 Checking {len(campaigns)} active campaigns")

        for campaign in campaigns:
            if _should_campaign_run(db, campaign, now):
                _schedule_campaign_run(db, campaign, now)

        logger.info("✅ Campaign check completed")

    except Exception as e:
        logger.error(f"❌ Error checking pending campaigns: {str(e)}")
        raise


@celery_app.task(bind=True, base=DatabaseTask, name='app.services.campaign_tasks.execute_campaign_run')
def execute_campaign_run(self, campaign_run_id: int):
    """
    Execute a campaign run - send messages to all target contacts.

    Args:
        campaign_run_id: ID of the campaign run to execute
    """
    db = self.db
    campaign_run = None

    try:
        campaign_run, campaign = _load_campaign_run(db, campaign_run_id)
        if not campaign_run or not campaign:
            return

        _mark_run_as_running(db, campaign_run)

        contacts = _get_target_contacts(db, campaign)
        if not contacts:
            _complete_run_with_no_contacts(db, campaign_run, campaign)
            return

        template = _load_template(db, campaign)
        if not template:
            _mark_run_as_failed(db, campaign_run)
            return

        messages = _build_messages(db, contacts, campaign, campaign_run, template)
        _dispatch_messages(messages)
        _complete_run(db, campaign_run, contacts, messages)

        logger.info(f"✅ Campaign run {campaign_run_id} completed: {len(messages)} queued")

    except Exception as e:
        logger.error(f"❌ Error executing campaign run {campaign_run_id}: {str(e)}")
        _mark_run_as_failed(db, campaign_run)
        raise


@celery_app.task(bind=True, base=DatabaseTask, name='app.services.campaign_tasks.send_campaign_message')
def send_campaign_message(self, message_id: int):
    """
    Send a single campaign message via WhatsApp.

    Args:
        message_id: ID of the message to send
    """
    db = self.db
    message = None

    try:
        message = db.query(Message).filter(Message.id == message_id).first()

        if not message:
            logger.error(f"❌ Message {message_id} not found")
            return

        related = db.query(Campaign, Contact, Template).filter(
            Campaign.id == message.campaign_id,
            Contact.id == message.contact_id,
            Template.id == Campaign.template_id
        ).first()

        if not related:
            logger.error(f"❌ Missing data for message {message_id}")
            message.status = MessageStatus.FAILED
            message.failure_reason = "Missing campaign, contact, or template data"
            message.updated_at = now_utc()
            db.commit()
            return

        _, contact, template = related 

        result = asyncio.run(
            whatsapp_service.send_template_message(
                phone_number=contact.phone_number,
                template_name=template.template_name,
                language_code=(contact.preferred_language or Language.ENGLISH).value,
                body_params=message.message_body,
            )
        )

        if result.success:
            message.status = MessageStatus.SENT
            message.whatsapp_message_id = result.message_id
            message.sent_at = now_utc()
            message.updated_at = now_utc()
            logger.info(f"✅ Message {message_id} sent to {contact.phone_number}")
        else:
            message.status = MessageStatus.FAILED
            message.failure_reason = result.error or "Unknown error"
            message.updated_at = now_utc()
            logger.error(f"❌ Message {message_id} failed: {message.failure_reason}")

        db.commit()

    except Exception as e:
        logger.error(f"❌ Error sending message {message_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


# ---------------------------------------------------------------------------
# check_pending_campaigns helpers
# ---------------------------------------------------------------------------

def _get_active_campaigns(db, now):
    return db.query(Campaign).filter(
        Campaign.status == CampaignStatus.ACTIVE,
        Campaign.start_date <= now.date()
    ).all()


def _should_campaign_run(db, campaign, now) -> bool:
    checkers = {
        RecurrenceType.ONE_TIME: _should_run_one_time,
        RecurrenceType.DAILY:    _should_run_daily,
        RecurrenceType.WEEKLY:   _should_run_weekly,
        RecurrenceType.MONTHLY:  _should_run_monthly,
    }
    checker = checkers.get(campaign.recurrence_type)
    return checker(db, campaign, now) if checker else False


def _has_existing_run(db, campaign_id, since=None) -> bool:
    query = db.query(CampaignRun).filter(CampaignRun.campaign_id == campaign_id)
    if since:
        query = query.filter(CampaignRun.scheduled_at >= since)
    return query.first() is not None


def _should_run_one_time(db, campaign, now) -> bool:
    return campaign.start_date <= now.date() and not _has_existing_run(db, campaign.id)


def _should_run_daily(db, campaign, now) -> bool:
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return not _has_existing_run(db, campaign.id, since=today_start)


def _should_run_weekly(db, campaign, now) -> bool:
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return not _has_existing_run(db, campaign.id, since=week_start)


def _should_run_monthly(db, campaign, now) -> bool:
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return not _has_existing_run(db, campaign.id, since=month_start)


def _schedule_campaign_run(db, campaign, now):
    logger.info(f"📅 Scheduling campaign run for '{campaign.name}' (ID: {campaign.id})")
    campaign_run = CampaignRun(
        campaign_id=campaign.id,
        jeweller_id=campaign.jeweller_id,
        scheduled_at=now,
        status="PENDING"
    )
    db.add(campaign_run)
    db.commit()
    db.refresh(campaign_run)
    execute_campaign_run.delay(campaign_run.id)


# ---------------------------------------------------------------------------
# execute_campaign_run helpers
# ---------------------------------------------------------------------------

def _load_campaign_run(db, campaign_run_id):
    campaign_run = db.query(CampaignRun).options(
        joinedload(CampaignRun.campaign)
    ).filter(CampaignRun.id == campaign_run_id).first()

    if not campaign_run:
        logger.error(f"❌ Campaign run {campaign_run_id} not found")
        return None, None

    campaign = campaign_run.campaign
    if not campaign:
        logger.error(f"❌ Campaign {campaign_run.campaign_id} not found")
        return campaign_run, None

    logger.info(f"🚀 Starting campaign run {campaign_run_id} for campaign '{campaign.name}'")
    return campaign_run, campaign


def _mark_run_as_running(db, campaign_run):
    campaign_run.status = "RUNNING"
    campaign_run.started_at = now_utc()
    db.commit()


def _mark_run_as_failed(db, campaign_run):
    if campaign_run:
        campaign_run.status = "FAILED"
        campaign_run.completed_at = now_utc()
        db.commit()


def _get_target_contacts(db, campaign):
    query = db.query(Contact).filter(
        Contact.jeweller_id == campaign.jeweller_id,
        Contact.is_deleted == False
    )
    if campaign.sub_segment:
        query = query.filter(Contact.segment == campaign.sub_segment)
    return query.all()


def _complete_run_with_no_contacts(db, campaign_run, campaign):
    logger.warning(f"⚠️ No contacts found for campaign {campaign.id}")
    campaign_run.status = "COMPLETED"
    campaign_run.completed_at = now_utc()
    campaign_run.total_contacts = 0
    campaign_run.eligible_contacts = 0
    campaign_run.messages_queued = 0
    campaign_run.messages_failed = 0
    db.commit()


def _load_template(db, campaign):
    template = db.query(Template).filter(Template.id == campaign.template_id).first()
    if not template:
        logger.error(f"❌ Template {campaign.template_id} not found for campaign {campaign.id}")
    return template


def _resolve_variables(campaign, contact) -> dict:
    if not campaign.variable_mapping:
        return {}
    try:
        raw_mapping = (
            ast.literal_eval(campaign.variable_mapping)
            if isinstance(campaign.variable_mapping, str)
            else campaign.variable_mapping
        )
        if not isinstance(raw_mapping, dict):
            return {}
        return {
            key: (getattr(contact, value) or "" if isinstance(value, str) and hasattr(contact, value) else str(value))
            for key, value in raw_mapping.items()
        }
    except Exception:
        return {}


def _build_messages(db, contacts, campaign, campaign_run, template) -> list:
    logger.info(f"📋 Found {len(contacts)} contacts to message")
    template_service = TemplateService(db)
    messages = []

    for contact in contacts:
        language = contact.preferred_language or Language.ENGLISH
        variables = _resolve_variables(campaign, contact)
        body = template_service.render_template(campaign.template_id, language, variables) or ""

        message = Message(
            campaign_id=campaign.id,
            campaign_run_id=campaign_run.id,
            contact_id=contact.id,
            jeweller_id=campaign.jeweller_id,
            message_type=MessageType.CAMPAIGN,
            phone_number=contact.phone_number,
            template_name=template.template_name,
            language=language,
            message_body=body,
            status=MessageStatus.QUEUED,
            scheduled_at=now_utc(),
        )
        db.add(message)
        messages.append(message)

    db.commit()
    return messages


def _dispatch_messages(messages: list):
    for message in messages:
        send_campaign_message.delay(message.id)


def _complete_run(db, campaign_run, contacts, messages):
    campaign_run.total_contacts = len(contacts)
    campaign_run.eligible_contacts = len(contacts)
    campaign_run.messages_queued = len(messages)
    campaign_run.messages_failed = 0
    campaign_run.status = "COMPLETED"
    campaign_run.completed_at = now_utc()
    db.commit()