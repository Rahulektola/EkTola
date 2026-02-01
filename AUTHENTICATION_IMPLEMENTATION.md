# Authentication System Implementation Summary

## ✅ Completed Changes

### 1. **New Models Created**
- ✅ `app/models/admin.py` - Admin model with role-based permissions
- ✅ `app/models/otp.py` - OTP model for WhatsApp authentication
- ✅ `app/models/jeweller.py` - Updated to remove User dependency

### 2. **New Services Created**
- ✅ `app/services/whatsapp_service.py` - WhatsApp API integration (text, template, media messages)
- ✅ `app/services/otp_service.py` - OTP generation, sending, and verification

### 3. **Updated Files**
- ✅ `app/routers/auth.py` - Complete rewrite with dual authentication
- ✅ `app/core/dependencies.py` - Support for Jeweller and Admin types
- ✅ `app/schemas/auth.py` - Updated schemas for OTP and admin auth
- ✅ `app/config.py` - Added platform WhatsApp settings
- ✅ `app/models/__init__.py` - Import new models

---

## 🔐 Authentication Flows

### **Jeweller Authentication (WhatsApp OTP)**

#### Registration:
```
1. POST /auth/jeweller/request-signup-otp
   Body: { "phone_number": "+919876543210" }
   → Sends OTP to WhatsApp

2. POST /auth/jeweller/register
   Body: {
     "phone_number": "+919876543210",
     "otp_code": "123456",
     "business_name": "Gold Palace",
     "owner_name": "Rajesh Kumar",
     "email": "contact@goldpalace.com"
   }
   → Creates account and returns JWT token
```

#### Login:
```
1. POST /auth/jeweller/request-otp
   Body: { "phone_number": "+919876543210" }
   → Sends OTP to WhatsApp

2. POST /auth/jeweller/verify-otp
   Body: {
     "phone_number": "+919876543210",
     "otp_code": "123456"
   }
   → Returns JWT token (valid for 30 days)
```

### **Admin Authentication (Email/Password)**

#### Login:
```
POST /auth/admin/login
Body: {
  "email": "admin@ektola.com",
  "password": "SecurePassword123"
}
→ Returns JWT token (valid for 8 hours)
```

#### Register New Admin (Super Admin Only):
```
POST /auth/admin/register
Headers: Authorization: Bearer <super_admin_token>
Body: {
  "full_name": "John Doe",
  "email": "john@ektola.com",
  "password": "SecurePassword123",
  "phone_number": "+919876543210",
  "role": "admin"
}
```

---

## 📊 Database Migrations Required

Run these commands to create the new tables:

```bash
# Create migration
alembic revision --autogenerate -m "Add Admin and OTP models, update Jeweller"

# Apply migration
alembic upgrade head
```

### **Tables Created:**
- `admins` - Admin users table
- `otps` - OTP verification codes table

### **Tables Modified:**
- `jewellers` - Removed `user_id`, added `email`, `owner_name`, `is_verified`, `onboarding_completed`, `last_login`

---

## 🔧 Configuration Setup

### **Environment Variables (.env)**

Add these to your `.env` file:

```env
# Platform WhatsApp (for sending OTPs)
PLATFORM_WHATSAPP_TOKEN=your_platform_token
PLATFORM_PHONE_NUMBER_ID=your_platform_phone_id

# Token expiry
ACCESS_TOKEN_EXPIRE_DAYS=30
```

### **Getting Platform WhatsApp Credentials**

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Navigate to: WhatsApp > API Setup
3. Copy:
   - **Access Token** → `PLATFORM_WHATSAPP_TOKEN`
   - **Phone Number ID** → `PLATFORM_PHONE_NUMBER_ID`

---

## 🧪 Testing the Implementation

### **1. Create First Super Admin**

Run this script to create your first super admin manually:

```python
# create_super_admin.py
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.admin import Admin, AdminRole
from app.core.security import get_password_hash
import sys

def create_super_admin():
    db = SessionLocal()
    try:
        email = input("Enter admin email: ")
        full_name = input("Enter full name: ")
        password = input("Enter password (min 8 chars): ")
        
        # Check if exists
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            print(f"Admin with email {email} already exists!")
            return
        
        admin = Admin(
            full_name=full_name,
            email=email,
            hashed_password=get_password_hash(password),
            role=AdminRole.SUPER_ADMIN,
            can_manage_jewellers=True,
            can_view_analytics=True,
            can_manage_templates=True
        )
        
        db.add(admin)
        db.commit()
        
        print(f"✅ Super admin created successfully!")
        print(f"Email: {email}")
        print(f"Role: SUPER_ADMIN")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
```

Run it:
```bash
python create_super_admin.py
```

### **2. Test Jeweller OTP Flow**

```bash
# Request OTP
curl -X POST http://localhost:8000/auth/jeweller/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'

# Check WhatsApp for OTP, then verify
curl -X POST http://localhost:8000/auth/jeweller/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "otp_code": "123456"
  }'
```

### **3. Test Admin Login**

```bash
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ektola.com",
    "password": "your_password"
  }'
```

---

## 🔐 Admin Roles & Permissions

| Role | Can Manage Jewellers | Can View Analytics | Can Manage Templates |
|------|---------------------|-------------------|---------------------|
| **SUPER_ADMIN** | ✅ | ✅ | ✅ |
| **ADMIN** | ✅ | ✅ | ❌ |
| **SUPPORT** | ✅ | ✅ | ❌ |

---

## 📝 Token Structure

### **Jeweller Token (30 days expiry)**
```json
{
  "sub": "123",
  "user_type": "jeweller",
  "phone": "+919876543210",
  "business_name": "Gold Palace",
  "exp": 1738483200
}
```

### **Admin Token (8 hours expiry)**
```json
{
  "sub": "5",
  "user_type": "admin",
  "role": "super_admin",
  "email": "admin@ektola.com",
  "exp": 1706889600
}
```

---

## 🚀 Next Steps

### **1. Update Other Routers**

All routers that currently use jeweller authentication need to be updated to use the new dependency:

```python
# Before
from app.core.dependencies import get_current_user

@router.get("/")
def get_items(current_user: User = Depends(get_current_user)):
    pass

# After
from app.core.dependencies import get_current_jeweller

@router.get("/")
def get_items(current_jeweller: Jeweller = Depends(get_current_jeweller)):
    pass
```

### **2. Admin-Only Endpoints**

Create admin routes for managing jewellers:

```python
# app/routers/admin.py
from app.core.dependencies import get_current_admin

@router.get("/jewellers")
def list_jewellers(admin: Admin = Depends(get_current_admin)):
    # Admin can view all jewellers
    pass

@router.put("/jewellers/{jeweller_id}/approve")
def approve_jeweller(
    jeweller_id: int,
    admin: Admin = Depends(get_current_admin)
):
    # Admin can approve jewellers
    pass
```

### **3. Frontend Integration**

Update frontend to handle two login flows:
- Jeweller login page: Phone number → OTP verification
- Admin login page: Email + Password

### **4. WhatsApp OTP Template (Optional)**

Instead of plain text, you can create an approved WhatsApp template for OTPs:

```
Template Name: otp_login
Category: Authentication
Body: Your EkTola login code is *{{1}}*. Valid for 10 minutes. Do not share.
```

---

## ⚠️ Important Security Notes

1. **OTP Settings:**
   - Expires in 10 minutes
   - Max 3 attempts per OTP
   - Single use only

2. **Token Expiry:**
   - Jewellers: 30 days (convenience)
   - Admins: 8 hours (security)

3. **Rate Limiting:**
   - Consider adding rate limiting to OTP endpoints to prevent spam

4. **Password Requirements:**
   - Minimum 8 characters
   - Consider adding complexity requirements

---

## 📞 Support

For WhatsApp API setup issues:
- [Meta for Developers Docs](https://developers.facebook.com/docs/whatsapp/)
- [WhatsApp Business API](https://business.whatsapp.com/developers/)

---

**Status:** ✅ All authentication infrastructure is ready!

**Testing Required:** Create super admin → Test admin login → Configure WhatsApp → Test jeweller OTP flow
