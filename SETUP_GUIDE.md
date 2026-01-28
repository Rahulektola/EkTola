# EkTola Backend - Setup Guide

## Quick Start (Development without Database)

The application can run without a database for testing the API structure:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn app.main:app --reload

# Access Swagger UI
# Open: http://localhost:8000/docs
```

## Full Setup (With Database)

### Prerequisites
- Python 3.9+
- PostgreSQL 13+
- Redis 6+

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set Up PostgreSQL

#### Option A: Using Docker (Recommended)
```bash
# Start PostgreSQL container
docker run --name ektola-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_USER=ektola \
  -e POSTGRES_DB=ektola_db \
  -p 5432:5432 \
  -d postgres:15

# Verify it's running
docker ps
```

#### Option B: Local PostgreSQL Installation
```bash
# Windows: Download from https://www.postgresql.org/download/windows/
# Mac: brew install postgresql@15
# Linux: sudo apt install postgresql-15

# Create database
createdb -U postgres ektola_db
```

### Step 3: Set Up Redis

#### Option A: Using Docker (Recommended)
```bash
# Start Redis container
docker run --name ektola-redis \
  -p 6379:6379 \
  -d redis:7
```

#### Option B: Local Redis Installation
```bash
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# Mac: brew install redis
# Linux: sudo apt install redis-server

# Start Redis
redis-server
```

### Step 4: Configure Environment

Update your `.env` file with actual credentials:

```bash
# Database
DATABASE_URL=postgresql://ektola:yourpassword@localhost:5432/ektola_db

# Security (generate new secret key for production)
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# WhatsApp
WHATSAPP_API_VERSION=v18.0

# Environment
ENVIRONMENT=development
```

#### Generate a Secure Secret Key:
```python
# Run this in Python
import secrets
print(secrets.token_urlsafe(32))
```

### Step 5: Run the Server

```bash
# Development mode (auto-reload on code changes)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the built-in runner
python app/main.py
```

### Step 6: Verify Installation

1. **Check server is running:**
   - Open: http://localhost:8000
   - Should see: `{"message": "EkTola WhatsApp Jeweller Platform API", ...}`

2. **Check health endpoint:**
   - Open: http://localhost:8000/health
   - Should see: `{"status": "healthy", "environment": "development"}`

3. **Check API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. **Verify database tables:**
   ```bash
   # Connect to PostgreSQL
   psql -U ektola -d ektola_db
   
   # List all tables
   \dt
   
   # Should see: users, jewellers, contacts, templates, template_translations, 
   # campaigns, campaign_runs, messages, webhook_events
   ```

## Testing the API

### 1. Register a Jeweller

Using Swagger UI (http://localhost:8000/docs):

1. Go to **POST /auth/register**
2. Click "Try it out"
3. Fill in the request body:
```json
{
  "email": "jeweller@example.com",
  "password": "SecurePass123",
  "business_name": "Golden Jewels",
  "phone_number": "+919876543210"
}
```
4. Click "Execute"
5. Copy the `access_token` from the response

### 2. Authorize with Token

1. Click the "Authorize" button at the top
2. Paste your token: `Bearer your_access_token_here`
3. Click "Authorize"

### 3. Test Protected Endpoints

Now you can test authenticated endpoints like:
- GET /auth/me - Get your profile
- POST /contacts - Create a contact
- GET /contacts - List contacts
- GET /templates - View available templates

## Database Schema

The following tables are automatically created:

### Core Tables
- **users** - Authentication (email + password/OTP)
- **jewellers** - Business profiles and WhatsApp credentials
- **contacts** - Customer contacts (tenant-isolated)

### Messaging Tables
- **templates** - WhatsApp message templates
- **template_translations** - Multi-language template content
- **campaigns** - Campaign configuration
- **campaign_runs** - Individual campaign executions
- **messages** - Message tracking and status

### System Tables
- **webhook_events** - WhatsApp webhook event log

## Troubleshooting

### Database Connection Error
```
OperationalError: connection to server at "localhost" failed
```

**Solution:**
- Ensure PostgreSQL is running: `docker ps` or `systemctl status postgresql`
- Check DATABASE_URL in .env matches your credentials
- For Docker: Use host.docker.internal instead of localhost if running app in Docker

### Import Errors
```
ModuleNotFoundError: No module named 'app'
```

**Solution:**
- Ensure you're in the project root directory
- Run: `python -m uvicorn app.main:app --reload`
- Or: `cd EkTola && uvicorn app.main:app --reload`

### Port Already in Use
```
OSError: [Errno 98] Address already in use
```

**Solution:**
- Kill process on port 8000: 
  - Windows: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
  - Linux/Mac: `lsof -ti:8000 | xargs kill -9`
- Or use a different port: `uvicorn app.main:app --port 8001`

### Redis Connection Error
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:**
- Start Redis: `docker start ektola-redis` or `redis-server`
- Check Redis is accessible: `redis-cli ping` (should return PONG)

## Next Steps

1. **Add Admin User** (requires database access):
```sql
-- Connect to database
psql -U ektola -d ektola_db

-- Create admin user
INSERT INTO users (email, hashed_password, is_active, is_admin, created_at, updated_at)
VALUES (
  'admin@ektola.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5jtJ9uKvdH6Oe',  -- password: admin123
  true,
  true,
  NOW(),
  NOW()
);
```

2. **Create Sample Templates** (using admin account)

3. **Implement WhatsApp Integration** (see PROJECT_STATUS.md)

4. **Set up Celery Workers** for background tasks

5. **Deploy to Production** (see deployment guide)

## Development Commands

```bash
# Run server
python -m uvicorn app.main:app --reload

# Run with specific host/port
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Run tests (when implemented)
pytest

# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## API Endpoints Summary

### Authentication (`/auth`)
- POST /register - Register jeweller
- POST /login - Login with password
- POST /otp/request - Request OTP
- POST /otp/verify - Verify OTP
- POST /refresh - Refresh token
- GET /me - Current user profile
- GET /me/jeweller - Jeweller profile

### Contacts (`/contacts`)
- POST /upload - Bulk import
- POST / - Create contact
- GET / - List contacts
- GET /{id} - Get contact
- PATCH /{id} - Update contact
- DELETE /{id} - Delete contact

### Campaigns (`/campaigns`)
- POST / - Create campaign
- GET / - List campaigns
- GET /{id} - Campaign details
- PATCH /{id} - Update campaign
- POST /{id}/activate - Activate
- POST /{id}/pause - Pause

### Templates (`/templates`)
- GET / - List templates (jeweller)
- GET /{id} - Template details
- Admin endpoints for CRUD

### Analytics (`/analytics`)
- GET /dashboard - Jeweller dashboard
- GET /admin/dashboard - Admin dashboard

### Webhooks (`/webhooks`)
- POST /whatsapp - WhatsApp webhook
- GET /whatsapp - Webhook verification

## Support

For issues or questions:
- Check PROJECT_STATUS.md for implementation status
- Check logs: Uvicorn logs in terminal
- Check database: psql connection for data verification
- API documentation: http://localhost:8000/docs
