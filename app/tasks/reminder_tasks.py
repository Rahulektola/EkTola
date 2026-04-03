"""
Celery Tasks for SIP & Loan Payment Reminders
Sends WhatsApp reminders N days before each customer's payment due date.

Schedule:
  - Runs daily at 9 AM IST via Celery Beat
  - Iterates every jeweller → every contact with a payment day set
  - Calculates whether today is the reminder day for that contact
  - If yes AND no reminder was already sent this month → sends WhatsApp template message
"""
import asyncio
import calendar
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from celery import Task
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import settings
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

logger = logging.getLogger(__name__)

# IST offset from UTC
IST_OFFSET = timedelta(hours=5, minutes=30)


class DatabaseTask(Task):
    """Base task that provides a database session"""
    _db: Optional[Session] = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


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
    from app.services.whatsapp_service import get_jeweller_whatsapp_client, WhatsAppServiceError

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
        scheduled_at=datetime.utcnow(),
        queued_at=datetime.utcnow(),
    )
    db.add(message)
    db.flush()  # get message.id before sending

    # Attempt to send via jeweller's WhatsApp client
    try:
        client = get_jeweller_whatsapp_client(contact.jeweller_id, db)
        if client is None:
            # Dev mode — mark as sent for traceability
            logger.warning(
                f"[DEV MODE] Reminder ({message_type.value}) to {contact.phone_number} "
                f"for jeweller {contact.jeweller_id}"
            )
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
            message.whatsapp_message_id = f"dev_{message_type.value}_{contact.id}_{today.isoformat()}"
            db.flush()
            return True

        # Template body params: customer_name and due_date_str
        body_params = [contact.name or "Customer", due_date_str]
        language_code = (contact.preferred_language or Language.ENGLISH).value

        # pywa 3.x send_template (sync wrapper around async call)
        components = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in body_params],
            }
        ]

        response = asyncio.run(
            client.send_template(
                to=contact.phone_number,
                template=template_name,
                language=language_code,
                components=components,
            )
        )

        wa_msg_id = response.id if hasattr(response, "id") else str(response)

        message.status = MessageStatus.SENT
        message.sent_at = datetime.utcnow()
        message.whatsapp_message_id = wa_msg_id
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
        message.failed_at = datetime.utcnow()
        message.failure_reason = f"{e.error_code}: {e.message}"
        db.flush()
        return False

    except Exception as e:
        logger.error(
            f"❌ Error sending {message_type.value} to {contact.phone_number}: {e}"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = datetime.utcnow()
        message.failure_reason = str(e)
        db.flush()
        return False


# ---------------------------------------------------------------------------
# Celery task: daily payment reminder runner
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.reminder_tasks.send_payment_reminders",
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
    now_utc = datetime.utcnow()
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
