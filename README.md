# OUTDATED DO NOT REFER THIS FILE

**Status:** ✅ **Backend Complete - Message Sending Service Operational**

## Overview
FastAPI backend for a multi-tenant WhatsApp messaging platform for jewellers. Supports contact management, campaign scheduling, automated message delivery, and tracking.

## ✨ Key Features

✅ **Complete Backend Infrastructure**
- 34 REST API endpoints
- PostgreSQL database (9 tables)
- JWT authentication (email/phone + OTP)
- Multi-tenant architecture

✅ **Contact Management**
- Bulk upload (CSV/XLSX)
- Segment-based filtering
- Soft deletes

✅ **Campaign Management**
- One-time & recurring campaigns
- Automatic scheduling
- Template-based messaging

✅ **Message Sending Service** 🎉
- WhatsApp Cloud API integration
- Background task processing (Celery)
- Variable replacement & personalization
- Automatic retries
- Status tracking (PENDING → SENT → DELIVERED → READ)

## Tech Stack
- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT (email + OTP or password)
- **Task Queue**: Celery + Redis ✅ **Implemented**
- **Messaging**: WhatsApp Cloud API ✅ **Integrated**
- **File Processing**: Pandas, OpenPyXL

## Project Structure
```
app/
├── main.py                 # FastAPI app entry point + scheduler
├── config.py               # Settings & environment variables
├── database.py             # Database connection & session
├── celery_app.py          # ✅ Celery configuration
├── models/                 # SQLAlchemy models (9 tables)
│   ├── user.py
│   ├── jeweller.py
│   ├── contact.py
│   ├── template.py
│   ├── campaign.py
│   ├── message.py
│   └── webhook.py
├── schemas/                # Pydantic request/response schemas
│   ├── auth.py
│   ├── contact.py
│   ├── campaign.py
│   ├── template.py
│   ├── message.py
│   └── analytics.py
├── routers/                # API endpoints (34 endpoints)
│   ├── auth.py
│   ├── contacts.py
│   ├── campaigns.py
│   ├── templates.py
│   ├── analytics.py
│   └── webhooks.py
├── services/              # ✅ Business logic services
│   ├── whatsapp.py        # WhatsApp Cloud API service
│   └── scheduler.py       # Campaign scheduler
├── tasks/                 # ✅ Celery background tasks
│   └── campaign_tasks.py  # Message sending tasks
├── core/                  # Security & dependencies
│   ├── security.py        # JWT utilities
│   └── dependencies.py    # Auth dependencies
└── utils/
    ├── enums.py           # Shared enums
    └── whatsapp.py        # WhatsApp utilities
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Redis
```powershell
# Windows (using Chocolatey)
choco install redis-64

# Or use WSL
wsl --install
# In WSL:
sudo apt install redis-server
sudo service redis-server start

# Verify
redis-cli ping  # Should return: PONG
```

### 3. Environment Variables
Copy `.env.example` to `.env` and configure:
```env
# Database
DATABASE_URL=postgresql://ektola_user:ektola2024@localhost:5432/ektola_db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# WhatsApp (optional for development)
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_OTP_TEMPLATE_NAME=otp_verification

# Environment
ENVIRONMENT=development

# Admin
ADMIN_ACCESS_CODE=your_admin_code
```

### 4. Run Database Migrations
```bash
# Tables auto-created on startup
# Or use Alembic for production:
alembic upgrade head
```

### 5. Run the Services

**You need to run 3 processes simultaneously:**

**Terminal 1: FastAPI Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2: Celery Worker**
```bash
celery -A app.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3: Celery Beat (Scheduler)**
```bash
celery -A app.celery_app beat --loglevel=info
```

### 6. Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📚 Complete Documentation

- **[MESSAGE_SERVICE_GUIDE.md](MESSAGE_SERVICE_GUIDE.md)** - Complete guide for running message sending services
- **[FRONTEND_CONTRACT.md](FRONTEND_CONTRACT.md)** - API contract for frontend integration
- OpenAPI JSON: http://localhost:8000/openapi.json

## Database Models

### Core Models
1. **User** - Authentication (email + password/OTP)
2. **Jeweller** - Tenant entity with WhatsApp Business Account details
3. **Contact** - Customer contacts (tenant-isolated, unique phone per jeweller)
4. **Template** - WhatsApp message templates (admin-managed)
5. **TemplateTranslation** - Language-specific template content
6. **Campaign** - Messaging campaigns (utility/marketing)
7. **CampaignRun** - Individual campaign execution instances
8. **Message** - Individual WhatsApp messages with status tracking
9. **WebhookEvent** - WhatsApp webhook event log

### Key Features
- **Tenant Isolation**: All jeweller data is strictly isolated via `jeweller_id` foreign key
- **Soft Deletes**: Contacts use `is_deleted` flag
- **Indexes**: Optimized for queries on `jeweller_id`, `segment`, `status`, `phone_number`

## API Authentication

All endpoints (except `/auth/*` and `/webhooks/whatsapp`) require JWT authentication.

### Header Format
```
Authorization: Bearer <access_token>
```

### Token Payload
```json
{
  "user_id": 123,
  "email": "jeweller@example.com",
  "is_admin": false,
  "jeweller_id": 45,
  "exp": 1706112000,
  "type": "access"
}
```

### Token Lifetime
- Access token: 30 minutes
- Refresh token: 7 days

## API Endpoints Summary

### Authentication (`/auth`)
- `POST /auth/register` - Register jeweller
- `POST /auth/login` - Login with email/password
- `POST /auth/otp/request` - Request OTP
- `POST /auth/otp/verify` - Verify OTP & login
- `GET /auth/me` - Get current user profile
- `GET /auth/me/jeweller` - Get jeweller profile

### Contacts (`/contacts`)
- `POST /contacts/upload` - Bulk upload CSV/XLSX
- `POST /contacts/` - Create single contact
- `GET /contacts/` - List contacts (paginated, filterable)
- `GET /contacts/stats` - Contact distribution by segment
- `GET /contacts/{id}` - Get contact details
- `PATCH /contacts/{id}` - Update contact
- `DELETE /contacts/{id}` - Soft delete contact

### Campaigns (`/campaigns`)
- `POST /campaigns/` - Create campaign
- `GET /campaigns/` - List campaigns
- `GET /campaigns/{id}` - Get campaign details
- `PATCH /campaigns/{id}` - Update campaign
- `POST /campaigns/{id}/activate` - Activate draft campaign
- `POST /campaigns/{id}/pause` - Pause active campaign
- `POST /campaigns/{id}/resume` - Resume paused campaign
- `GET /campaigns/{id}/runs` - Get run history
- `GET /campaigns/{id}/stats` - Get campaign statistics
- `DELETE /campaigns/{id}` - Delete campaign

### Templates (`/templates`)
**Jeweller:**
- `GET /templates/` - List available templates
- `GET /templates/{id}` - Get template details

**Admin:**
- `GET /templates/admin/all` - List all templates
- `POST /templates/admin/` - Create template
- `PATCH /templates/admin/{id}` - Update template
- `DELETE /templates/admin/{id}` - Deactivate template

### Analytics (`/analytics`)
**Jeweller:**
- `GET /analytics/dashboard` - Jeweller dashboard

**Admin:**
- `GET /analytics/admin/dashboard` - Admin dashboard
- `GET /analytics/admin/detailed` - Detailed analytics

### Webhooks (`/webhooks`)
- `POST /webhooks/whatsapp` - WhatsApp status updates
- `GET /webhooks/whatsapp` - Webhook verification

## Enums

### SegmentType (MVP Locked)
- `GOLD_LOAN`
- `GOLD_SIP`
- `MARKETING`

### CampaignType
- `UTILITY`
- `MARKETING`

### CampaignStatus
- `DRAFT`
- `ACTIVE`
- `PAUSED`
- `COMPLETED`

### MessageStatus
- `QUEUED`
- `SENT`
- `DELIVERED`
- `READ`
- `FAILED`

### RecurrenceType
- `DAILY`
- `WEEKLY`
- `MONTHLY`
- `ONE_TIME`

### Language
- `en` (English)
- `hi` (Hindi)
- `kn` (Kannada)
- `ta` (Tamil)
- `pa` (Punjabi)

## Development Notes

### TODO: Not Yet Implemented
1. **Celery Workers** - Background job processing for:
   - Campaign scheduling
   - Message sending
   - Contact import processing
2. **WhatsApp Cloud API Integration** - Actual message sending
3. **Email Service** - OTP delivery
4. **Rate Limiting** - Per jeweller/WABA
5. **Admin Approval Workflow** - Jeweller activation
6. **File Upload Progress** - Async upload with status polling

### Security Considerations
- Store WhatsApp access tokens encrypted
- Implement rate limiting
- Add request validation
- Secure webhook verify_token
- Use HTTPS in production
- Restrict CORS origins

## Testing
```bash
# Run tests (when implemented)
pytest

# Check coverage
pytest --cov=app
```

## License
Proprietary - EkTola Platform
