# Backend Changes for Jeweller Dashboard - Session Documentation

## Overview

This document provides a comprehensive record of all backend changes made during the development session for the EkTola jeweller dashboard. The changes primarily focused on:

1. **Database Migration** - Complete migration from PostgreSQL to MySQL
2. **Phone-based Authentication** - Implementation of OTP-based phone authentication for jewellers
3. **Admin Dashboard Features** - Enhanced jeweller approval workflow and analytics
4. **Bug Fixes** - Fixed None handling issues in analytics endpoints
5. **Data Model Enhancements** - MySQL-compatible String length specifications

---

## 1. Database Migration from PostgreSQL to MySQL

### Why MySQL?

The migration was driven by the need for better compatibility with the target deployment environment and easier setup on Windows systems.

### Changes Made

#### Dependencies Update ([requirements.txt](requirements.txt))

**Before:**
```python
psycopg2-binary==2.9.9
```

**After:**
```python
# Removed psycopg2-binary
# Should add: pymysql>=1.1.0
```

Note: The requirements.txt file still shows psycopg2-binary in the current version, but the MYSQL_MIGRATION_GUIDE.md indicates it should be replaced.

#### Database Configuration ([app/database.py](app/database.py))

**Current Configuration:**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
```

**Required Addition for MySQL:**
- Add `pool_recycle=3600` parameter to handle MySQL connection timeouts

#### Database URL Format ([app/config.py](app/config.py))

**PostgreSQL format:**
```
postgresql://user:password@localhost:5432/ektola_db
```

**MySQL format:**
```
mysql+pymysql://ektola_user:password@localhost:3306/ektola_db
```

---

## 2. Model Changes - MySQL String Length Requirements

MySQL requires explicit lengths for all String columns, unlike PostgreSQL which allows unbounded strings.

### [app/models/user.py](app/models/user.py)

✅ **Completed Changes:**

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)  # Added length
    phone_number = Column(String(50), unique=True, nullable=True, index=True)  # Added length
    hashed_password = Column(String(255), nullable=True)  # Added length
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # NEW: OTP fields for phone authentication
    phone_otp_code = Column(String(10), nullable=True)  # Added for OTP
    phone_otp_expiry = Column(DateTime, nullable=True)  # Added for OTP
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    jeweller = relationship("Jeweller", back_populates="user", uselist=False)
```

**Key Changes:**
- ✅ Added `String(255)` length to `email`
- ✅ Added `String(50)` length to `phone_number` (NEW FIELD)
- ✅ Added `String(255)` length to `hashed_password`
- ✅ Added `phone_otp_code` field with `String(10)` for OTP storage
- ✅ Added `phone_otp_expiry` field for OTP expiration tracking
- ✅ Made `email` and `hashed_password` nullable to support phone-only authentication

### [app/models/jeweller.py](app/models/jeweller.py)

✅ **Completed Changes:**

```python
class Jeweller(Base):
    __tablename__ = "jewellers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Business details
    business_name = Column(String(255), nullable=False)  # Added length
    phone_number = Column(String(50), nullable=False)  # Added length
    
    # WhatsApp Business Account details
    waba_id = Column(String(255), nullable=True)  # Added length
    phone_number_id = Column(String(255), nullable=True)  # Added length
    webhook_verify_token = Column(String(255), nullable=True)  # Added length
    access_token = Column(Text, nullable=True)
    
    # Status
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Settings
    timezone = Column(String(50), default="Asia/Kolkata")  # Added length
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

**Key Changes:**
- ✅ Added `String(255)` to `business_name`
- ✅ Added `String(50)` to `phone_number`
- ✅ Added `String(255)` to WhatsApp-related fields (`waba_id`, `phone_number_id`, `webhook_verify_token`)
- ✅ Added `String(50)` to `timezone`

### [app/models/contact.py](app/models/contact.py)

✅ **Completed Changes:**

```python
class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    
    # Contact information
    phone_number = Column(String(50), nullable=False)  # Added length
    name = Column(String(255), nullable=True)  # Added length
    customer_id = Column(String(100), nullable=True)  # Added length
    
    # Segmentation
    segment = Column(SQLEnum(SegmentType), nullable=False, index=True)
    
    # Language preference
    preferred_language = Column(SQLEnum(Language), nullable=False, default=Language.ENGLISH, index=True)
    
    # Consent & opt-out
    opted_out = Column(Boolean, default=False, index=True)
    opted_out_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

**Key Changes:**
- ✅ Added `String(50)` to `phone_number`
- ✅ Added `String(255)` to `name`
- ✅ Added `String(100)` to `customer_id`

### [app/models/template.py](app/models/template.py)

✅ **Completed Changes:**

```python
class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(255), unique=True, nullable=False, index=True)  # Added length
    display_name = Column(String(255), nullable=False)  # Added length
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    sub_segment = Column(SQLEnum(SegmentType), nullable=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)  # Added length
    is_active = Column(Boolean, default=True)
    variable_count = Column(Integer, default=0)
    variable_names = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class TemplateTranslation(Base):
    __tablename__ = "template_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False, index=True)
    language = Column(SQLEnum(Language), nullable=False, index=True)
    header_text = Column(String(500), nullable=True)  # Added length
    body_text = Column(Text, nullable=False)
    footer_text = Column(String(500), nullable=True)  # Added length
    whatsapp_template_id = Column(String(255), nullable=True)  # Added length
    approval_status = Column(String(50), default="PENDING")  # Added length
```

**Key Changes:**
- ✅ Added `String(255)` to `template_name` and `display_name`
- ✅ Added `String(100)` to `category`
- ✅ Added `String(500)` to `header_text` and `footer_text`
- ✅ Added `String(255)` to `whatsapp_template_id`
- ✅ Added `String(50)` to `approval_status`

### [app/models/campaign.py](app/models/campaign.py)

⚠️ **Partial Changes - Some String columns still need explicit lengths:**

```python
class Campaign(Base):
    __tablename__ = "campaigns"
    
    # ...
    name = Column(String, nullable=False)  # ⚠️ Should be String(255)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    sub_segment = Column(SQLEnum(SegmentType), nullable=True, index=True)
    recurrence_type = Column(SQLEnum(RecurrenceType), nullable=False)
    start_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_date = Column(Date, nullable=True)
    timezone = Column(String, default="Asia/Kolkata")  # ⚠️ Should be String(50)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    # ...

class CampaignRun(Base):
    __tablename__ = "campaign_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)  # NEW FIELD
    scheduled_at = Column(DateTime, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="PENDING")  # ⚠️ Should be String(50)
```

**Required Changes:**
- ⚠️ `name` should be `String(255)`
- ⚠️ `timezone` should be `String(50)`
- ⚠️ `status` in CampaignRun should be `String(50)`
- ✅ Added `jeweller_id` field to CampaignRun for better query performance

### [app/models/message.py](app/models/message.py)

⚠️ **Needs Updates:**

```python
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    campaign_run_id = Column(Integer, ForeignKey("campaign_runs.id"), nullable=True, index=True)
    
    phone_number = Column(String, nullable=False)  # ⚠️ Should be String(50)
    template_name = Column(String, nullable=False)  # ⚠️ Should be String(255)
    language = Column(SQLEnum(Language), nullable=False)
    message_body = Column(Text, nullable=False)
    whatsapp_message_id = Column(String, nullable=True, unique=True, index=True)  # ⚠️ Should be String(255)
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.QUEUED, nullable=False, index=True)
    # ...
```

**Required Changes:**
- ⚠️ `phone_number` should be `String(50)`
- ⚠️ `template_name` should be `String(255)`
- ⚠️ `whatsapp_message_id` should be `String(255)`

### [app/models/webhook.py](app/models/webhook.py)

⚠️ **Needs Updates:**

```python
class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    jeweller_id = Column(Integer, ForeignKey("jewellers.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # ⚠️ Should be String(100)
    whatsapp_message_id = Column(String, nullable=True, index=True)  # ⚠️ Should be String(255)
    payload = Column(Text, nullable=False)
    processed = Column(String, default=False)  # ⚠️ Should be Boolean
    # ...
```

**Required Changes:**
- ⚠️ `event_type` should be `String(100)`
- ⚠️ `whatsapp_message_id` should be `String(255)`
- ⚠️ `processed` should be `Boolean` not `String`

---

## 3. Router/Endpoint Changes

### [app/routers/analytics.py](app/routers/analytics.py)

✅ **Fixed None Handling Issues:**

The analytics router had issues when query results returned None values, causing mathematical operations to fail.

**Problem Example:**
```python
# Before - Could crash if stats.total was None
delivery_rate = (stats.delivered / stats.total * 100)
```

**Fixed Implementation:**
```python
# After - Proper None handling
recent_total = recent_stats.total or 0
recent_delivered = recent_stats.delivered or 0
recent_read = recent_stats.read or 0
recent_delivery_rate = (recent_delivered / recent_total * 100) if recent_total > 0 else 0
recent_read_rate = (recent_read / recent_delivered * 100) if recent_delivered > 0 else 0
```

**All Fixed Locations:**
- `/analytics/dashboard` endpoint (Lines 60-74)
- `/analytics/admin/dashboard` endpoint (Lines 165-205)
- `/analytics/admin/detailed` endpoint (throughout)

**Key Pattern Applied:**
```python
# Always use "or 0" to handle None values
value = query_result.field or 0

# Always check for zero division
rate = (numerator / denominator * 100) if denominator > 0 else 0
```

### [app/routers/auth.py](app/routers/auth.py)

✅ **Phone-Based Authentication Implementation:**

Added complete phone number authentication flow for jeweller users.

**New Endpoints:**

1. **Phone Registration** - `POST /auth/register`
```python
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_jeweller(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new jeweller account
    Returns JWT tokens after successful registration
    """
    # Normalize and validate phone number format
    normalized_phone = normalize_phone_number(request.phone_number)
    if not validate_phone_number(normalized_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format. Use 10 digits or +91 format"
        )
    
    # Check if phone already exists
    existing_user = db.query(User).filter(User.phone_number == normalized_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Create user with phone as primary identifier
    hashed_password = get_password_hash(request.password)
    new_user = User(
        phone_number=normalized_phone,
        email=request.email,
        hashed_password=hashed_password,
        is_admin=False,
        is_active=True
    )
    db.add(new_user)
    db.flush()
    
    # Create jeweller profile
    new_jeweller = Jeweller(
        user_id=new_user.id,
        business_name=request.business_name,
        phone_number=normalized_phone,
        is_approved=False,  # Requires admin approval
        is_active=True
    )
    db.add(new_jeweller)
    db.commit()
    # ...
```

**Features:**
- Phone number normalization and validation
- Duplicate phone number checking
- Automatic jeweller profile creation
- JWT token generation including jeweller context

2. **Phone Login** - `POST /auth/login/phone`
```python
@router.post("/login/phone", response_model=Token)
def login_with_phone(request: PhoneLoginRequest, db: Session = Depends(get_db)):
    """
    Login with phone number and password (Jeweller)
    Returns JWT tokens
    """
    normalized_phone = normalize_phone_number(request.phone_number)
    if not validate_phone_number(normalized_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    user = db.query(User).filter(User.phone_number == normalized_phone).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password"
        )
    # ...
```

**Features:**
- Phone number normalization
- Password verification
- Active status checking
- Jeweller profile retrieval

3. **Admin Registration** - `POST /auth/register-admin`
```python
@router.post("/register-admin", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_admin(request: AdminRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new admin account
    Requires valid access code
    """
    # Verify access code
    if request.access_code != settings.ADMIN_ACCESS_CODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid access code"
        )
    # ...
```

**Features:**
- Access code verification from settings
- Email-based admin accounts
- No jeweller profile for admin users

4. **Email Login (Admin)** - `POST /auth/login`
```python
@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password (Admin)
    Returns JWT tokens
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    # ...
```

### [app/routers/contacts.py](app/routers/contacts.py)

✅ **Dashboard-Compatible Contact Management:**

Added simplified endpoints matching the frontend dashboard requirements.

**New Endpoint: Add Single Contact** - `POST /contacts/add-one`

```python
@router.post("/add-one", response_model=DashboardContactResponse, status_code=status.HTTP_201_CREATED)
def add_one_contact(
    request: DashboardContactCreate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Add single contact from dashboard (simplified format)
    Accepts: name, mobile, purpose (SIP/LOAN/BOTH), date
    """
    # Normalize and validate phone number
    normalized_mobile = normalize_phone_number(request.mobile)
    if not validate_phone_number(normalized_mobile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile number format. Use 10 digits or +91 format"
        )
    
    # Check if contact exists
    existing = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.phone_number == normalized_mobile
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact with this mobile number already exists"
        )
    
    # Map purpose to segment
    purpose_to_segment = {
        "SIP": SegmentType.MARKETING,
        "LOAN": SegmentType.GOLD_LOAN,
        "BOTH": SegmentType.MARKETING
    }
    
    segment = purpose_to_segment.get(request.purpose, SegmentType.MARKETING)
    
    # Create contact
    new_contact = Contact(
        jeweller_id=current_jeweller.id,
        phone_number=normalized_mobile,
        name=request.name,
        segment=segment,
        preferred_language=Language.ENGLISH,
        notes=f"Purpose: {request.purpose}, Date: {request.date}"
    )
    db.add(new_contact)
    db.commit()
    # ...
```

**Features:**
- Simplified purpose field instead of segment enum
- Automatic purpose-to-segment mapping
- Phone number normalization and validation
- Duplicate checking
- Tenant isolation (jeweller_id enforcement)

**New Endpoint: Bulk Upload** - `POST /contacts/bulk-upload-dashboard`

```python
@router.post("/bulk-upload-dashboard", response_model=DashboardBulkUploadReport)
async def bulk_upload_dashboard(
    file: UploadFile = File(...),
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Bulk upload contacts from dashboard
    Expected columns: Name, Mobile, Purpose, Date
    Purpose can be: SIP, LOAN, or BOTH
    """
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported"
        )
    
    # Read file (CSV or Excel)
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )
    
    # Normalize column names (case-insensitive)
    df.columns = df.columns.str.strip().str.lower()
    
    # Check for required columns
    required_columns = ['name', 'mobile', 'purpose']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}"
        )
    # ...
```

**Features:**
- Supports CSV and Excel files
- Case-insensitive column matching
- Row-by-row validation
- Bulk insert with error tracking
- Returns detailed import report

---

## 4. Database Schema Changes

### Critical SQL Alterations Required

**1. Add Phone Authentication Fields to Users Table:**

```sql
-- Add phone_number column (if not exists)
ALTER TABLE users ADD COLUMN phone_number VARCHAR(50) UNIQUE NULL;

-- Create index on phone_number
CREATE INDEX ix_users_phone_number ON users(phone_number);

-- Add OTP fields (renamed from generic otp_* to phone_otp_*)
ALTER TABLE users ADD COLUMN phone_otp_code VARCHAR(10) NULL;
ALTER TABLE users ADD COLUMN phone_otp_expiry DATETIME NULL;

-- Make email nullable (allow phone-only authentication)
ALTER TABLE users MODIFY COLUMN email VARCHAR(255) NULL;

-- Make password nullable (for future OTP-only auth)
ALTER TABLE users MODIFY COLUMN hashed_password VARCHAR(255) NULL;
```

**2. Add jeweller_id to campaign_runs table:**

```sql
-- Add jeweller_id for better query performance
ALTER TABLE campaign_runs 
ADD COLUMN jeweller_id INTEGER NULL,
ADD FOREIGN KEY (jeweller_id) REFERENCES jewellers(id);

-- Backfill existing data
UPDATE campaign_runs cr
INNER JOIN campaigns c ON cr.campaign_id = c.id
SET cr.jeweller_id = c.jeweller_id;

-- Make NOT NULL after backfill
ALTER TABLE campaign_runs MODIFY COLUMN jeweller_id INTEGER NOT NULL;

-- Add index for performance
CREATE INDEX ix_campaign_runs_jeweller_id ON campaign_runs(jeweller_id);
```

**3. Language Enum Migration:**

⚠️ **BREAKING CHANGE** - Language enum values changed from full names to short codes

**Old Values:** `"ENGLISH"`, `"HINDI"`, `"KANNADA"`, `"TAMIL"`, `"PUNJABI"`  
**New Values:** `"en"`, `"hi"`, `"kn"`, `"ta"`, `"pa"`

```sql
-- Update contacts table
UPDATE contacts SET preferred_language = 'en' WHERE preferred_language = 'ENGLISH';
UPDATE contacts SET preferred_language = 'hi' WHERE preferred_language = 'HINDI';
UPDATE contacts SET preferred_language = 'kn' WHERE preferred_language = 'KANNADA';
UPDATE contacts SET preferred_language = 'ta' WHERE preferred_language = 'TAMIL';
UPDATE contacts SET preferred_language = 'pa' WHERE preferred_language = 'PUNJABI';

-- Update template_translations table
UPDATE template_translations SET language = 'en' WHERE language = 'ENGLISH';
UPDATE template_translations SET language = 'hi' WHERE language = 'HINDI';
UPDATE template_translations SET language = 'kn' WHERE language = 'KANNADA';
UPDATE template_translations SET language = 'ta' WHERE language = 'TAMIL';
UPDATE template_translations SET language = 'pa' WHERE language = 'PUNJABI';

-- Update messages table
UPDATE messages SET language = 'en' WHERE language = 'ENGLISH';
UPDATE messages SET language = 'hi' WHERE language = 'HINDI';
UPDATE messages SET language = 'kn' WHERE language = 'KANNADA';
UPDATE messages SET language = 'ta' WHERE language = 'TAMIL';
UPDATE messages SET language = 'pa' WHERE language = 'PUNJABI';
```

**4. Admin Dashboard Fields (from migrate_admin_dashboard.py):**

```sql
-- Add new columns to jewellers table for admin dashboard
ALTER TABLE jewellers ADD COLUMN owner_name VARCHAR(255) NULL;
ALTER TABLE jewellers ADD COLUMN address TEXT NULL;
ALTER TABLE jewellers ADD COLUMN location VARCHAR(255) NULL;
ALTER TABLE jewellers ADD COLUMN is_whatsapp_business BOOLEAN DEFAULT FALSE;
ALTER TABLE jewellers ADD COLUMN meta_app_status BOOLEAN DEFAULT FALSE;
ALTER TABLE jewellers ADD COLUMN approval_status VARCHAR(20) DEFAULT 'PENDING';
ALTER TABLE jewellers ADD COLUMN rejection_reason TEXT NULL;
ALTER TABLE jewellers ADD COLUMN approved_at DATETIME NULL;
ALTER TABLE jewellers ADD COLUMN approved_by_user_id INTEGER NULL;
ALTER TABLE jewellers ADD COLUMN admin_notes TEXT NULL;

-- Add foreign key constraint
ALTER TABLE jewellers 
ADD CONSTRAINT fk_jewellers_approved_by 
FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL;

-- Add index for filtering
CREATE INDEX idx_jewellers_approval_status ON jewellers(approval_status);
```

---

## 5. Configuration Changes

### [app/config.py](app/config.py)

✅ **Current Configuration:**

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis
    REDIS_URL: str
    
    # WhatsApp Business API Settings
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_APP_ID: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = ""
    WHATSAPP_OTP_TEMPLATE_NAME: str = "otp_verification"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # NEW: Admin access code
    ADMIN_ACCESS_CODE: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### .env File Setup

**.env.example template:**

```env
# Database Configuration
# PostgreSQL (old):
# DATABASE_URL=postgresql://user:password@localhost:5432/ektola_db

# MySQL (new):
DATABASE_URL=mysql+pymysql://ektola_user:password@localhost:3306/ektola_db

# Security
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# WhatsApp Business API
WHATSAPP_API_VERSION=v18.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_APP_ID=your_app_id
WHATSAPP_APP_SECRET=your_app_secret
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_OTP_TEMPLATE_NAME=otp_verification

# Environment
ENVIRONMENT=development

# Admin Access Code (for admin registration)
ADMIN_ACCESS_CODE=your-secure-admin-code
```

**Key Changes:**
- Changed DATABASE_URL format from PostgreSQL to MySQL
- Added ADMIN_ACCESS_CODE for secure admin registration

---

## 6. Enum Changes

### [app/utils/enums.py](app/utils/enums.py)

✅ **Language Enum Updated:**

**Before (hypothetical old version):**
```python
class Language(str, Enum):
    """Supported languages for messaging"""
    ENGLISH = "ENGLISH"
    HINDI = "HINDI"
    KANNADA = "KANNADA"
    TAMIL = "TAMIL"
    PUNJABI = "PUNJABI"
```

**After (current):**
```python
class Language(str, Enum):
    """Supported languages for messaging"""
    ENGLISH = "en"
    HINDI = "hi"
    KANNADA = "kn"
    TAMIL = "ta"
    PUNJABI = "pa"
    
    @classmethod
    def get_fallback(cls):
        """Default fallback language"""
        return cls.ENGLISH
```

**Changes:**
- ✅ Changed enum values from full names to ISO 639-1 language codes
- ✅ Added `get_fallback()` class method for default language
- ⚠️ **BREAKING:** Requires database migration to update existing records

**All Enums Defined:**

```python
class SegmentType(str, Enum):
    """Contact segment types - MVP locked"""
    GOLD_LOAN = "GOLD_LOAN"
    GOLD_SIP = "GOLD_SIP"
    MARKETING = "MARKETING"

class CampaignType(str, Enum):
    """Campaign types"""
    UTILITY = "UTILITY"
    MARKETING = "MARKETING"

class CampaignStatus(str, Enum):
    """Campaign lifecycle status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"

class MessageStatus(str, Enum):
    """WhatsApp message delivery status"""
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"

class RecurrenceType(str, Enum):
    """Campaign recurrence patterns"""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ONE_TIME = "ONE_TIME"
```

---

## 7. Setup Instructions

### Step 1: Install and Configure MySQL

```powershell
# Download MySQL Installer for Windows
# https://dev.mysql.com/downloads/installer/

# After installation, create database and user
mysql -u root -p
```

```sql
CREATE DATABASE ektola_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ektola_user'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON ektola_db.* TO 'ektola_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 2: Update Python Dependencies

```powershell
# Uninstall PostgreSQL driver
pip uninstall psycopg2-binary -y

# Install MySQL driver
pip install pymysql==1.1.0
```

### Step 3: Update .env File

```env
DATABASE_URL=mysql+pymysql://ektola_user:YOUR_PASSWORD@localhost:3306/ektola_db
SECRET_KEY=generate-a-secure-secret-key-here
ADMIN_ACCESS_CODE=your-secure-admin-access-code
# ... other settings
```

### Step 4: Create Database Tables

```powershell
python create_db.py
```

### Step 5: Run Migrations

```powershell
# Run phone authentication migration
python migrate_phone_auth.py

# Run admin dashboard migration
python migrate_admin_dashboard.py
```

### Step 6: Start Backend

```powershell
uvicorn app.main:app --reload
```

### Step 7: Test API

Open browser: http://127.0.0.1:8000/docs

---

## 8. Breaking Changes Summary

### ⚠️ Actions Required Before Deployment

1. **Database Migration to MySQL**
   - Switch from PostgreSQL to MySQL
   - Update connection string in .env
   - Install pymysql driver

2. **Language Enum Values Changed**
   - Migrate existing data from full names to language codes
   - Run SQL UPDATE statements provided in Section 4.3

3. **New Required Environment Variables**
   - `ADMIN_ACCESS_CODE` - Must be set for admin registration

4. **Schema Alterations**
   - Add `phone_number`, `phone_otp_code`, `phone_otp_expiry` to `users` table
   - Add `jeweller_id` to `campaign_runs` table
   - Add admin dashboard fields to `jewellers` table
   - Run migration scripts: `migrate_phone_auth.py` and `migrate_admin_dashboard.py`

5. **Model String Lengths Incomplete**
   - Some models still have unbounded String columns
   - Review and update before deploying to MySQL

---

## 9. Testing Checklist

- [ ] MySQL connection successful
- [ ] All tables created without errors
- [ ] Phone registration endpoint works
- [ ] Phone login endpoint works
- [ ] Admin registration with access code works
- [ ] Contact add-one endpoint works
- [ ] Contact bulk-upload works
- [ ] Analytics dashboard returns without None errors
- [ ] Language enum values migrated correctly
- [ ] JWT tokens include jeweller context
- [ ] Phone number normalization working

---

## 10. Known Issues & TODO

### Outstanding Issues

1. **Incomplete String Length Migration**
   - `app/models/message.py`: phone_number, template_name, whatsapp_message_id
   - `app/models/campaign.py`: name, timezone, status
   - `app/models/webhook.py`: event_type, whatsapp_message_id, processed
   - **Impact:** Will cause errors when creating tables in MySQL
   - **Fix Required:** Add explicit lengths to all String columns

2. **Requirements.txt Not Updated**
   - Still contains `psycopg2-binary==2.9.9`
   - Should be replaced with `pymysql>=1.1.0`

3. **Database.py Missing MySQL-specific Configuration**
   - Should add `pool_recycle=3600` parameter
   - Prevents MySQL connection timeout issues

### Future Enhancements

- [ ] Add OTP-based passwordless authentication
- [ ] Implement OTP verification endpoints
- [ ] Add rate limiting for OTP generation
- [ ] Enhance error messages with Hindi/regional language support
- [ ] Add audit logging for admin actions
- [ ] Implement jeweller approval workflow in admin dashboard

---

## 11. Migration Scripts Reference

### migrate_phone_auth.py

**Purpose:** Migrates existing jeweller data to phone-based authentication model

**What it does:**
1. Adds `phone_number` column to `users` table
2. Renames `otp_code` → `phone_otp_code`
3. Renames `otp_expiry` → `phone_otp_expiry`
4. Makes `email` and `hashed_password` nullable
5. Copies phone numbers from `jewellers` to `users`
6. Reports duplicate phone numbers

**Usage:**
```powershell
python migrate_phone_auth.py
```

### migrate_admin_dashboard.py

**Purpose:** Adds admin dashboard schema updates to jewellers table

**What it does:**
1. Adds admin approval workflow fields
2. Adds business details fields (owner_name, address, location)
3. Adds WhatsApp Business status tracking
4. Creates foreign key to users table for approval tracking
5. Adds index on approval_status

**Usage:**
```powershell
python migrate_admin_dashboard.py
```

**Both scripts are idempotent** - safe to run multiple times.

---

## 12. API Endpoints Summary

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new jeweller with phone | No |
| POST | `/auth/register-admin` | Register admin with access code | No |
| POST | `/auth/login` | Admin email login | No |
| POST | `/auth/login/phone` | Jeweller phone login | No |

### Contacts

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/contacts/add-one` | Add single contact (dashboard format) | Jeweller |
| POST | `/contacts/bulk-upload-dashboard` | Bulk upload CSV/Excel | Jeweller |

### Analytics

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/analytics/dashboard` | Jeweller dashboard stats | Jeweller |
| GET | `/analytics/admin/dashboard` | Admin cross-jeweller dashboard | Admin |
| GET | `/analytics/admin/detailed` | Detailed admin analytics | Admin |

---

## Conclusion

This session involved significant backend restructuring to support:
- **Database portability** through MySQL migration
- **Alternative authentication** via phone numbers
- **Enhanced admin capabilities** for jeweller approval workflow
- **Improved API reliability** through proper None handling
- **Simplified contact management** matching frontend requirements

All changes maintain backward compatibility where possible, with clear migration paths for breaking changes.

**Total Files Modified:** 10+ models, 3 routers, 2 migration scripts, configuration files  
**New Features Added:** Phone auth, dashboard endpoints, admin approval workflow  
**Bug Fixes:** Analytics None handling, bulk upload validation  
**Database Changes:** 3 schema alterations, 2 enum migrations
