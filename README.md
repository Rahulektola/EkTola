# EkTola - WhatsApp Jeweller Platform Backend

## Overview
FastAPI backend for a multi-tenant WhatsApp messaging platform for jewellers. Supports contact management, campaign scheduling, and message delivery tracking.

## Tech Stack
- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT (email + OTP or password)
- **Task Queue**: Celery + Redis
- **File Processing**: Pandas, OpenPyXL

## Project Structure
```
app/
├── main.py                 # FastAPI app entry point
├── config.py               # Settings & environment variables
├── database.py             # Database connection & session
├── models/                 # SQLAlchemy models
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
├── routers/                # API endpoints
│   ├── auth.py
│   ├── contacts.py
│   ├── campaigns.py
│   ├── templates.py
│   ├── analytics.py
│   └── webhooks.py
├── core/                   # Security & dependencies
│   ├── security.py         # JWT utilities
│   └── dependencies.py     # Auth dependencies
└── utils/
    └── enums.py            # Shared enums
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/ektola_db
SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379/0
```

### 3. Run Database Migrations
```bash
# Auto-create tables (development only)
# Tables are created automatically on app start via Base.metadata.create_all()

# For production, use Alembic:
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4. Run the Server
```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
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
