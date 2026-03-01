# Scripts Directory

This directory contains utility scripts for database management, testing, and migrations.

## Setup

All scripts require the `.env` file in the project root with `DATABASE_URL` configured.

```bash
# Example .env
DATABASE_URL=postgresql://user:password@localhost:5432/ektola_db
# or
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/ektola_db
```

## Database Setup Scripts

### `create_db.py`
Creates the initial database schema.

```bash
python scripts/create_db.py
```

## Test Data Scripts

### `create_test_user.py`
Creates a test jeweller user for development/testing.

```bash
python scripts/create_test_user.py
```

**Test credentials:**
- Phone: +919876543210
- Password: test1234

### `create_sample_data.py`
Creates sample jewellers with various statuses and contacts for testing the admin dashboard.

```bash
python scripts/create_sample_data.py
```

## Admin Management Scripts

### `check_admin_user.py`
Checks for existing admin users and optionally creates one.

```bash
python scripts/check_admin_user.py
```

### `reset_admin_password.py`
Resets an admin user's password (interactive).

```bash
python scripts/reset_admin_password.py
```

## Database Migration Scripts

### `migrate_admin_dashboard.py`
Adds admin dashboard fields to jewellers table.

```bash
python scripts/migrate_admin_dashboard.py
```

### `migrate_phone_auth.py`
Adds phone authentication support to users table.

```bash
python scripts/migrate_phone_auth.py
```

### `migrate_whatsapp_signup.py`
Adds WhatsApp Embedded Signup fields to jewellers table.

```bash
python scripts/migrate_whatsapp_signup.py
```

## Utility Scripts

### `check_schema.py`
Displays the current database schema for contacts and jewellers tables.

```bash
python scripts/check_schema.py
```

### `audit_contacts.py`
Audits the contacts table for data integrity issues.

```bash
python scripts/audit_contacts.py
```

## Security Notes

⚠️ **Important:**
- All scripts now use environment variables for database credentials
- Never commit credentials directly in scripts
- Keep your `.env` file secure and never commit it to version control
- Scripts are for development/testing only - use proper migrations in production
