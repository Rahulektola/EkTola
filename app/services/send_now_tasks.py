"""
Celery Tasks for Send-Now (Manual Reminder)
Jeweller-triggered immediate WhatsApp reminders using the customer's registered template.
"""
import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import or_

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

IST_OFFSET = timedelta(hours=5, minutes=30)

# Segment → template mapping (same templates as auto-reminders)
SEGMENT_TEMPLATE_MAP = {
    SegmentType.GOLD_SIP: settings.WHATSAPP_SIP_REMINDER_TEMPLATE,
    SegmentType.GOLD_LOAN: settings.WHATSAPP_LOAN_REMINDER_TEMPLATE,
}


def _get_template_for_contact(contact: Contact) -> list[tuple[str, str]]:
    """
    Return list of (template_name, label) for a contact based on segment.
    A BOTH-segment contact gets both SIP and Loan templates.
    """
    templates = []
    if contact.segment in (SegmentType.GOLD_SIP, SegmentType.BOTH):
        templates.append((settings.WHATSAPP_SIP_REMINDER_TEMPLATE, "Gold SIP"))
    if contact.segment in (SegmentType.GOLD_LOAN, SegmentType.BOTH):
        templates.append((settings.WHATSAPP_LOAN_REMINDER_TEMPLATE, "Gold Loan"))
    return templates


def _send_manual_reminder(
    contact: Contact,
    jeweller: Jeweller,
    template_name: str,
    label: str,
    db,
) -> bool:
    """
    Build a Message record and send the WhatsApp template immediately.
    Returns True on success.
    """
    from app.core.encryption import decrypt_token, TokenEncryptionError
    from app.services.whatsapp_service import whatsapp_service, WhatsAppServiceError

    now = now_utc()
    today = (now + IST_OFFSET).date()

    rendered_body = (
        f"Hi {contact.name or 'Customer'}, this is a reminder for your "
        f"{label} payment. Please ensure timely payment."
    )

    message = Message(
        jeweller_id=contact.jeweller_id,
        contact_id=contact.id,
        campaign_run_id=None,
        message_type=MessageType.MANUAL_REMINDER,
        phone_number=contact.phone_number,
        template_name=template_name,
        language=contact.preferred_language or Language.ENGLISH,
        message_body=rendered_body,
        status=MessageStatus.QUEUED,
        scheduled_at=None,
        queued_at=now,
    )
    db.add(message)
    db.flush()

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
            template_name=template_name,
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
            f"✅ Manual reminder sent to {contact.phone_number} "
            f"(jeweller {contact.jeweller_id}, template {template_name})"
        )
        return True

    except WhatsAppServiceError as e:
        logger.error(
            f"❌ WhatsApp error sending manual reminder to "
            f"{contact.phone_number}: {e.message} [{e.error_code}]"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = now_utc()
        message.failure_reason = f"{e.error_code}: {e.message}"
        db.flush()
        return False

    except Exception as e:
        logger.error(
            f"❌ Unexpected error sending manual reminder to "
            f"{contact.phone_number}: {e}"
        )
        message.status = MessageStatus.FAILED
        message.failed_at = now_utc()
        message.failure_reason = str(e)
        db.flush()
        return False


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.services.send_now_tasks.send_now_to_contacts",
    queue="campaigns",
)
def send_now_to_contacts(self, jeweller_id: int, contact_ids: List[int]):
    """
    Celery task: send reminders immediately to a list of contacts.
    Each contact receives the template matching their segment.

    Args:
        jeweller_id: ID of the jeweller triggering the send
        contact_ids: List of contact IDs to send to
    """
    db = self.db
    sent = failed = skipped = 0

    try:
        jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
        if not jeweller:
            logger.error(f"❌ Jeweller {jeweller_id} not found for send-now")
            return {"sent": 0, "failed": 0, "skipped": 0, "error": "Jeweller not found"}

        contacts = (
            db.query(Contact)
            .filter(
                Contact.id.in_(contact_ids),
                Contact.jeweller_id == jeweller_id,
                Contact.is_deleted == False,
                Contact.opted_out == False,
            )
            .all()
        )

        logger.info(
            f"📤 Send-now triggered by jeweller {jeweller_id} "
            f"for {len(contacts)} contacts"
        )

        for contact in contacts:
            templates = _get_template_for_contact(contact)
            if not templates:
                skipped += 1
                logger.warning(
                    f"⚠️ No template for contact {contact.id} "
                    f"(segment={contact.segment})"
                )
                continue

            for template_name, label in templates:
                ok = _send_manual_reminder(
                    contact=contact,
                    jeweller=jeweller,
                    template_name=template_name,
                    label=label,
                    db=db,
                )
                if ok:
                    sent += 1
                else:
                    failed += 1

        db.commit()
        logger.info(
            f"✅ Send-now complete for jeweller {jeweller_id}: "
            f"sent={sent} failed={failed} skipped={skipped}"
        )
        return {"sent": sent, "failed": failed, "skipped": skipped}

    except Exception as e:
        logger.error(f"❌ Error in send-now task: {e}")
        db.rollback()
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.services.send_now_tasks.send_now_to_segment",
    queue="campaigns",
)
def send_now_to_segment(self, jeweller_id: int, segment: str):
    """
    Celery task: send reminders immediately to all contacts in a segment.

    Args:
        jeweller_id: ID of the jeweller triggering the send
        segment: SegmentType value (GOLD_SIP, GOLD_LOAN, BOTH, MARKETING)
    """
    db = self.db

    try:
        segment_enum = SegmentType(segment)

        # Resolve which segments to query
        if segment_enum == SegmentType.BOTH:
            target_segments = [SegmentType.GOLD_SIP, SegmentType.GOLD_LOAN, SegmentType.BOTH]
        elif segment_enum == SegmentType.GOLD_SIP:
            target_segments = [SegmentType.GOLD_SIP, SegmentType.BOTH]
        elif segment_enum == SegmentType.GOLD_LOAN:
            target_segments = [SegmentType.GOLD_LOAN, SegmentType.BOTH]
        else:
            logger.warning(f"⚠️ Segment {segment} has no reminder template")
            return {"sent": 0, "failed": 0, "skipped": 0, "error": "No template for segment"}

        contacts = (
            db.query(Contact)
            .filter(
                Contact.jeweller_id == jeweller_id,
                Contact.is_deleted == False,
                Contact.opted_out == False,
                Contact.segment.in_(target_segments),
            )
            .all()
        )

        contact_ids = [c.id for c in contacts]

        if not contact_ids:
            logger.info(f"No contacts in segment {segment} for jeweller {jeweller_id}")
            return {"sent": 0, "failed": 0, "skipped": 0}

        # Delegate to the contact-list task
        result = send_now_to_contacts.apply(
            args=[jeweller_id, contact_ids],
        )
        return result.result

    except Exception as e:
        logger.error(f"❌ Error in send-now-segment task: {e}")
        db.rollback()
        raise
