"""
Database Migration Script
Migrates existing jeweller data to phone-based authentication
Run this after updating the User model with phone_number field
"""

from app.database import SessionLocal
from app.models.user import User
from app.models.jeweller import Jeweller
from sqlalchemy import text

def migrate_phone_to_user_table():
    """
    Copy phone numbers from Jeweller table to User table
    and update database schema
    """
    db = SessionLocal()
    
    try:
        print("Starting phone migration...")
        
        # Step 1: Add phone_number column to users table (if not exists)
        try:
            db.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS phone_number VARCHAR UNIQUE;
            """))
            print("✓ Added phone_number column to users table")
        except Exception as e:
            print(f"Note: {e}")
        
        # Step 2: Create index on phone_number
        try:
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_phone_number 
                ON users(phone_number);
            """))
            print("✓ Created index on phone_number")
        except Exception as e:
            print(f"Note: {e}")
        
        # Step 3: Rename OTP columns
        try:
            db.execute(text("""
                ALTER TABLE users 
                RENAME COLUMN otp_code TO phone_otp_code;
            """))
            db.execute(text("""
                ALTER TABLE users 
                RENAME COLUMN otp_expiry TO phone_otp_expiry;
            """))
            print("✓ Renamed OTP columns")
        except Exception as e:
            print(f"Note: OTP columns may already be renamed - {e}")
        
        # Step 4: Make email nullable
        try:
            db.execute(text("""
                ALTER TABLE users 
                ALTER COLUMN email DROP NOT NULL;
            """))
            print("✓ Made email column nullable")
        except Exception as e:
            print(f"Note: {e}")
        
        # Step 5: Make hashed_password nullable
        try:
            db.execute(text("""
                ALTER TABLE users 
                ALTER COLUMN hashed_password DROP NOT NULL;
            """))
            print("✓ Made hashed_password column nullable")
        except Exception as e:
            print(f"Note: {e}")
        
        db.commit()
        
        # Step 6: Copy phone numbers from jewellers to users
        jewellers = db.query(Jeweller).all()
        migrated_count = 0
        
        for jeweller in jewellers:
            user = db.query(User).filter(User.id == jeweller.user_id).first()
            if user and not user.phone_number and jeweller.phone_number:
                user.phone_number = jeweller.phone_number
                migrated_count += 1
        
        db.commit()
        print(f"✓ Migrated {migrated_count} phone numbers from jewellers to users")
        
        # Step 7: Report duplicate phone numbers
        duplicates = db.execute(text("""
            SELECT phone_number, COUNT(*) as count
            FROM jewellers
            WHERE phone_number IS NOT NULL
            GROUP BY phone_number
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if duplicates:
            print(f"\n⚠ Warning: Found {len(duplicates)} duplicate phone numbers in jewellers table:")
            for phone, count in duplicates:
                print(f"  - {phone}: {count} occurrences")
            print("  These need manual resolution before making phone_number unique.")
        else:
            print("✓ No duplicate phone numbers found")
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your backend server")
        print("2. Update .env with WhatsApp credentials")
        print("3. Test phone-based authentication")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Phone-Based Authentication Migration")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Add phone_number column to users table")
    print("2. Make email/password optional for jewellers")
    print("3. Rename OTP columns for clarity")
    print("4. Copy phone numbers from jewellers to users")
    print("\n" + "=" * 60)
    
    confirm = input("\nProceed with migration? (yes/no): ")
    
    if confirm.lower() == 'yes':
        migrate_phone_to_user_table()
    else:
        print("Migration cancelled.")
