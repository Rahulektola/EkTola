"""
Celery Tasks for SIP & Loan Payment Reminders
Sends WhatsApp reminders N days before each customer's payment due date.

Schedule:
  - Runs daily at 9 AM IST via Celery Beat
  - Iterates every jeweller → every contact with a payment day set
  - Calculates whether today is the reminder day for that contact
  - If yes AND no reminder was already sent this month → sends WhatsApp template message
"""
import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import settings
from app.core.datetime_utils import now_utc
from app.database import SessionLocal
from app.models.contact import Contact
from app.models.jeweller import Jeweller
from app.models.message import Message
from app.utils.enums import (
    SegmentType,
    MessageStatus,
    MessageType,
    Language,
)
from app.services.base_task import DatabaseTask

logger = logging.getLogger(__name__)

# IST offset from UTC
IST_OFFSET = timedelta(hours=5, minutes=30)


# ---------------------------------------------------------------------------
# ReminderConfig: describes one reminder type (SIP or Loan) as data,
# so the processing loop runs once for both instead of duplicating code.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReminderConfig:
    segment_types: tuple[SegmentType, ...]
    payment_day_attr: str       # Contact attribute name, e.g. "sip_payment_day"
    reminder_days_attr: str     # Contact attribute name, e.g. "sip_reminder_days_before"
    last_sent_attr: str         # Contact attribute name, e.g. "last_sip_reminder_sent_at"
    message_type: MessageType
    template_name: str
    label: str                  # Human-readable label for the message body
    default_reminder_days: int = 3


REMINDER_CONFIGS: list[ReminderConfig] = [
    ReminderConfig(
        segment_types=(SegmentType.GOLD_SIP, SegmentType.BOTH),
        payment_day_attr="sip_payment_day",
        reminder_days_attr="sip_reminder_days_before",
        last_sent_attr="last_sip_reminder_sent_at",
        message_type=MessageType.SIP_REMINDER,
        template_name=settings.WHATSAPP_SIP_REMINDER_TEMPLATE,
        label="Gold SIP",
    ),
    ReminderConfig(
        segment_types=(SegmentType.GOLD_LOAN, SegmentType.BOTH),
        payment_day_attr="loan_payment_day",
        reminder_days_attr="loan_reminder_days_before",
        last_sent_attr="last_loan_reminder_sent_at",
        message_type=MessageType.LOAN_REMINDER,
        template_name=settings.WHATSAPP_LOAN_REMINDER_TEMPLATE,
        label="Gold Loan",
    ),
]


# ---------------------------------------------------------------------------
# Helper: date / reminder logic
# ---------------------------------------------------------------------------

def _is_reminder_day(payment_day: int, days_before: int, today: date) -> bool:
    """
    Return True if today is exactly `days_before` days before the payment
    due date for the current month.

    Handles month-end edge cases:
      - If payment_day > last day of month, the effective due date is the
        last day of the month.
    """
    year, month = today.year, today.month
    last_day = calendar.monthrange(year, month)[1]
    effective_day = min(payment_day, last_day)
    due_date = date(year, month, effective_day)
    reminder_date = due_date - timedelta(days=days_before)

    # reminder_date may fall in the previous month — that is expected
    return today == reminder_date


def _already_sent_this_month(last_sent: Optional[datetime], today: date) -> bool:
    """Return True if a reminder was already sent in the calendar month of `today`."""
    if last_sent is None:
        return False
    return last_sent.year == today.year and last_sent.month == today.month


def _format_due_date(payment_day: int, today: date) -> str:
    """Return a human-readable due date string like '5th March 2026'."""
    year, month = today.year, today.month
    last_day = calendar.monthrange(year, month)[1]
    effective_day = min(payment_day, last_day)
    due = date(year, month, effective_day)

    suffix = (
        "th" if 11 <= effective_day <= 13
        else {1: "st", 2: "nd", 3: "rd"}.get(effective_day % 10, "th")
    )
    return f"{effective_day}{suffix} {due.strftime('%B %Y')}"


# ---------------------------------------------------------------------------
# Core: send a single reminder message via WhatsApp
# ---------------------------------------------------------------------------

def _send_reminder(
    contact: Contact,
    jeweller: Jeweller,
    cfg: ReminderConfig,
    today: date,
    db: Session,
) -> bool:
    """
    Build a Message record and send the WhatsApp template.

    Returns True on success.
    """
    from app.core.encryption import decrypt_token, TokenEncryptionError
    from app.services.whatsapp_service import whatsapp_service, WhatsAppServiceError

    payment_day = getattr(contact, cfg.payment_day_attr)
    due_date_str = _format_due_date(payment_day, today)

    rendered_body = (
        f"Hi {contact.name or 'Customer'}, your {cfg.label} payment is due on "
        f"{due_date_str}. Please ensure timely payment."
    )

    message = Message(
        jeweller_id=contact.jeweller_id,
        contact_id=contact.id,
        campaign_run_id=None,
        message_type=cfg.message_type,
        phone_number=contact.phone_number,
        template_name=cfg.template_name,
        language=contact.preferred_language or Language.ENGLISH,
        message_body=rendered_body,
        status=MessageStatus.QUEUED,
        scheduled_at=now_utc(),
        queued_at=now_utc(),
    )
    db.add(message)
    db.flush()  # get message.id before sending

    try:
        if not jeweller.phone_number_id or not jeweller.access_token:
            raise WhatsAppServiceError(
                f"WhatsApp not connected for jeweller {contact.jeweller_id}",
                error_code="WHATSAPP_NOT_CONNECTED",
            )

        try:
            access_token = decrypt_token(jeweller.access_token)
        except TokenEncryptionError as e:
            raise WhatsAppServiceError(
                f"Failed to decrypt token for jeweller {contact.jeweller_id}: {e}",
                error_code="DECRYPTION_FAILED",
            )

        response = whatsapp_service.send_template_message_sync(
            phone_number_id=jeweller.phone_number_id,
            access_token=access_token,
            phone_number=contact.phone_number,
            template_name=cfg.template_name,
            language_code=(contact.preferred_language or Language.ENGLISH).value,
            header_params=[contact.name or "Customer"],
            body_params=[jeweller.business_name, today.strftime("%B")],
        )

        if not response.success:
            raise WhatsAppServiceError(response.error or "WhatsApp send failed")

        message.status = MessageStatus.SENT
        message.sent_at = now_utc()
        message.whatsapp_message_id = response.message_id
        db.flush()

        logger.info(
            f"✅ {cfg.message_type.value} reminder sent to {contact.phone_number} "
            f"(jeweller {contact.jeweller_id})"
        )
        return True

    except WhatsAppServiceError as e:
        logger.error(
            f"❌ WhatsApp error sending {cfg.message_type.value} to "
            f"{contact.phone_number}: {e.message} [{e.error_code}]"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = now_utc()
        message.failure_reason = f"{e.error_code}: {e.message}"
        db.flush()
        return False

    except Exception as e:
        logger.error(
            f"❌ Unexpected error sending {cfg.message_type.value} to "
            f"{contact.phone_number}: {e}"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = now_utc()
        message.failure_reason = str(e)
        db.flush()
        return False


# ---------------------------------------------------------------------------
# Private helpers for the Celery task
# ---------------------------------------------------------------------------

def _fetch_jeweller_map(db: Session) -> dict[int, Jeweller]:
    """
    Return {jeweller_id: Jeweller} for all jewellers that have at least
    one eligible contact with a SIP or Loan payment day set.
    """
    rows = (
        db.query(Contact.jeweller_id)
        .filter(
            Contact.is_deleted == False,
            Contact.opted_out == False,
            or_(
                Contact.sip_payment_day.isnot(None),
                Contact.loan_payment_day.isnot(None),
            ),
        )
        .distinct()
        .all()
    )
    ids = [row[0] for row in rows]
    if not ids:
        return {}

    jewellers = db.query(Jeweller).filter(Jeweller.id.in_(ids)).all()
    return {j.id: j for j in jewellers}


def _fetch_contacts(db: Session, jeweller_id: int, cfg: ReminderConfig) -> list[Contact]:
    """Fetch eligible, active contacts for one jeweller and one reminder type."""
    payment_day_col = getattr(Contact, cfg.payment_day_attr)
    return (
        db.query(Contact)
        .filter(
            Contact.jeweller_id == jeweller_id,
            Contact.is_deleted == False,
            Contact.opted_out == False,
            Contact.segment.in_(cfg.segment_types),
            payment_day_col.isnot(None),
        )
        .all()
    )


def _process_reminder_batch(
    db: Session,
    jeweller_id: int,
    jeweller: Jeweller,
    cfg: ReminderConfig,
    today: date,
    now: datetime,
) -> tuple[int, int, int]:
    """
    Process all contacts for one jeweller and one reminder type.

    Returns:
        (sent, skipped, failed) counts
    """
    sent = skipped = failed = 0

    for contact in _fetch_contacts(db, jeweller_id, cfg):
        payment_day = getattr(contact, cfg.payment_day_attr)
        reminder_days = getattr(contact, cfg.reminder_days_attr) or cfg.default_reminder_days
        last_sent_at = getattr(contact, cfg.last_sent_attr)

        if not _is_reminder_day(payment_day, reminder_days, today):
            continue

        if _already_sent_this_month(last_sent_at, today):
            skipped += 1
            continue

        ok = _send_reminder(
            contact=contact,
            jeweller=jeweller,
            cfg=cfg,
            today=today,
            db=db,
        )
        if ok:
            setattr(contact, cfg.last_sent_attr, now)
            sent += 1
        else:
            failed += 1

    return sent, skipped, failed


def _log_summary(today: date, counters: dict[MessageType, dict], failed: int) -> None:
    parts = " | ".join(
        f"{msg_type.value} sent={c['sent']} skipped={c['skipped']}"
        for msg_type, c in counters.items()
    )
    logger.info(
        f"✅ Payment reminder run complete for {today.isoformat()}: "
        f"{parts} | Failed={failed}"
    )


# ---------------------------------------------------------------------------
# Celery task: daily payment reminder runner
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.services.reminder_tasks.send_payment_reminders",
    queue="campaigns",
)
def send_payment_reminders(self):
    """
    Periodic task (daily at 9 AM IST via Celery Beat).

    For every jeweller → every contact with a payment day:
      1. Determine if today is the reminder day
      2. Skip if reminder already sent this month
      3. Send WhatsApp template and record Message
      4. Update last_*_reminder_sent_at
    """
    db = self.db
    now = now_utc()
    today = (now + IST_OFFSET).date()

    logger.info(f"🔔 Starting payment reminder check for {today.isoformat()}")

    counters = {cfg.message_type: {"sent": 0, "skipped": 0} for cfg in REMINDER_CONFIGS}
    failed = 0

    try:
        jeweller_map = _fetch_jeweller_map(db)

        if not jeweller_map:
            logger.info("No contacts with payment schedules found.")
            return

        for jeweller_id, jeweller in jeweller_map.items():
            for cfg in REMINDER_CONFIGS:
                sent, skipped, errors = _process_reminder_batch(
                    db=db,
                    jeweller_id=jeweller_id,
                    jeweller=jeweller,
                    cfg=cfg,
                    today=today,
                    now=now,
                )
                counters[cfg.message_type]["sent"] += sent
                counters[cfg.message_type]["skipped"] += skipped
                failed += errors

        db.commit()
        _log_summary(today, counters, failed)

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in payment reminder task: {e}")
        raise