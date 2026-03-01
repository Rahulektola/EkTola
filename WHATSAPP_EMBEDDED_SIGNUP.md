# WhatsApp Embedded Signup Integration

**Date:** February 24, 2026  
**Status:** 🚧 In Implementation  
**Architecture:** Multi-Tenant Partner Model

---

## Overview

This implementation enables jewellers to connect their own WhatsApp Business Accounts (WABA) to the platform using Facebook's Embedded Signup flow. The platform operates as a **Business Solution Provider (BSP)**, managing multiple jeweller WhatsApp accounts under a shared credit line while maintaining a platform account for authentication OTPs.

### Architecture Model
- **Multi-Tenant**: Each jeweller owns their WABA
- **Partner Model**: Jewellers as partners under platform's Business Portfolio
- **Dual WhatsApp Mode**: 
  - Platform account → Authentication OTPs, admin notifications
  - Jeweller accounts → Marketing campaigns, customer communications
- **Post-Registration**: Optional WhatsApp connection after jeweller signup

---

## Backend Changes Summary

### 1. Database Schema Changes
**File:** `app/models/jeweller.py`

**New Fields Added:**
```python
# Facebook/Meta Integration
fb_app_scoped_user_id = Column(String(255), nullable=True)      # Facebook User ID
access_token_expires_at = Column(DateTime, nullable=True)        # Token expiry
waba_name = Column(String(255), nullable=True)                   # Business name from Meta
phone_display_number = Column(String(50), nullable=True)         # Human-readable phone
business_verification_status = Column(String(50), nullable=True) # verified|pending|unverified
whatsapp_connected_at = Column(DateTime, nullable=True)          # Connection timestamp
last_token_refresh = Column(DateTime, nullable=True)             # Last refresh time
```

**Existing Fields Retained:**
- `waba_id`, `phone_number_id`, `access_token`, `webhook_verify_token`

**Migration:** Alembic migration required for schema updates

---

### 2. Token Encryption System
**File:** `app/core/encryption.py` (NEW)

**Purpose:** Secure storage of WhatsApp access tokens

**Functions:**
- `encrypt_token(plaintext: str) -> str` - Encrypt before database storage
- `decrypt_token(ciphertext: str) -> str` - Decrypt for API calls

**Implementation:** Uses Fernet (cryptography library) with key from `WHATSAPP_TOKEN_ENCRYPTION_KEY` environment variable

**Security:** All access tokens encrypted at rest in database

---

### 3. WhatsApp Authentication Router
**File:** `app/routers/whatsapp_auth.py` (NEW)

**Endpoints:**

#### GET `/auth/whatsapp/config`
- **Auth:** JWT required (jeweller user)
- **Purpose:** Generate Facebook SDK configuration
- **Returns:**
  ```json
  {
    "appId": "2416144582179119",
    "configId": "your-config-id",
    "redirectUri": "https://yourdomain.com/auth/whatsapp/callback",
    "state": "signed-jwt-token"
  }
  ```
- **State Token:** Contains `{jeweller_id, user_id, timestamp, nonce}` signed with platform secret

#### POST `/auth/whatsapp/callback`
- **Auth:** Public (validates state token internally)
- **Purpose:** Complete Embedded Signup flow
- **Input:**
  - `code`: Authorization code from Facebook
  - `state`: State token from config endpoint
- **Process:**
  1. Validate and decode state token
  2. Exchange code for access token (Meta Graph API)
  3. Request long-lived token (60-day validity)
  4. Fetch WABA details via Graph API
  5. Fetch phone number details
  6. Encrypt and store all credentials
  7. Generate unique webhook verify token
  8. Subscribe WABA to platform webhooks
  9. Send admin notification
- **Returns:**
  ```json
  {
    "success": true,
    "waba_id": "123456789012345",
    "phone_display_number": "+91 98765 43210",
    "business_name": "XYZ Jewellers"
  }
  ```

#### DELETE `/auth/whatsapp/disconnect`
- **Auth:** JWT required (jeweller user)
- **Purpose:** Disconnect WhatsApp account
- **Process:** Nullify all WhatsApp fields, log event
- **Returns:** Success confirmation

**External API Calls:**
- `POST /oauth/access_token` - Token exchange
- `GET /debug_token` - Validate token and get WABA ID
- `GET /{waba_id}` - Get business account details
- `GET /{waba_id}/phone_numbers` - Get phone numbers
- `POST /{waba_id}/subscribed_apps` - Subscribe to webhooks

---

### 4. Configuration Updates
**File:** `app/config.py`

**New Settings:**
```python
# Token Encryption
WHATSAPP_TOKEN_ENCRYPTION_KEY: str  # Fernet key for token encryption

# Facebook Embedded Signup
FACEBOOK_CONFIG_ID: str             # Embedded Signup configuration ID
WHATSAPP_CALLBACK_BASE_URL: str     # Base URL for OAuth callbacks
```

**Usage:**
- Generate encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Set in `.env`: `WHATSAPP_TOKEN_ENCRYPTION_KEY=your-generated-key`

---

### 5. Multi-Tenant WhatsApp Service
**File:** `app/services/whatsapp_service.py`

**Major Refactor:**

#### New: Per-Jeweller Client Factory
```python
def get_whatsapp_client(jeweller_id: int, db: Session) -> WhatsApp:
    """Get WhatsApp client for specific jeweller"""
    # Fetch jeweller credentials
    # Decrypt access token
    # Check expiry, refresh if needed
    # Return WhatsApp client instance
```

#### New: Platform Client (Separate)
```python
def get_platform_whatsapp_client() -> WhatsApp:
    """Get platform WhatsApp client for OTPs/admin messages"""
    # Uses global platform credentials
```

#### New: Admin Notification
```python
async def send_admin_notification(
    jeweller_id: int,
    event: str,
    db: Session
) -> bool:
    """Send notification to all admins via platform WhatsApp"""
    # Fetch admin phone numbers
    # Use platform client
    # Send notification message
```

**Updated Methods:**
- All campaign sending methods now accept `jeweller_id` and use per-jeweller client
- Token refresh logic before API calls
- Error handling for missing credentials

**Backward Compatibility:**
- Platform OTP methods continue using global client
- No breaking changes to existing OTP flow

---

### 6. Enhanced Webhook Router
**File:** `app/routers/webhooks.py`

**Updates:**

#### GET `/webhooks/whatsapp` (Verification)
**Before:** Single verify token match
**After:** Multi-jeweller token matching
- Extract `hub.verify_token` from query params
- Query database for matching jeweller
- Fallback to platform token
- Return `hub.challenge` if match found

**Logic:**
```python
verify_token = request.query_params.get("hub.verify_token")

# Try jeweller-specific tokens
jeweller = db.query(Jeweller).filter(
    Jeweller.webhook_verify_token == verify_token
).first()

if jeweller:
    return int(request.query_params.get("hub.challenge"))

# Fallback to platform token
if verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
    return int(request.query_params.get("hub.challenge"))
```

#### POST `/webhooks/whatsapp` (Callbacks)
**Before:** Global message status updates
**After:** Jeweller-specific routing
- Extract `phone_number_id` from webhook payload
- Query jeweller by `phone_number_id`
- Route to correct jeweller's message handler
- Update message status with jeweller context

**Payload Identification:**
```python
phone_number_id = payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]

jeweller = db.query(Jeweller).filter(
    Jeweller.phone_number_id == phone_number_id
).first()
```

---

### 7. Token Refresh Task
**File:** `app/tasks/token_refresh.py` (NEW)

**Purpose:** Automatically refresh expiring WhatsApp access tokens

**Celery Task:**
```python
@celery.task(name="refresh_whatsapp_tokens")
def refresh_expiring_tokens():
    """Run daily to refresh tokens expiring within 7 days"""
    # Query jewellers with expiring tokens
    # For each: Call Meta API token exchange
    # Update encrypted access_token
    # Update access_token_expires_at
    # Update last_token_refresh
    # Log success/failure
```

**Schedule:** Daily at 2:00 AM (configured in `app/celery_app.py`)

**Meta API Call:**
```
GET /oauth/access_token?grant_type=fb_exchange_token
    &client_id={app_id}
    &client_secret={app_secret}
    &fb_exchange_token={current_token}
```

**Error Handling:**
- Log failures to database
- Send admin notification on failures
- Continue processing other jewellers

---

### 8. Admin Router Updates
**File:** `app/routers/admin.py`

**New Endpoint:**

#### GET `/admin/jewellers/{jeweller_id}/whatsapp-status`
- **Auth:** Admin only
- **Purpose:** View jeweller's WhatsApp connection status
- **Returns:**
  ```json
  {
    "connected": true,
    "waba_id": "123456789012345",
    "waba_name": "XYZ Jewellers",
    "phone_number_id": "109876543210",
    "phone_display_number": "+91 98765 43210",
    "business_verification_status": "verified",
    "connected_at": "2026-02-24T10:30:00Z",
    "token_expires_at": "2026-04-25T10:30:00Z",
    "token_expires_in_days": 60,
    "last_token_refresh": "2026-02-24T10:30:00Z"
  }
  ```

**Updated Endpoint:**

#### PUT `/admin/jewellers/{jeweller_id}/meta-status`
- **Addition:** Encrypt `access_token` before storage
- **Addition:** Set `whatsapp_connected_at` timestamp
- **Addition:** Validate token with Meta API before saving

---

### 9. Schema Updates
**File:** `app/schemas/auth.py`

**New Schemas:**
```python
class WhatsAppConfigResponse(BaseModel):
    appId: str
    configId: str
    redirectUri: str
    state: str

class WhatsAppCallbackRequest(BaseModel):
    code: str
    state: str

class WhatsAppCallbackResponse(BaseModel):
    success: bool
    waba_id: Optional[str]
    phone_display_number: Optional[str]
    business_name: Optional[str]
    error: Optional[str]
```

**File:** `app/schemas/admin.py`

**New Schema:**
```python
class WhatsAppStatusResponse(BaseModel):
    connected: bool
    waba_id: Optional[str]
    waba_name: Optional[str]
    phone_number_id: Optional[str]
    phone_display_number: Optional[str]
    business_verification_status: Optional[str]
    connected_at: Optional[datetime]
    token_expires_at: Optional[datetime]
    token_expires_in_days: Optional[int]
    last_token_refresh: Optional[datetime]
```

---

### 10. Dependencies Update
**File:** `requirements.txt`

**Added:**
```
cryptography>=42.0.0  # For Fernet token encryption
httpx>=0.27.0         # Already exists, verify version
```

**Existing Dependencies Used:**
- `pywa-async>=3.8.0` - WhatsApp Cloud API client
- `SQLAlchemy>=2.0.0` - ORM with new columns
- `celery>=5.3.0` - Token refresh task
- `PyJWT>=2.8.0` - State token signing

---

## Callback URLs

### OAuth Callback
**URL:** `https://yourdomain.com/auth/whatsapp/callback`
**Configure In:** Facebook App Dashboard → Products → WhatsApp → Configuration

### Webhook URL
**URL:** `https://yourdomain.com/webhooks/whatsapp`
**Configure In:** Facebook App Dashboard → Products → WhatsApp → Webhooks
**Subscriptions:** `messages`, `message_status`, `message_template_status_update`

### Redirect URI Whitelist
**Add to:** Facebook App Dashboard → Settings → Basic → App Domains
- `yourdomain.com`
- `www.yourdomain.com`
- Development: `localhost:8000`, `127.0.0.1:8000`

---

## Database Migration Required

**Create migration:**
```bash
# Generate migration
alembic revision --autogenerate -m "add_whatsapp_embedded_signup_fields"

# Review migration file
# Edit if needed (especially for encrypted field migration)

# Apply migration
alembic upgrade head
```

**Manual Migration Steps:**
1. Add new columns to `jewellers` table
2. All new columns nullable=True (backward compatible)
3. Existing jewellers retain NULL values (can connect later)
4. No data migration required

---

## Security Considerations

### Token Encryption
- **Algorithm:** Fernet (AES-128-CBC with HMAC)
- **Key Storage:** Environment variable only, never committed
- **Rotation:** Change `WHATSAPP_TOKEN_ENCRYPTION_KEY` requires re-encryption of all tokens

### State Token
- **Signing:** HMAC-SHA256 with platform secret
- **Expiry:** 10-minute validity
- **One-time Use:** Validated and consumed immediately

### Token Refresh
- **Automatic:** Runs daily for tokens expiring within 7 days
- **Monitoring:** Logs all refresh attempts
- **Failure Handling:** Admin notification on failures

### Webhook Verification
- **Signature Validation:** Meta webhook signature verification
- **Token Validation:** Per-jeweller verify token matching
- **Platform Fallback:** Platform token for OTP webhooks

---

## Testing Checklist

### Backend Testing
- [ ] Token encryption/decryption functionality
- [ ] Embedded Signup config endpoint returns valid state
- [ ] Callback endpoint exchanges code for token
- [ ] Long-lived token storage and expiry calculation
- [ ] Multi-jeweller webhook verification
- [ ] Webhook payload routing by phone_number_id
- [ ] Token refresh task identifies expiring tokens
- [ ] Token refresh successfully updates credentials
- [ ] Admin notification sends on connection
- [ ] Admin WhatsApp status endpoint returns correct data

### Integration Testing
- [ ] Complete Embedded Signup flow (sandbox mode)
- [ ] Send campaign message from jeweller account
- [ ] Receive webhook callback and update message status
- [ ] Platform OTP still uses platform account
- [ ] Token refresh maintains campaign functionality
- [ ] Disconnect removes credentials cleanly
- [ ] Reconnect with different WABA works

### Load Testing
- [ ] Multiple concurrent Embedded Signup flows
- [ ] Webhook handling for multiple jewellers simultaneously
- [ ] Token refresh for 100+ jewellers
- [ ] Campaign sending from 50+ jeweller accounts

---

## Rollback Plan

### If Issues Occur
1. **Disable Embedded Signup UI** - Remove frontend buttons
2. **Fallback to Manual Configuration** - Use existing admin meta-status endpoint
3. **Platform Mode** - All jewellers use platform account temporarily
4. **Database Rollback** - Alembic downgrade if schema issues

### Database Rollback
```bash
# Downgrade one version
alembic downgrade -1

# Or downgrade to specific version
alembic downgrade <previous_revision_id>
```

---

## Future Enhancements

### Phase 2 (Optional)
- [ ] System User Token support for permanent access
- [ ] Business Manager integration for team management
- [ ] Template approval status sync from Meta
- [ ] Phone number quality rating monitoring
- [ ] Billing integration (track message costs per jeweller)
- [ ] WhatsApp Business Profile management from UI
- [ ] Message template creation via UI (submit for approval)

### Phase 3 (Advanced)
- [ ] Multi-phone number support per jeweller
- [ ] Shared WABA mode (some jewellers share, some own)
- [ ] WhatsApp Commerce API integration
- [ ] Payment reminders via WhatsApp Pay
- [ ] Conversational messaging (two-way chat)
- [ ] WhatsApp Flows (interactive forms)

---

## Support & Troubleshooting

### Common Issues

**Issue:** "Token exchange failed"
- **Check:** Facebook App credentials in config
- **Check:** Code hasn't expired (10-minute validity)
- **Check:** Network connectivity to graph.facebook.com

**Issue:** "Webhook verification failed"
- **Check:** Verify token saved correctly in database
- **Check:** Webhook endpoint accessible publicly
- **Check:** HTTPS certificate valid

**Issue:** "Campaign not sending from jeweller account"
- **Check:** Token not expired
- **Check:** WABA phone number verified with Meta
- **Check:** Template approved for use
- **Check:** Jeweller's message quota not exceeded

### Logging
- Enable debug logging: `LOG_LEVEL=DEBUG` in .env
- Check logs: `app/logs/whatsapp_auth.log`
- Celery task logs: `app/logs/celery.log`

### Meta API Rate Limits
- **Token exchange:** 200 calls/hour per app
- **Graph API:** 200 calls/hour per user (per jeweller)
- **Webhook subscriptions:** No limit

---

## Implementation Status

**Completed:**
- [x] Architecture design
- [x] Documentation

**In Progress:**
- [ ] Backend implementation
- [ ] Database migration
- [ ] Frontend integration

**Pending:**
- [ ] Testing
- [ ] Deployment

**Last Updated:** February 24, 2026
