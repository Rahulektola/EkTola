from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.webhook import WebhookEvent
from app.models.message import Message
from app.utils.enums import MessageStatus
from app.services.template_service import MessageService
import json
import hmac
import hashlib
from datetime import datetime

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify WhatsApp webhook signature using app secret
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        
    Returns:
        True if signature is valid
    """
    if not settings.WHATSAPP_APP_SECRET:
        # Skip verification if app secret not configured (development mode)
        return True
    
    if not signature or not signature.startswith("sha256="):
        return False
    
    expected_signature = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    WhatsApp Cloud API webhook endpoint
    Receives message status updates from WhatsApp
    
    This endpoint should be registered in WhatsApp Business Account settings
    """
    # Get raw payload for signature verification
    raw_payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    # Verify webhook signature
    if not verify_webhook_signature(raw_payload, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse JSON payload
    payload = json.loads(raw_payload)
    payload_str = json.dumps(payload)
    
    # Store webhook event
    webhook_event = WebhookEvent(
        event_type="message_status",
        payload=payload_str,
        received_at=datetime.utcnow()
    )
    db.add(webhook_event)
    
    # Initialize message service
    message_service = MessageService(db)
    
    try:
        # Parse WhatsApp payload
        # Format: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
        
        if "entry" in payload:
            for entry in payload["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if change.get("field") == "messages":
                            value = change.get("value", {})
                            
                            # Process status updates
                            if "statuses" in value:
                                for status_update in value["statuses"]:
                                    whatsapp_message_id = status_update.get("id")
                                    status_value = status_update.get("status")
                                    timestamp_str = status_update.get("timestamp")
                                    
                                    # Convert timestamp
                                    timestamp = None
                                    if timestamp_str:
                                        try:
                                            timestamp = datetime.fromtimestamp(int(timestamp_str))
                                        except (ValueError, TypeError):
                                            timestamp = datetime.utcnow()
                                    
                                    # Use message service to update status
                                    updated = message_service.update_message_status(
                                        whatsapp_message_id=whatsapp_message_id,
                                        status=status_value,
                                        timestamp=timestamp
                                    )
                                    
                                    # If message found, get jeweller_id for webhook event
                                    if updated:
                                        message = db.query(Message).filter(
                                            Message.whatsapp_message_id == whatsapp_message_id
                                        ).first()
                                        if message:
                                            webhook_event.jeweller_id = message.jeweller_id
                                    
                                    # Handle errors in status update
                                    if status_value == "failed":
                                        errors = status_update.get("errors", [])
                                        if errors:
                                            error_msg = errors[0].get("message", "Unknown error")
                                            message = db.query(Message).filter(
                                                Message.whatsapp_message_id == whatsapp_message_id
                                            ).first()
                                            if message:
                                                message.failure_reason = error_msg
                                                message.updated_at = datetime.utcnow()
                            
                            # Process incoming messages (for future use)
                            if "messages" in value:
                                for incoming_message in value["messages"]:
                                    # Log incoming message for debugging
                                    from_number = incoming_message.get("from")
                                    message_type = incoming_message.get("type")
                                    # TODO: Handle incoming messages if needed
        
        webhook_event.processed = True
        webhook_event.processed_at = datetime.utcnow()
        db.commit()
        
        return {"status": "success"}
    
    except Exception as e:
        webhook_event.processed = False
        webhook_event.error_message = str(e)
        db.commit()
        
        # Still return 200 to prevent WhatsApp from retrying
        return {"status": "error", "message": str(e)}


@router.get("/whatsapp")
def whatsapp_webhook_verify(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    WhatsApp webhook verification endpoint
    Required for setting up webhook in WhatsApp Business Account
    
    Query params:
    - hub.mode: "subscribe"
    - hub.verify_token: Your verify token
    - hub.challenge: Challenge string to echo back
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    # Validate token against configured verify token
    expected_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
    
    if mode == "subscribe" and challenge:
        # In development, accept if no token configured
        if not expected_token or token == expected_token:
            return int(challenge)
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification failed"
    )
