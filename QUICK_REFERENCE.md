# 🚀 Quick Reference Guide - Dual Authentication System

## API Endpoints

### **Jeweller Endpoints (WhatsApp OTP)**

#### Register New Jeweller
```http
POST /auth/jeweller/request-signup-otp
Content-Type: application/json

{
  "phone_number": "+919876543210"
}
```

```http
POST /auth/jeweller/register
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "otp_code": "123456",
  "business_name": "Gold Palace Jewellers",
  "owner_name": "Rajesh Kumar",
  "email": "contact@goldpalace.com"
}
```

#### Jeweller Login
```http
POST /auth/jeweller/request-otp
Content-Type: application/json

{
  "phone_number": "+919876543210"
}
```

```http
POST /auth/jeweller/verify-otp
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "otp_code": "123456"
}

Response:
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_type": "jeweller",
  "user": {
    "id": 1,
    "business_name": "Gold Palace Jewellers",
    "phone_number": "+919876543210",
    "is_verified": true,
    "is_approved": false
  }
}
```

#### Get Jeweller Profile
```http
GET /auth/me/jeweller
Authorization: Bearer <jeweller_token>
```

---

### **Admin Endpoints (Email/Password)**

#### Admin Login
```http
POST /auth/admin/login
Content-Type: application/json

{
  "email": "admin@ektola.com",
  "password": "SecurePassword123"
}

Response:
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_type": "admin",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "admin@ektola.com",
    "role": "super_admin",
    "can_manage_jewellers": true,
    "can_view_analytics": true,
    "can_manage_templates": true
  }
}
```

#### Register New Admin (Super Admin Only)
```http
POST /auth/admin/register
Authorization: Bearer <super_admin_token>
Content-Type: application/json

{
  "full_name": "Jane Smith",
  "email": "jane@ektola.com",
  "password": "SecurePassword123",
  "phone_number": "+919876543211",
  "role": "admin"
}
```

#### Get Admin Profile
```http
GET /auth/me/admin
Authorization: Bearer <admin_token>
```

---

## Using Authentication in Code

### **Protect Jeweller Endpoints**
```python
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_jeweller
from app.models.jeweller import Jeweller

router = APIRouter()

@router.get("/my-campaigns")
def get_my_campaigns(
    current_jeweller: Jeweller = Depends(get_current_jeweller)
):
    # Only authenticated and approved jewellers can access
    return {
        "jeweller_id": current_jeweller.id,
        "business": current_jeweller.business_name
    }
```

### **Protect Admin Endpoints**
```python
from app.core.dependencies import get_current_admin
from app.models.admin import Admin

@router.get("/all-jewellers")
def list_all_jewellers(
    current_admin: Admin = Depends(get_current_admin)
):
    # Only admins can access
    return {"message": f"Admin {current_admin.full_name} viewing jewellers"}
```

### **Super Admin Only**
```python
from app.core.dependencies import get_current_super_admin

@router.post("/create-admin")
def create_new_admin(
    super_admin: Admin = Depends(get_current_super_admin)
):
    # Only super admins can access
    pass
```

### **Accept Both Types**
```python
from app.core.dependencies import get_current_user
from typing import Union

@router.get("/health")
def health_check(
    current_user: Union[Jeweller, Admin] = Depends(get_current_user)
):
    user_type = "jeweller" if isinstance(current_user, Jeweller) else "admin"
    return {"status": "healthy", "user_type": user_type}
```

---

## Token Information

### **Jeweller Token**
- **Expiry:** 30 days
- **Type:** `jeweller`
- **Contains:** `sub` (ID), `user_type`, `phone`, `business_name`

### **Admin Token**
- **Expiry:** 8 hours
- **Type:** `admin`
- **Contains:** `sub` (ID), `user_type`, `role`, `email`

---

## OTP Configuration

### **OTP Settings**
- **Length:** 6 digits
- **Expiry:** 10 minutes
- **Max Attempts:** 3
- **Single Use:** Yes

### **OTP Format (WhatsApp Message)**
```
🔐 EkTola Login OTP

Your verification code is: *123456*

Valid for 10 minutes.

⚠️ Do not share this code with anyone.
```

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ektola

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ACCESS_TOKEN_EXPIRE_DAYS=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# WhatsApp API
WHATSAPP_API_VERSION=v18.0
PLATFORM_WHATSAPP_TOKEN=EAABs...your_token
PLATFORM_PHONE_NUMBER_ID=1234567890

# Environment
ENVIRONMENT=development
```

---

## Database Models

### **Admin Model**
```python
class Admin:
    id: int
    full_name: str
    email: str
    phone_number: Optional[str]
    hashed_password: str
    role: AdminRole  # SUPER_ADMIN, ADMIN, SUPPORT
    is_active: bool
    can_manage_jewellers: bool
    can_view_analytics: bool
    can_manage_templates: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime
```

### **Jeweller Model**
```python
class Jeweller:
    id: int
    business_name: str
    owner_name: Optional[str]
    email: Optional[str]
    phone_number: str  # Required, unique
    waba_id: Optional[str]
    phone_number_id: Optional[str]
    access_token: Optional[str]
    is_approved: bool
    is_active: bool
    is_verified: bool  # Phone verified via OTP
    onboarding_completed: bool
    timezone: str
    created_at: datetime
    updated_at: datetime
    last_login: datetime
```

### **OTP Model**
```python
class OTP:
    id: int
    phone_number: str
    otp_code: str  # 6 digits
    purpose: OTPPurpose  # LOGIN, SIGNUP, RESET_PASSWORD
    is_verified: bool
    is_expired: bool
    created_at: datetime
    expires_at: datetime
    verified_at: Optional[datetime]
    attempts: int
    max_attempts: int
```

---

## Testing with cURL

### **Test Jeweller OTP Flow**
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8000/auth/jeweller/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'

# Step 2: Check WhatsApp for OTP

# Step 3: Verify OTP and login
curl -X POST http://localhost:8000/auth/jeweller/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "otp_code": "123456"
  }'

# Step 4: Use token to access protected endpoint
curl -X GET http://localhost:8000/auth/me/jeweller \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### **Test Admin Login**
```bash
# Login
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ektola.com",
    "password": "your_password"
  }'

# Access admin endpoint
curl -X GET http://localhost:8000/auth/me/admin \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Common Tasks

### **Create First Super Admin**
```bash
python create_super_admin.py
```

### **List Existing Admins**
```bash
python create_super_admin.py --list
```

### **Generate Secret Key**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### **Run Migrations**
```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Check current version
alembic current
```

---

## Error Codes

| Code | Message | Reason |
|------|---------|--------|
| 400 | Phone number not registered | Jeweller doesn't exist |
| 400 | Phone number already registered | Duplicate registration attempt |
| 401 | Invalid or expired OTP | Wrong OTP or expired |
| 401 | Could not validate credentials | Invalid token |
| 403 | Jeweller account pending approval | Admin hasn't approved yet |
| 403 | Admin access required | Jeweller trying to access admin endpoint |
| 403 | Super admin access required | Regular admin trying super admin action |

---

## File Structure

```
app/
├── models/
│   ├── admin.py          # ✅ NEW - Admin model
│   ├── otp.py            # ✅ NEW - OTP model
│   ├── jeweller.py       # 🔄 UPDATED - Removed user_id dependency
│   └── ...
├── services/
│   ├── whatsapp_service.py  # ✅ NEW - WhatsApp API integration
│   └── otp_service.py       # ✅ NEW - OTP logic
├── routers/
│   ├── auth.py           # 🔄 UPDATED - Dual authentication
│   └── ...
├── core/
│   ├── dependencies.py   # 🔄 UPDATED - Support both user types
│   └── security.py       # ✅ OK - Password hashing, JWT
├── schemas/
│   └── auth.py           # 🔄 UPDATED - New auth schemas
└── config.py             # 🔄 UPDATED - Added WhatsApp settings
```

---

## WhatsApp API Setup

### **Get Credentials from Meta**
1. Visit: https://business.facebook.com/
2. Navigate to: WhatsApp → API Setup
3. Copy:
   - **Access Token** → `PLATFORM_WHATSAPP_TOKEN`
   - **Phone Number ID** → `PLATFORM_PHONE_NUMBER_ID`

### **Test WhatsApp Connection**
```python
from app.services.whatsapp_service import WhatsAppService
import asyncio

async def test():
    service = WhatsAppService(
        "YOUR_TOKEN",
        "YOUR_PHONE_ID"
    )
    result = await service.send_text_message(
        "+919876543210",
        "Test message from EkTola"
    )
    print(result)

asyncio.run(test())
```

---

## Frontend Integration

### **Jeweller Login Flow (React Example)**
```javascript
// Step 1: Request OTP
const requestOTP = async (phoneNumber) => {
  const response = await fetch('/auth/jeweller/request-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber })
  });
  return response.json();
};

// Step 2: Verify OTP
const verifyOTP = async (phoneNumber, otpCode) => {
  const response = await fetch('/auth/jeweller/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_number: phoneNumber,
      otp_code: otpCode
    })
  });
  const data = await response.json();
  
  // Save token
  localStorage.setItem('token', data.access_token);
  localStorage.setItem('user_type', 'jeweller');
  
  return data;
};
```

### **Admin Login Flow (React Example)**
```javascript
const adminLogin = async (email, password) => {
  const response = await fetch('/auth/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  
  localStorage.setItem('token', data.access_token);
  localStorage.setItem('user_type', 'admin');
  
  return data;
};
```

---

## Security Best Practices

✅ Always use HTTPS in production  
✅ Store tokens securely (httpOnly cookies recommended)  
✅ Implement rate limiting on OTP endpoints  
✅ Log failed authentication attempts  
✅ Use strong passwords for admins (min 8 chars, complexity)  
✅ Rotate WhatsApp access tokens periodically  
✅ Monitor OTP abuse (too many requests)  
✅ Implement CORS properly  
✅ Keep SECRET_KEY secure and never commit to git  

---

**Need Help?**  
See [AUTHENTICATION_IMPLEMENTATION.md](AUTHENTICATION_IMPLEMENTATION.md) for detailed documentation.
See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for migration instructions.
