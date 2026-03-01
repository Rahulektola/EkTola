"""
Migration script to add WhatsApp Embedded Signup fields to jewellers table

Run this script to add the new columns required for WhatsApp Embedded Signup.
"""

import sys
from sqlalchemy import text
from app.database import engine

# New columns to add
NEW_COLUMNS = [
    ("fb_app_scoped_user_id", "VARCHAR(100) NULL"),
    ("access_token_expires_at", "DATETIME NULL"),
    ("waba_name", "VARCHAR(255) NULL"),
    ("phone_display_number", "VARCHAR(50) NULL"),
    ("business_verification_status", "VARCHAR(50) DEFAULT 'pending'"),
    ("whatsapp_connected_at", "DATETIME NULL"),
    ("last_token_refresh", "DATETIME NULL"),
]

def check_column_exists(conn, column_name):
    """Check if column already exists in jewellers table"""
    result = conn.execute(text("""
        SELECT COUNT(*) as count 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'jewellers' 
        AND COLUMN_NAME = :column_name
        AND TABLE_SCHEMA = DATABASE()
    """), {"column_name": column_name})
    return result.fetchone()[0] > 0

def migrate():
    """Add new columns to jewellers table"""
    print("=" * 60)
    print("WhatsApp Embedded Signup Migration")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if jewellers table exists
        result = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'jewellers' 
            AND TABLE_SCHEMA = DATABASE()
        """))
        
        if result.fetchone()[0] == 0:
            print("\n⚠️  Warning: 'jewellers' table does not exist.")
            print("   Run 'python create_db.py' first to create all tables.")
            return False
        
        print("\n✓ Found 'jewellers' table")
        print("\nAdding new columns:")
        print("-" * 40)
        
        added_count = 0
        skipped_count = 0
        
        for column_name, column_def in NEW_COLUMNS:
            if check_column_exists(conn, column_name):
                print(f"  • {column_name}: Already exists (skipped)")
                skipped_count += 1
            else:
                try:
                    alter_sql = f"ALTER TABLE jewellers ADD COLUMN {column_name} {column_def}"
                    conn.execute(text(alter_sql))
                    conn.commit()
                    print(f"  ✓ {column_name}: Added successfully")
                    added_count += 1
                except Exception as e:
                    print(f"  ✗ {column_name}: Failed - {e}")
                    return False
        
        print("-" * 40)
        print(f"\n✅ Migration complete!")
        print(f"   Added: {added_count} columns")
        print(f"   Skipped (already exist): {skipped_count} columns")
        
        # Show current jewellers table structure
        print("\n" + "=" * 60)
        print("Current 'jewellers' table structure:")
        print("-" * 40)
        
        result = conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'jewellers' 
            AND TABLE_SCHEMA = DATABASE()
            ORDER BY ORDINAL_POSITION
        """))
        
        for row in result:
            nullable = "NULL" if row[2] == "YES" else "NOT NULL"
            default = f"DEFAULT {row[3]}" if row[3] else ""
            print(f"  {row[0]}: {row[1]} {nullable} {default}")
        
        print("=" * 60)
        
    return True

def rollback():
    """Remove the added columns (for reverting)"""
    print("=" * 60)
    print("WhatsApp Embedded Signup Migration - ROLLBACK")
    print("=" * 60)
    
    confirm = input("\n⚠️  This will remove WhatsApp Embedded Signup columns. Are you sure? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Rollback cancelled.")
        return False
    
    with engine.connect() as conn:
        print("\nRemoving columns:")
        print("-" * 40)
        
        for column_name, _ in NEW_COLUMNS:
            if check_column_exists(conn, column_name):
                try:
                    conn.execute(text(f"ALTER TABLE jewellers DROP COLUMN {column_name}"))
                    conn.commit()
                    print(f"  ✓ {column_name}: Removed")
                except Exception as e:
                    print(f"  ✗ {column_name}: Failed - {e}")
            else:
                print(f"  • {column_name}: Does not exist (skipped)")
        
        print("-" * 40)
        print("\n✅ Rollback complete!")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback()
    else:
        migrate()
