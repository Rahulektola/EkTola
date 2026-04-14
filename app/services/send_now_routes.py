"""
Send-Now Routes: Jeweller-triggered immediate reminders
Endpoints for sending WhatsApp reminders to contacts on demand.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.core.dependencies import get_current_jeweller
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.models.message import Message
from app.schemas.send_now import (
    SendNowSingleRequest,
    SendNowBulkRequest,
    SendNowSegmentRequest,
    SendNowResponse,
    SendNowStatusResponse,
)
from app.utils.enums import SegmentType, MessageType, MessageStatus

router = APIRouter(prefix="/send-now", tags=["Send Now"])


def _validate_whatsapp_connected(jeweller: Jeweller):
    """Raise 400 if jeweller hasn't connected WhatsApp."""
    if not jeweller.phone_number_id or not jeweller.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WhatsApp is not connected. Please connect your WhatsApp Business Account first.",
        )


@router.post("/single", response_model=SendNowResponse, status_code=status.HTTP_202_ACCEPTED)
def send_now_single(
    request: SendNowSingleRequest,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db),
):
    """
    Send reminder to a single contact immediately.
    Uses the template matching the contact's registered segment.
    """
    _validate_whatsapp_connected(current_jeweller)

    contact = (
        db.query(Contact)
        .filter(
            Contact.id == request.contact_id,
            Contact.jeweller_id == current_jeweller.id,
            Contact.is_deleted == False,
        )
        .first()
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    if contact.opted_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact has opted out of messages",
        )

    if contact.segment == SegmentType.MARKETING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact is in MARKETING segment and has no reminder template",
        )

    from app.services.send_now_tasks import send_now_to_contacts
    task = send_now_to_contacts.delay(current_jeweller.id, [contact.id])

    return SendNowResponse(
        task_id=task.id,
        total_queued=1,
        message="Reminder queued for delivery",
    )


@router.post("/bulk", response_model=SendNowResponse, status_code=status.HTTP_202_ACCEPTED)
def send_now_bulk(
    request: SendNowBulkRequest,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db),
):
    """
    Send reminders to multiple contacts immediately.
    Each contact receives the template matching their registered segment.
    """
    _validate_whatsapp_connected(current_jeweller)

    # Validate all contact_ids belong to this jeweller and are active
    valid_count = (
        db.query(func.count(Contact.id))
        .filter(
            Contact.id.in_(request.contact_ids),
            Contact.jeweller_id == current_jeweller.id,
            Contact.is_deleted == False,
            Contact.opted_out == False,
            Contact.segment != SegmentType.MARKETING,
        )
        .scalar()
    )

    if valid_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid contacts found for sending reminders",
        )

    from app.services.send_now_tasks import send_now_to_contacts
    task = send_now_to_contacts.delay(current_jeweller.id, request.contact_ids)

    return SendNowResponse(
        task_id=task.id,
        total_queued=valid_count,
        message=f"Reminders queued for {valid_count} contacts",
    )


@router.post("/segment", response_model=SendNowResponse, status_code=status.HTTP_202_ACCEPTED)
def send_now_segment(
    request: SendNowSegmentRequest,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db),
):
    """
    Send reminders to all contacts in a segment immediately.
    Supports GOLD_SIP, GOLD_LOAN, and BOTH segments.
    """
    _validate_whatsapp_connected(current_jeweller)

    if request.segment == SegmentType.MARKETING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MARKETING segment has no reminder template",
        )

    # Resolve target segments
    if request.segment == SegmentType.BOTH:
        target_segments = [SegmentType.GOLD_SIP, SegmentType.GOLD_LOAN, SegmentType.BOTH]
    elif request.segment == SegmentType.GOLD_SIP:
        target_segments = [SegmentType.GOLD_SIP, SegmentType.BOTH]
    elif request.segment == SegmentType.GOLD_LOAN:
        target_segments = [SegmentType.GOLD_LOAN, SegmentType.BOTH]
    else:
        target_segments = [request.segment]

    contact_count = (
        db.query(func.count(Contact.id))
        .filter(
            Contact.jeweller_id == current_jeweller.id,
            Contact.is_deleted == False,
            Contact.opted_out == False,
            Contact.segment.in_(target_segments),
        )
        .scalar()
    )

    if contact_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active contacts in {request.segment.value} segment",
        )

    from app.services.send_now_tasks import send_now_to_segment
    task = send_now_to_segment.delay(current_jeweller.id, request.segment.value)

    return SendNowResponse(
        task_id=task.id,
        total_queued=contact_count,
        message=f"Reminders queued for {contact_count} contacts in {request.segment.value} segment",
    )


@router.get("/status/{task_id}", response_model=SendNowStatusResponse)
def get_send_now_status(
    task_id: str,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
):
    """
    Check the status of a send-now task.
    """
    from app.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    if result.state == "PENDING":
        return SendNowStatusResponse(
            task_id=task_id,
            total=0,
            sent=0,
            failed=0,
            pending=0,
            status="PENDING",
        )

    if result.state == "FAILURE":
        return SendNowStatusResponse(
            task_id=task_id,
            total=0,
            sent=0,
            failed=0,
            pending=0,
            status="FAILED",
        )

    if result.state == "SUCCESS" and isinstance(result.result, dict):
        data = result.result
        sent = data.get("sent", 0)
        failed = data.get("failed", 0)
        skipped = data.get("skipped", 0)
        total = sent + failed + skipped
        return SendNowStatusResponse(
            task_id=task_id,
            total=total,
            sent=sent,
            failed=failed,
            pending=0,
            status="COMPLETED",
        )

    return SendNowStatusResponse(
        task_id=task_id,
        total=0,
        sent=0,
        failed=0,
        pending=0,
        status="IN_PROGRESS",
    )
