from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.webhook import WebhookEvent
from app.models.message import Message
from app.utils.enums import MessageStatus
import json
from datetime import datetime

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


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
    # Get raw payload
    payload = await request.json()
    payload_str = json.dumps(payload)
    
    # Store webhook event
    webhook_event = WebhookEvent(
        event_type="message_status",
        payload=payload_str,
        received_at=datetime.utcnow()
    )
    db.add(webhook_event)
    
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
                                    timestamp = status_update.get("timestamp")
                                    
                                    # Find message in database
                                    message = db.query(Message).filter(
                                        Message.whatsapp_message_id == whatsapp_message_id
                                    ).first()
                                    
                                    if message:
                                        # Update message status
                                        if status_value == "sent":
                                            message.status = MessageStatus.SENT
                                            message.sent_at = datetime.fromtimestamp(int(timestamp))
                                        elif status_value == "delivered":
                                            message.status = MessageStatus.DELIVERED
                                            message.delivered_at = datetime.fromtimestamp(int(timestamp))
                                        elif status_value == "read":
                                            message.status = MessageStatus.READ
                                            message.read_at = datetime.fromtimestamp(int(timestamp))
                                        elif status_value == "failed":
                                            message.status = MessageStatus.FAILED
                                            message.failed_at = datetime.fromtimestamp(int(timestamp))
                                            
                                            # Get failure reason
                                            errors = status_update.get("errors", [])
                                            if errors:
                                                message.failure_reason = errors[0].get("message", "Unknown error")
                                        
                                        message.updated_at = datetime.utcnow()
                                        webhook_event.jeweller_id = message.jeweller_id
        
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
    
    # TODO: Validate token against stored verify_token in Jeweller model
    # For now, accept any token (insecure - fix in production)
    
    if mode == "subscribe" and challenge:
        return int(challenge)
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification failed"
    )
