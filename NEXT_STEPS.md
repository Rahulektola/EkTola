# Next Steps for EkTola Backend

## Critical Priority (Complete Before Production)

### 1. WhatsApp Cloud API Integration
**File:** `app/services/whatsapp_service.py`

```python
"""
WhatsApp Cloud API integration service
Implements message sending via WhatsApp Business API
"""

import httpx
from typing import Dict, Optional
from app.config import settings

class WhatsAppService:
    """Service for sending messages via WhatsApp Cloud API"""
    
    BASE_URL = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
    
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list
    ) -> Dict:
        """Send a template message"""
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": param}
                            for param in parameters
                        ]
                    }
                ]
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.json()
```

### 2. Celery Task Queue Setup
**File:** `app/celery_app.py`

```python
"""
Celery configuration for background task processing
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "ektola",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.message_tasks", "app.tasks.campaign_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

**File:** `app/tasks/message_tasks.py`

```python
"""
Background tasks for message sending
"""

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.message import Message
from app.models.jeweller import Jeweller
from app.services.whatsapp_service import WhatsAppService
from app.utils.enums import MessageStatus
from datetime import datetime

@celery_app.task(bind=True, max_retries=3)
def send_whatsapp_message(self, message_id: int):
    """Send a single WhatsApp message"""
    db = SessionLocal()
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return {"status": "error", "reason": "Message not found"}
        
        jeweller = db.query(Jeweller).filter(Jeweller.id == message.jeweller_id).first()
        if not jeweller or not jeweller.access_token or not jeweller.phone_number_id:
            message.status = MessageStatus.FAILED
            message.failure_reason = "WhatsApp credentials not configured"
            db.commit()
            return {"status": "error", "reason": "WhatsApp not configured"}
        
        # Send message
        service = WhatsAppService(jeweller.access_token, jeweller.phone_number_id)
        response = await service.send_template_message(
            to=message.phone_number,
            template_name=message.template_name,
            language_code=message.language.value,
            parameters=[]  # Parse from message_body
        )
        
        if "messages" in response:
            message.whatsapp_message_id = response["messages"][0]["id"]
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
        else:
            message.status = MessageStatus.FAILED
            message.failure_reason = response.get("error", {}).get("message", "Unknown error")
        
        db.commit()
        return {"status": "success", "message_id": message.id}
        
    except Exception as e:
        db.rollback()
        # Retry on failure
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
```

### 3. Campaign Scheduler Service
**File:** `app/tasks/campaign_tasks.py`

```python
"""
Background tasks for campaign execution
"""

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.campaign import Campaign, CampaignRun
from app.models.contact import Contact
from app.models.message import Message
from app.utils.enums import CampaignStatus, MessageStatus
from datetime import datetime, timedelta

@celery_app.task
def execute_campaign_run(campaign_run_id: int):
    """Execute a scheduled campaign run"""
    db = SessionLocal()
    try:
        run = db.query(CampaignRun).filter(CampaignRun.id == campaign_run_id).first()
        if not run:
            return
        
        campaign = db.query(Campaign).filter(Campaign.id == run.campaign_id).first()
        
        # Update run status
        run.status = "RUNNING"
        run.started_at = datetime.utcnow()
        db.commit()
        
        # Get eligible contacts
        query = db.query(Contact).filter(
            Contact.jeweller_id == campaign.jeweller_id,
            Contact.opted_out == False,
            Contact.is_deleted == False
        )
        
        if campaign.sub_segment:
            query = query.filter(Contact.segment == campaign.sub_segment)
        
        contacts = query.all()
        run.eligible_contacts = len(contacts)
        db.commit()
        
        # Queue messages
        for contact in contacts:
            message = Message(
                jeweller_id=campaign.jeweller_id,
                contact_id=contact.id,
                campaign_run_id=run.id,
                phone_number=contact.phone_number,
                template_name=campaign.template.template_name,
                language=contact.preferred_language,
                message_body="",  # Render template with variables
                status=MessageStatus.QUEUED
            )
            db.add(message)
            db.flush()
            
            # Queue for sending
            send_whatsapp_message.delay(message.id)
            run.messages_queued += 1
        
        run.status = "COMPLETED"
        run.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        run.status = "FAILED"
        run.error_message = str(e)
        db.commit()
    finally:
        db.close()


@celery_app.task
def schedule_upcoming_campaigns():
    """Periodic task to schedule upcoming campaign runs"""
    db = SessionLocal()
    try:
        # Find active campaigns
        active_campaigns = db.query(Campaign).filter(
            Campaign.status == CampaignStatus.ACTIVE
        ).all()
        
        for campaign in active_campaigns:
            # Check if run needed based on recurrence
            # Create CampaignRun
            # Schedule execution
            pass
            
    finally:
        db.close()


# Schedule periodic task
celery_app.conf.beat_schedule = {
    'schedule-campaigns-every-hour': {
        'task': 'app.tasks.campaign_tasks.schedule_upcoming_campaigns',
        'schedule': 3600.0,  # Every hour
    },
}
```

### 4. Run Celery Worker

```bash
# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.celery_app beat --loglevel=info

# Or run both together
celery -A app.celery_app worker --beat --loglevel=info
```

## High Priority (Before Beta Release)

### 5. Email Service for OTP
**File:** `app/services/email_service.py`

```python
"""
Email service for sending OTPs
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(email: str, otp: str):
    """Send OTP via email"""
    # Configure SMTP settings
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "noreply@ektola.com"
    sender_password = "your-app-password"
    
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Your EkTola Login OTP"
    message["From"] = sender_email
    message["To"] = email
    
    html = f"""
    <html>
      <body>
        <h2>EkTola Login OTP</h2>
        <p>Your one-time password is: <strong>{otp}</strong></p>
        <p>This OTP will expire in 10 minutes.</p>
      </body>
    </html>
    """
    
    part = MIMEText(html, "html")
    message.attach(part)
    
    # Send email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, message.as_string())
```

Update [app/routers/auth.py](app/routers/auth.py#L127):
```python
from app.services.email_service import send_otp_email

# In request_otp function, replace:
# return {"message": "OTP sent to email", "otp": otp_code}

# With:
send_otp_email(request.email, otp_code)
return {"message": "OTP sent to email"}
```

### 6. Admin Management Endpoints
**File:** `app/routers/admin.py`

```python
"""
Admin-only endpoints for system management
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.jeweller import Jeweller

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/jewellers")
def list_jewellers(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all jewellers"""
    jewellers = db.query(Jeweller).all()
    return {"jewellers": jewellers, "total": len(jewellers)}

@router.patch("/jewellers/{jeweller_id}/approve")
def approve_jeweller(
    jeweller_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve a jeweller account"""
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    if not jeweller:
        raise HTTPException(status_code=404, detail="Jeweller not found")
    
    jeweller.is_approved = True
    db.commit()
    return {"message": "Jeweller approved", "jeweller": jeweller}
```

### 7. Database Migrations (Alembic)

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "Description of changes"
```

## Medium Priority (Nice to Have)

### 8. Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/login")
@limiter.limit("5/minute")
def login(...):
    pass
```

### 9. Logging Enhancement

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### 10. Testing Suite

```python
# File: tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register():
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "business_name": "Test Jewels",
        "phone_number": "+919999999999"
    })
    assert response.status_code == 201
    assert "access_token" in response.json()

def test_login():
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## Production Deployment Checklist

- [ ] Set up production database (managed PostgreSQL)
- [ ] Set up production Redis (managed Redis/ElastiCache)
- [ ] Configure environment variables securely (AWS Secrets Manager, etc.)
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domains
- [ ] Enable database connection pooling
- [ ] Set up application monitoring (DataDog, New Relic)
- [ ] Set up error tracking (Sentry)
- [ ] Configure log aggregation (CloudWatch, Papertrail)
- [ ] Set up CI/CD pipeline (GitHub Actions, GitLab CI)
- [ ] Configure auto-scaling
- [ ] Set up database backups
- [ ] Load testing and performance optimization
- [ ] Security audit
- [ ] Documentation for deployment

## Resources

- WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
- Celery Documentation: https://docs.celeryproject.org/
- FastAPI Best Practices: https://fastapi.tiangolo.com/tutorial/
- SQLAlchemy: https://docs.sqlalchemy.org/
