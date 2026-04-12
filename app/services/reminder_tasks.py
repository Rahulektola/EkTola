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
# Helper: calculate whether today is the reminder date
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

    # Ordinal suffix
    if 11 <= effective_day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(effective_day % 10, "th")

    return f"{effective_day}{suffix} {due.strftime('%B %Y')}"


# ---------------------------------------------------------------------------
# Core: send a single reminder message via WhatsApp
# ---------------------------------------------------------------------------

def _send_reminder(
    contact: Contact,
    jeweller: Jeweller,
    message_type: MessageType,
    template_name: str,
    today: date,
    db: Session,
) -> bool:
    """
    Build a Message record and send the WhatsApp template.

    Returns True on success.
    """
    from app.core.encryption import decrypt_token, TokenEncryptionError
    from app.services.whatsapp_service import whatsapp_service, WhatsAppServiceError

    payment_day = (
        contact.sip_payment_day if message_type == MessageType.SIP_REMINDER
        else contact.loan_payment_day
    )
    due_date_str = _format_due_date(payment_day, today)

    # Build the rendered message body (for audit / display purposes)
    label = "Gold SIP" if message_type == MessageType.SIP_REMINDER else "Gold Loan"
    rendered_body = (
        f"Hi {contact.name or 'Customer'}, your {label} payment is due on {due_date_str}. "
        "Please ensure timely payment."
    )

    # Create Message record
    message = Message(
        jeweller_id=contact.jeweller_id,
        contact_id=contact.id,
        campaign_run_id=None,
        message_type=message_type,
        phone_number=contact.phone_number,
        template_name=template_name,
        language=contact.preferred_language or Language.ENGLISH,
        message_body=rendered_body,
        status=MessageStatus.QUEUED,
        scheduled_at=now_utc(),
        queued_at=now_utc(),
    )
    db.add(message)
    db.flush()  # get message.id before sending

    # Attempt to send via jeweller's WhatsApp account using HTTPX
    try:
        if not jeweller.phone_number_id or not jeweller.access_token:
            raise WhatsAppServiceError(
                f"WhatsApp not connected for jeweller {contact.jeweller_id}",
                error_code="WHATSAPP_NOT_CONNECTED"
            )

        try:
            access_token = decrypt_token(jeweller.access_token)
        except TokenEncryptionError as e:
            raise WhatsAppServiceError(
                f"Failed to decrypt token for jeweller {contact.jeweller_id}: {str(e)}",
                error_code="DECRYPTION_FAILED"
            )

        body_params = [contact.name or "Customer", due_date_str]
        language_code = (contact.preferred_language or Language.ENGLISH).value

        response = whatsapp_service.send_template_message_sync(
            phone_number_id=jeweller.phone_number_id,
            access_token=access_token,
            phone_number=contact.phone_number,
            template_name=template_name,
            language_code=language_code,
            body_params=body_params,
        )

        if not response.success:
            raise WhatsAppServiceError(response.error or "WhatsApp send failed")

        message.status = MessageStatus.SENT
        message.sent_at = now_utc()
        message.whatsapp_message_id = response.message_id
        db.flush()

        logger.info(
            f"✅ {message_type.value} reminder sent to {contact.phone_number} "
            f"(jeweller {contact.jeweller_id})"
        )
        return True

    except WhatsAppServiceError as e:
        logger.error(
            f"❌ WhatsApp error sending {message_type.value} to {contact.phone_number}: "
            f"{e.message} [{e.error_code}]"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = now_utc()
        message.failure_reason = f"{e.error_code}: {e.message}"
        db.flush()
        return False

    except Exception as e:
        logger.error(
            f"❌ Error sending {message_type.value} to {contact.phone_number}: {e}"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = now_utc()
        message.failure_reason = str(e)
        db.flush()
        return False


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
    now_utc = now_utc()
    today = (now_utc + IST_OFFSET).date()

    logger.info(f"🔔 Starting payment reminder check for {today.isoformat()}")

    # Counters
    sip_sent = 0
    loan_sent = 0
    sip_skipped = 0
    loan_skipped = 0
    failed = 0

    try:
        # Get all approved jewellers that have contacts with schedules
        jeweller_ids = (
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
        jeweller_ids = [j[0] for j in jeweller_ids]

        if not jeweller_ids:
            logger.info("No contacts with payment schedules found.")
            return

        # Batch-fetch all jewellers in a single query instead of one query per jeweller_id
        jewellers = db.query(Jeweller).filter(Jeweller.id.in_(jeweller_ids)).all()
        jeweller_map = {j.id: j for j in jewellers}

        for jeweller_id in jeweller_ids:
            jeweller = jeweller_map.get(jeweller_id)
            if not jeweller:
                continue

            # ---- SIP Reminders ----
            sip_contacts = (
                db.query(Contact)
                .filter(
                    Contact.jeweller_id == jeweller_id,
                    Contact.is_deleted == False,
                    Contact.opted_out == False,
                    Contact.segment.in_([SegmentType.GOLD_SIP, SegmentType.BOTH]),
                    Contact.sip_payment_day.isnot(None),
                )
                .all()
            )

            for contact in sip_contacts:
                if not _is_reminder_day(
                    contact.sip_payment_day,
                    contact.sip_reminder_days_before or 3,
                    today,
                ):
                    continue  # not the day

                if _already_sent_this_month(contact.last_sip_reminder_sent_at, today):
                    sip_skipped += 1
                    continue

                ok = _send_reminder(
                    contact=contact,
                    jeweller=jeweller,
                    message_type=MessageType.SIP_REMINDER,
                    template_name=settings.WHATSAPP_SIP_REMINDER_TEMPLATE,
                    today=today,
                    db=db,
                )
                if ok:
                    contact.last_sip_reminder_sent_at = now_utc
                    sip_sent += 1
                else:
                    failed += 1

            # ---- Loan Reminders ----
            loan_contacts = (
                db.query(Contact)
                .filter(
                    Contact.jeweller_id == jeweller_id,
                    Contact.is_deleted == False,
                    Contact.opted_out == False,
                    Contact.segment.in_([SegmentType.GOLD_LOAN, SegmentType.BOTH]),
                    Contact.loan_payment_day.isnot(None),
                )
                .all()
            )

            for contact in loan_contacts:
                if not _is_reminder_day(
                    contact.loan_payment_day,
                    contact.loan_reminder_days_before or 3,
                    today,
                ):
                    continue

                if _already_sent_this_month(contact.last_loan_reminder_sent_at, today):
                    loan_skipped += 1
                    continue

                ok = _send_reminder(
                    contact=contact,
                    jeweller=jeweller,
                    message_type=MessageType.LOAN_REMINDER,
                    template_name=settings.WHATSAPP_LOAN_REMINDER_TEMPLATE,
                    today=today,
                    db=db,
                )
                if ok:
                    contact.last_loan_reminder_sent_at = now_utc
                    loan_sent += 1
                else:
                    failed += 1

        # Commit all changes at once
        db.commit()

        logger.info(
            f"✅ Payment reminder run complete for {today.isoformat()}: "
            f"SIP sent={sip_sent} skipped={sip_skipped} | "
            f"Loan sent={loan_sent} skipped={loan_skipped} | "
            f"Failed={failed}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in payment reminder task: {e}")
        raise
