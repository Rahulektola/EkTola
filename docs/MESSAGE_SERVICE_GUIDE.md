# Running the Message Sending Service

## 🚀 Quick Start

The EkTola platform now has **complete message sending infrastructure**. Here's how to run it:

---

## Prerequisites

### 1. Redis Server

Redis is required for Celery message broker.

**Install Redis (Windows):**
```powershell
# Option 1: Using Chocolatey
choco install redis-64

# Option 2: Using WSL
wsl --install
# Then in WSL:
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

**Verify Redis is running:**
```powershell
redis-cli ping
# Should return: PONG
```

---

## Running the Services

You need to run **3 processes** simultaneously:

### Terminal 1: FastAPI Server
```powershell
cd C:\Users\halli\OneDrive\Desktop\EkTola\EkTola
```

**What it does:**
- REST API endpoints
- Campaign scheduler (checks every minute)
- Creates campaign runs automatically

---

### Terminal 2: Celery Worker
```powershell
cd C:\Users\halli\OneDrive\Desktop\EkTola\EkTola
celery -A app.celery_app worker --loglevel=info --pool=solo
```

**What it does:**
- Executes background tasks
- Sends WhatsApp messages
- Processes message queue

**Note:** Use `--pool=solo` on Windows (gevent not required)

---

### Terminal 3: Celery Beat (Scheduler)
```powershell
cd C:\Users\halli\OneDrive\Desktop\EkTola\EkTola
celery -A app.celery_app beat --loglevel=info
```

**What it does:**
- Periodic task scheduler
- Triggers `check_pending_campaigns` every minute
- Works alongside FastAPI's built-in scheduler for redundancy

---

## How It Works

### Campaign Execution Flow

```
1. User creates campaign (DRAFT)
   ↓
2. User activates campaign
   ↓
3. Scheduler checks every minute
   ↓
4. Creates CampaignRun when due
   ↓
5. Celery executes campaign_run
   ↓
6. Creates Message records for each contact
   ↓
7. Queues send_campaign_message tasks
   ↓
8. Worker sends WhatsApp messages
   ↓
9. Updates message status (SENT/FAILED)
   ↓
10. WhatsApp webhook updates final status
```

---

## Architecture

### Services Created

✅ **`app/services/whatsapp.py`** - WhatsApp Cloud API Service
- `send_template_message()` - Send template with variables
- `send_campaign_message()` - Send campaign message to contact
- `build_variables_from_contact()` - Auto-map contact data
- Development mode support (works without credentials)

✅ **`app/celery_app.py`** - Celery Configuration
- Redis broker setup
- Task routing (campaigns queue)
- Retry policies (3 retries, 60s delay)
- Beat schedule (check campaigns every minute)

✅ **`app/tasks/campaign_tasks.py`** - Background Tasks
- `execute_campaign_run(campaign_run_id)` - Execute full campaign
- `send_campaign_message(message_id)` - Send single message
- `check_pending_campaigns()` - Periodic campaign checker

✅ **`app/services/scheduler.py`** - Campaign Scheduler
- `check_and_trigger_campaigns()` - Find & trigger due campaigns
- Handles one-time and recurring campaigns
- Period detection (daily/weekly/monthly)

✅ **`app/main.py`** - FastAPI Integration
- Lifespan context manager
- Background scheduler task
- Runs scheduler every 60 seconds

---

## Development Mode

### Without WhatsApp Credentials

The system works in **development mode** without WhatsApp API credentials:

```env
# .env (empty WhatsApp values)
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
```

**Behavior:**
- Messages marked as SENT
- Message IDs are mocked: `dev_{phone}_{template}`
- No actual WhatsApp API calls
- Full workflow testing possible

---

## Production Setup

### WhatsApp Configuration

1. **Meta Business Account Setup:**
   - Go to https://business.facebook.com
   - Create Meta Business Account
   - Add WhatsApp product

2. **Get Credentials:**
   ```
   Phone Number ID: Found in WhatsApp > API Setup
   Access Token: Generate in System Users
   Business Account ID: Found in Business Settings
   ```

3. **Update `.env`:**
   ```env
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
   WHATSAPP_ACCESS_TOKEN=your_permanent_access_token_here
   WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id_here
   ```

4. **Create Templates:**
   - Go to WhatsApp Manager
   - Create message templates
   - Wait for Meta approval
   - Use approved template names in campaigns

---

## Testing Campaign Execution

### 1. Create Test Data

```bash
# API calls or use frontend
POST /contacts/upload  # Upload contacts
POST /templates/admin/  # Create template (Admin)
POST /campaigns/  # Create campaign
POST /campaigns/{id}/activate  # Activate
```

### 2. Watch Logs

**FastAPI logs:**
```
🔍 Checking 1 active campaigns
✅ Triggered campaign 'Gold Loan Reminder' (Run ID: 1)
```

**Celery Worker logs:**
```
🚀 Starting campaign run 1 for campaign 'Gold Loan Reminder'
📋 Found 50 contacts to message
✅ Message 1 sent to +919876543210
✅ Campaign run 1 completed: 50 queued, 0 failed
```

### 3. Check Database

```sql
-- View campaign runs
SELECT * FROM campaign_runs ORDER BY created_at DESC;

-- View messages
SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;

-- Check message status distribution
SELECT status, COUNT(*) FROM messages GROUP BY status;
```

---

## Campaign Types

### One-Time Campaigns
```python
recurrence_type = RecurrenceType.ONCE
start_date = "2026-02-01 10:00:00"
```
- Executes once at start_date
- Never repeats

### Daily Recurring
```python
recurrence_type = RecurrenceType.DAILY
start_date = "2026-02-01 09:00:00"
end_date = "2026-02-28 23:59:59"
```
- Executes once per day
- Continues until end_date

### Weekly Recurring
```python
recurrence_type = RecurrenceType.WEEKLY
```
- Executes once per week
- Runs every 7 days

### Monthly Recurring
```python
recurrence_type = RecurrenceType.MONTHLY
```
- Executes once per month
- Runs on the same day each month

---

## Message Status Lifecycle

```
PENDING → SENDING → SENT → DELIVERED → READ
           ↓
         FAILED
```

**Status Updates:**
1. `PENDING` - Message created in database
2. `SENDING` - Worker attempting to send
3. `SENT` - WhatsApp API accepted message
4. `DELIVERED` - WhatsApp delivered to device (webhook)
5. `READ` - User opened message (webhook)
6. `FAILED` - Error occurred (with error_message)

---

## Monitoring & Debugging

### Check Celery Queue
```powershell
# List active tasks
celery -A app.celery_app inspect active

# Check registered tasks
celery -A app.celery_app inspect registered

# View worker stats
celery -A app.celery_app inspect stats
```

### View Redis Queue
```powershell
redis-cli
> KEYS celery*
> LLEN celery
> LRANGE celery 0 10
```

### Common Issues

**Problem:** Worker not processing tasks
```powershell
# Solution: Check Redis connection
redis-cli ping

# Restart worker
# Press Ctrl+C, then rerun celery command
```

**Problem:** Messages stuck in PENDING
```powershell
# Solution: Check worker is running
celery -A app.celery_app inspect active

# Check for errors in worker logs
```

**Problem:** Scheduler not triggering campaigns
```powershell
# Solution: Check both schedulers are running
# 1. FastAPI background task (should see in uvicorn logs)
# 2. Celery Beat (separate terminal)

# Verify campaign status
SELECT id, name, status, start_date FROM campaigns;
```

---

## Performance Tuning

### Celery Worker Configuration

**For high volume (1000+ messages):**
```powershell
celery -A app.celery_app worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=4 \
    --max-tasks-per-child=100
```

**Options:**
- `--concurrency=4` - Run 4 parallel workers
- `--max-tasks-per-child=100` - Restart worker after 100 tasks (prevents memory leaks)

### Rate Limiting

WhatsApp has rate limits:
- **Tier 1:** 1,000 messages/day
- **Tier 2:** 10,000 messages/day
- **Tier 3:** 100,000 messages/day

**Add rate limiting to tasks:**
```python
# app/tasks/campaign_tasks.py
from celery import Task
from time import sleep

@celery_app.task(rate_limit='10/m')  # 10 messages per minute
def send_campaign_message(message_id: int):
    # ... existing code
    pass
```

---

## Production Deployment

### systemd Services (Linux)

**1. FastAPI Service:**
```ini
# /etc/systemd/system/ektola-api.service
[Unit]
Description=EkTola FastAPI Server

[Service]
User=www-data
WorkingDirectory=/var/www/ektola
ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

**2. Celery Worker:**
```ini
# /etc/systemd/system/ektola-worker.service
[Unit]
Description=EkTola Celery Worker

[Service]
User=www-data
WorkingDirectory=/var/www/ektola
ExecStart=/usr/bin/celery -A app.celery_app worker --loglevel=info

[Install]
WantedBy=multi-user.target
```

**3. Celery Beat:**
```ini
# /etc/systemd/system/ektola-beat.service
[Unit]
Description=EkTola Celery Beat

[Service]
User=www-data
WorkingDirectory=/var/www/ektola
ExecStart=/usr/bin/celery -A app.celery_app beat --loglevel=info

[Install]
WantedBy=multi-user.target
```

**Enable services:**
```bash
sudo systemctl enable ektola-api
sudo systemctl enable ektola-worker
sudo systemctl enable ektola-beat

sudo systemctl start ektola-api
sudo systemctl start ektola-worker
sudo systemctl start ektola-beat
```

---

## Summary

### ✅ Complete Infrastructure

1. **WhatsApp Service** - Send template messages
2. **Celery Tasks** - Background job processing
3. **Campaign Scheduler** - Automatic campaign triggering
4. **Message Tracking** - Full status lifecycle
5. **Error Handling** - Retries and error logging
6. **Development Mode** - Test without credentials

### 🚀 To Start Sending Messages:

1. **Start Redis** (if not running)
2. **Terminal 1:** `uvicorn app.main:app --reload`
3. **Terminal 2:** `celery -A app.celery_app worker --pool=solo`
4. **Terminal 3:** `celery -A app.celery_app beat`
5. **Create & activate campaign** via API
6. **Watch logs** for execution

### 📊 Message Flow:

```
Campaign Created → Activated → Scheduler Detects → 
CampaignRun Created → Celery Executes → Messages Queued → 
Worker Sends → WhatsApp Delivers → Status Updated
```

**The platform is now fully functional for sending utility messages!** 🎉
