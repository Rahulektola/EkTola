# 🔄 Database Migration Guide

This guide will help you migrate your database to support the new dual authentication system.

## Prerequisites

✅ Python environment activated  
✅ Database running (PostgreSQL)  
✅ `.env` file configured  
✅ Alembic installed (`pip install alembic`)

---

## Step 1: Backup Your Database (IMPORTANT!)

```bash
# PostgreSQL backup
pg_dump -U your_username -d ektola > backup_before_migration.sql

# Or using connection string
pg_dump "postgresql://user:password@localhost:5432/ektola" > backup_before_migration.sql
```

---

## Step 2: Update Environment Variables

Add these to your `.env` file:

```env
# Platform WhatsApp credentials (for sending OTPs to jewellers)
PLATFORM_WHATSAPP_TOKEN=your_platform_whatsapp_access_token
PLATFORM_PHONE_NUMBER_ID=your_platform_phone_number_id

# Token expiry settings
ACCESS_TOKEN_EXPIRE_DAYS=30
```

---

## Step 3: Generate Migration

```bash
# Generate migration script
alembic revision --autogenerate -m "Add Admin and OTP models, update Jeweller"
```

This will create a new migration file in `alembic/versions/`.

---

## Step 4: Review the Migration

Open the generated migration file and verify it includes:

### **New Tables:**
- ✅ `admins` table
- ✅ `otps` table

### **Modified Tables:**
- ✅ `jewellers` - Removes `user_id` foreign key
- ✅ `jewellers` - Adds: `email`, `owner_name`, `is_verified`, `onboarding_completed`, `last_login`

### **Example Migration (verify yours matches):**

```python
def upgrade():
    # Create admins table
    op.create_table('admins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'ADMIN', 'SUPPORT', name='adminrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('can_manage_jewellers', sa.Boolean(), nullable=True),
        sa.Column('can_view_analytics', sa.Boolean(), nullable=True),
        sa.Column('can_manage_templates', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admins_email'), 'admins', ['email'], unique=True)
    op.create_index(op.f('ix_admins_phone_number'), 'admins', ['phone_number'], unique=True)
    
    # Create otps table
    op.create_table('otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('otp_code', sa.String(length=6), nullable=False),
        sa.Column('purpose', sa.Enum('LOGIN', 'SIGNUP', 'RESET_PASSWORD', name='otppurpose'), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('is_expired', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=True),
        sa.Column('max_attempts', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_otps_phone_number'), 'otps', ['phone_number'], unique=False)
    
    # Modify jewellers table
    # Remove user_id foreign key
    op.drop_constraint('jewellers_user_id_fkey', 'jewellers', type_='foreignkey')
    op.drop_column('jewellers', 'user_id')
    
    # Add new columns
    op.add_column('jewellers', sa.Column('owner_name', sa.String(), nullable=True))
    op.add_column('jewellers', sa.Column('email', sa.String(), nullable=True))
    op.add_column('jewellers', sa.Column('is_verified', sa.Boolean(), nullable=True))
    op.add_column('jewellers', sa.Column('onboarding_completed', sa.Boolean(), nullable=True))
    op.add_column('jewellers', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_jewellers_email'), 'jewellers', ['email'], unique=True)
```

---

## Step 5: Apply Migration

```bash
# Apply the migration
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, Add Admin and OTP models, update Jeweller
```

---

## Step 6: Verify Migration

```bash
# Check current database revision
alembic current

# Check migration history
alembic history
```

### **Manual Database Verification:**

```sql
-- Connect to your database
psql -U your_username -d ektola

-- Check if new tables exist
\dt

-- You should see:
-- admins
-- otps
-- jewellers (modified)

-- Check admins table structure
\d admins

-- Check otps table structure
\d otps

-- Check jewellers table structure (verify new columns)
\d jewellers
```

---

## Step 7: Create First Super Admin

```bash
# Run the super admin creation script
python create_super_admin.py
```

Follow the prompts to create your first super admin account.

To list existing admins:
```bash
python create_super_admin.py --list
```

---

## Step 8: Test the System

### **Test Admin Login:**
```bash
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_admin_email@example.com",
    "password": "your_password"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_type": "admin",
  "user": {
    "id": 1,
    "full_name": "Admin Name",
    "email": "admin@example.com",
    "role": "super_admin",
    ...
  }
}
```

### **Test Jeweller OTP Request:**
```bash
curl -X POST http://localhost:8000/auth/jeweller/request-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210"
  }'
```

**Note:** You need to configure WhatsApp API credentials first (see Configuration section).

---

## Troubleshooting

### **Issue: Migration fails with foreign key error**

If you have existing data in `jewellers` table with `user_id` references:

1. Backup the data
2. Manually remove the foreign key constraint:
```sql
ALTER TABLE jewellers DROP CONSTRAINT jewellers_user_id_fkey;
```
3. Run migration again

### **Issue: Enum type already exists**

If you see "type adminrole already exists":
```sql
DROP TYPE IF EXISTS adminrole CASCADE;
DROP TYPE IF EXISTS otppurpose CASCADE;
```
Then re-run the migration.

### **Issue: Cannot create unique index on email**

If jewellers table has duplicate emails:
```sql
-- Find duplicates
SELECT email, COUNT(*) FROM jewellers WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1;

-- Clean up duplicates manually
UPDATE jewellers SET email = NULL WHERE id IN (...duplicate ids...);
```

---

## Rollback (If Needed)

If something goes wrong, you can rollback:

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Restore from backup
psql -U your_username -d ektola < backup_before_migration.sql
```

---

## Post-Migration Checklist

- [ ] Database migrated successfully
- [ ] New tables (`admins`, `otps`) exist
- [ ] `jewellers` table updated with new columns
- [ ] Super admin account created
- [ ] Admin login tested and working
- [ ] WhatsApp credentials configured in `.env`
- [ ] Server restarted to load new code

---

## Configuration: WhatsApp API Setup

To enable jeweller OTP authentication, you need WhatsApp Business API credentials:

### **Option 1: Meta WhatsApp Business (Recommended)**

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Select your business
3. Go to **WhatsApp** → **API Setup**
4. Copy:
   - Access Token → `PLATFORM_WHATSAPP_TOKEN`
   - Phone Number ID → `PLATFORM_PHONE_NUMBER_ID`

### **Option 2: Twilio WhatsApp (Alternative)**

If using Twilio:
1. Get credentials from [Twilio Console](https://console.twilio.com/)
2. Adapt the `WhatsAppService` class to use Twilio API

### **Update .env:**
```env
PLATFORM_WHATSAPP_TOKEN=EAABs...your_token_here
PLATFORM_PHONE_NUMBER_ID=1234567890
```

---

## Next Steps

After successful migration:

1. ✅ **Update frontend** - Implement dual login UI (Jeweller OTP + Admin Password)
2. ✅ **Create admin routes** - Build jeweller management endpoints for admins
3. ✅ **Update existing routers** - Change `get_current_user` to `get_current_jeweller`
4. ✅ **Test thoroughly** - Test both authentication flows end-to-end
5. ✅ **Deploy to production** - Run migration on production database

---

## Support

If you encounter issues:
1. Check [AUTHENTICATION_IMPLEMENTATION.md](AUTHENTICATION_IMPLEMENTATION.md) for detailed documentation
2. Review Alembic logs: `alembic history --verbose`
3. Check PostgreSQL logs for detailed error messages

---

**Migration Status:** Ready to execute! 🚀
