# MySQL Migration Guide - EkTola Backend

## Overview
This guide provides step-by-step instructions to migrate your EkTola backend from PostgreSQL to MySQL. All backend code changes have been completed automatically.

---

## ✅ Completed Backend Changes

The following changes have been applied to your backend:

1. **Updated Dependencies** ([requirements.txt](requirements.txt))
   - Replaced `psycopg2-binary==2.9.9` with `pymysql>=1.1.0`

2. **Fixed All Model Definitions** (MySQL requires explicit String lengths)
   - [app/models/user.py](app/models/user.py) - Added lengths to email(255), phone_number(20), hashed_password(255), phone_otp_code(10)
   - [app/models/jeweller.py](app/models/jeweller.py) - Added lengths to business_name(255), phone_number(20), waba_id(100), phone_number_id(100), webhook_verify_token(255), timezone(50)
   - [app/models/contact.py](app/models/contact.py) - Added lengths to phone_number(20), name(255), customer_id(100)
   - [app/models/campaign.py](app/models/campaign.py) - Added lengths to name(255), timezone(50), status(50)
   - [app/models/message.py](app/models/message.py) - Added lengths to phone_number(20), template_name(255), whatsapp_message_id(255)
   - [app/models/template.py](app/models/template.py) - Added lengths to template_name(255), display_name(255), category(50), header_text(255), footer_text(255), whatsapp_template_id(255), approval_status(50)
   - [app/models/webhook.py](app/models/webhook.py) - Added lengths to event_type(100), whatsapp_message_id(255), processed(10)

3. **Updated Database Configuration** ([app/database.py](app/database.py))
   - Added `pool_recycle=3600` to handle MySQL connection timeouts

4. **Updated Environment Template** ([.env.example](.env.example))
   - Changed default DATABASE_URL to MySQL format

---

## 🔧 Setup Instructions

### Step 1: Install MySQL on Windows

1. **Download MySQL Installer**
   ```
   https://dev.mysql.com/downloads/installer/
   ```
   - Choose "Windows (x86, 32-bit), MSI Installer" (works on 64-bit too)
   - Download the "mysql-installer-community" version

2. **Run MySQL Installer**
   - Choose "Developer Default" setup type
   - Click "Execute" to install all components
   - This will install MySQL Server, MySQL Workbench, and other tools

3. **Configure MySQL Server**
   - **Type and Networking**: Keep defaults (Standalone, Port 3306)
   - **Authentication Method**: Use Strong Password Encryption (recommended)
   - **Accounts and Roles**: 
     - Set a strong root password (REMEMBER THIS!)
     - Click "Add User" to create application user (optional, can do later)
   - **Windows Service**: 
     - Configure as Windows Service: ✓
     - Start at System Startup: ✓
   - **Apply Configuration**: Click "Execute" to complete setup

4. **Verify Installation**
   ```powershell
   # Check MySQL version
   mysql --version
   
   # If command not found, add to PATH:
   # C:\Program Files\MySQL\MySQL Server 8.0\bin
   ```

### Step 2: Create Database and User

Open PowerShell and run:

```powershell
# Login to MySQL as root
mysql -u root -p
# Enter the root password you set during installation
```

In the MySQL console, run these commands:

```sql
-- Create database with UTF-8 support (for emojis, etc.)
CREATE DATABASE ektola_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create application user
CREATE USER 'ektola_user'@'localhost' IDENTIFIED BY 'YOUR_STRONG_PASSWORD';

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON ektola_db.* TO 'ektola_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify database created
SHOW DATABASES;

-- Exit MySQL console
EXIT;
```

**Important:** Replace `YOUR_STRONG_PASSWORD` with a secure password!

### Step 3: Update Python Environment

```powershell
# Navigate to your project directory
cd "c:\Users\halli\OneDrive\Desktop\EkTola"

# Activate virtual environment (if using one)
.\venv\Scripts\Activate.ps1

# Uninstall PostgreSQL driver
pip uninstall psycopg2-binary -y

# Install MySQL driver
pip install pymysql==1.1.0

# Verify installation
pip show pymysql
```

### Step 4: Update .env File

1. **Copy .env.example to .env** (if you haven't already)
   ```powershell
   Copy-Item .env.example .env
   ```

2. **Edit .env file** and update the DATABASE_URL:
   ```env
   DATABASE_URL=mysql+pymysql://ektola_user:YOUR_STRONG_PASSWORD@localhost:3306/ektola_db
   ```
   
   Replace:
   - `ektola_user` - with your MySQL username (if you used a different name)
   - `YOUR_STRONG_PASSWORD` - with the password you set for ektola_user
   - `ektola_db` - with your database name (if you used a different name)

### Step 5: Create Database Tables

```powershell
# Make sure you're in the project root directory
cd "c:\Users\halli\OneDrive\Desktop\EkTola"

# Run the database creation script
python create_db.py
```

**Expected Output:**
```
Creating all database tables...
✅ All tables created successfully!

Tables created:
  - users
  - jewellers
  - contacts
  - campaigns
  - campaign_runs
  - messages
  - templates
  - template_translations
  - webhook_events
```

### Step 6: Verify Database Schema

**Option A: Using MySQL Command Line**
```powershell
mysql -u ektola_user -p ektola_db
```

```sql
-- Show all tables
SHOW TABLES;

-- Check structure of a specific table
DESCRIBE users;
DESCRIBE jewellers;

-- Exit
EXIT;
```

**Option B: Using MySQL Workbench (GUI)**
1. Open MySQL Workbench
2. Connect to localhost (root or ektola_user)
3. Navigate to "Schemas" → "ektola_db" → "Tables"
4. Right-click any table → "Table Inspector" to view structure

### Step 7: Test Backend

```powershell
# Start the FastAPI development server
uvicorn app.main:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test the API:**
- Open browser: http://127.0.0.1:8000/docs
- You should see the FastAPI Swagger documentation
- Try the health check endpoint if available

---

## 🐛 Troubleshooting

### Issue: "mysql: command not found"
**Solution:** Add MySQL to PATH
```powershell
# Add to PATH (PowerShell Admin)
$env:Path += ";C:\Program Files\MySQL\MySQL Server 8.0\bin"

# Make permanent: System Properties → Environment Variables → Path
```

### Issue: "Access denied for user 'ektola_user'@'localhost'"
**Solution:** Check credentials or recreate user
```sql
-- Login as root and run:
DROP USER IF EXISTS 'ektola_user'@'localhost';
CREATE USER 'ektola_user'@'localhost' IDENTIFIED BY 'NEW_PASSWORD';
GRANT ALL PRIVILEGES ON ektola_db.* TO 'ektola_user'@'localhost';
FLUSH PRIVILEGES;
```

### Issue: "Can't connect to MySQL server on 'localhost'"
**Solution:** Ensure MySQL service is running
```powershell
# Check service status
Get-Service MySQL80

# Start service if stopped
Start-Service MySQL80

# Or use MySQL Installer → Reconfigure → Check "Start at System Startup"
```

### Issue: "ModuleNotFoundError: No module named 'pymysql'"
**Solution:** Install pymysql in correct environment
```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Install pymysql
pip install pymysql==1.1.0
```

### Issue: "(pymysql.err.OperationalError) (2003, 'Can't connect...')"
**Solution:** Check DATABASE_URL format in .env
```env
# Correct format:
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/dbname

# Common mistakes:
# ❌ mysql://... (missing +pymysql)
# ❌ Using wrong port (PostgreSQL 5432 instead of MySQL 3306)
# ❌ Special characters in password not URL-encoded
```

### Issue: Tables not creating / String column errors
**Solution:** This should be fixed already, but if errors occur:
- All String columns now have explicit lengths
- If you see errors about "String type requires a length", check model files
- All models have been updated with proper String(length) definitions

---

## 📊 Verification Checklist

- [ ] MySQL installed and running
- [ ] Database `ektola_db` created
- [ ] User `ektola_user` created with privileges
- [ ] PyMySQL installed (`pip show pymysql`)
- [ ] `.env` file updated with MySQL connection string
- [ ] All tables created successfully (`python create_db.py`)
- [ ] Backend starts without errors (`uvicorn app.main:app --reload`)
- [ ] API documentation accessible (http://127.0.0.1:8000/docs)

---

## 🔄 Rolling Back to PostgreSQL (if needed)

If you need to switch back to PostgreSQL:

1. **Install PostgreSQL driver:**
   ```powershell
   pip install psycopg2-binary==2.9.9
   pip uninstall pymysql
   ```

2. **Update .env:**
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/ektola_db
   ```

3. **Revert requirements.txt** (use git or manually change back)

4. **Note:** Model changes (String lengths) are compatible with both databases, so no need to revert model files

---

## 📝 Key Differences: PostgreSQL vs MySQL

| Feature | PostgreSQL | MySQL |
|---------|-----------|-------|
| String Columns | `String` works | Requires `String(length)` |
| Default Port | 5432 | 3306 |
| Driver | psycopg2-binary | pymysql |
| Connection URL | `postgresql://...` | `mysql+pymysql://...` |
| Character Set | UTF-8 default | Must specify utf8mb4 for emojis |

---

## 🎯 Next Steps

After successful migration:

1. **Test all API endpoints** thoroughly
2. **Create test data** using your existing scripts:
   ```powershell
   python create_test_user.py
   ```
3. **Test WhatsApp integration** with the new database
4. **Monitor performance** - MySQL may have different performance characteristics
5. **Backup regularly** - Set up automated MySQL backups
   ```powershell
   mysqldump -u ektola_user -p ektola_db > backup.sql
   ```

---

## 🆘 Need Help?

- MySQL Documentation: https://dev.mysql.com/doc/
- PyMySQL Documentation: https://pymysql.readthedocs.io/
- SQLAlchemy MySQL Dialect: https://docs.sqlalchemy.org/en/20/dialects/mysql.html

---

**Migration completed successfully!** 🎉

All backend code has been updated for MySQL compatibility. Follow the setup instructions above to configure MySQL on your machine and recreate the database.
