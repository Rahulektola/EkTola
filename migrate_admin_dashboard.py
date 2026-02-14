"""
Database Migration Script: Admin Dashboard Schema Updates
Adds new columns to the jewellers table for admin dashboard features.

Run this script to upgrade your database schema:
    python migrate_admin_dashboard.py

This script is idempotent - safe to run multiple times.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text, inspect


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column already exists in a table"""
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """Apply admin dashboard migrations to the jewellers table"""
    
    new_columns = [
        # (column_name, sql_type, default, comment)
        ("owner_name", "VARCHAR(255) NULL", None, "Owner/proprietor name"),
        ("address", "TEXT NULL", None, "Full business address"),
        ("location", "VARCHAR(255) NULL", None, "City/Area location"),
        ("is_whatsapp_business", "BOOLEAN DEFAULT FALSE", "FALSE", "WhatsApp Business vs Personal"),
        ("meta_app_status", "BOOLEAN DEFAULT FALSE", "FALSE", "Meta App integration status (green light)"),
        ("approval_status", "VARCHAR(20) DEFAULT 'PENDING'", "'PENDING'", "PENDING/APPROVED/REJECTED enum"),
        ("rejection_reason", "TEXT NULL", None, "Mandatory reason when rejected"),
        ("approved_at", "DATETIME NULL", None, "Timestamp of approval"),
        ("approved_by_user_id", "INTEGER NULL", None, "Admin user who approved"),
        ("admin_notes", "TEXT NULL", None, "Admin internal notes (never visible to jeweller)"),
    ]
    
    with engine.connect() as conn:
        print("🔄 Starting admin dashboard migration...")
        print(f"   Database: {engine.url}")
        print()
        
        applied = 0
        skipped = 0
        
        for col_name, col_type, default, comment in new_columns:
            if column_exists(conn, "jewellers", col_name):
                print(f"   ✅ Column '{col_name}' already exists — skipping")
                skipped += 1
            else:
                try:
                    # MySQL syntax
                    sql = f"ALTER TABLE jewellers ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"   ➕ Added column '{col_name}' ({comment})")
                    applied += 1
                except Exception as e:
                    print(f"   ❌ Failed to add '{col_name}': {e}")
        
        # Add foreign key constraint for approved_by_user_id if not exists
        try:
            # Check if FK already exists (MySQL)
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_NAME = 'jewellers' AND COLUMN_NAME = 'approved_by_user_id' "
                "AND REFERENCED_TABLE_NAME = 'users'"
            ))
            fk_count = result.scalar()
            if fk_count == 0 and column_exists(conn, "jewellers", "approved_by_user_id"):
                conn.execute(text(
                    "ALTER TABLE jewellers ADD CONSTRAINT fk_jewellers_approved_by "
                    "FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL"
                ))
                conn.commit()
                print("   ➕ Added FK constraint on approved_by_user_id → users.id")
        except Exception as e:
            print(f"   ⚠️  FK constraint skipped (may already exist or DB type mismatch): {e}")
        
        # Add index on approval_status for filtering
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jewellers_approval_status ON jewellers(approval_status)"
            ))
            conn.commit()
            print("   ➕ Added index on approval_status")
        except Exception:
            # MySQL doesn't support IF NOT EXISTS for indexes in all versions
            try:
                conn.execute(text(
                    "CREATE INDEX idx_jewellers_approval_status ON jewellers(approval_status)"
                ))
                conn.commit()
                print("   ➕ Added index on approval_status")
            except Exception:
                print("   ✅ Index on approval_status already exists — skipping")
        
        # Backfill approval_status from is_approved for existing rows
        try:
            conn.execute(text(
                "UPDATE jewellers SET approval_status = 'APPROVED' "
                "WHERE is_approved = TRUE AND (approval_status IS NULL OR approval_status = 'PENDING')"
            ))
            conn.commit()
            print("   🔄 Backfilled approval_status from is_approved for existing rows")
        except Exception as e:
            print(f"   ⚠️  Backfill skipped: {e}")
        
        print()
        print(f"✅ Migration complete: {applied} columns added, {skipped} already existed")
        print()


if __name__ == "__main__":
    migrate()
