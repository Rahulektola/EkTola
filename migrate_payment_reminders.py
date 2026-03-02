"""
Migration Script: Add Payment Reminder Scheduling Fields
=========================================================
Adds SIP/Loan payment scheduling columns to the contacts table
and scheduled_at + message_type to the messages table.

Run:  python migrate_payment_reminders.py

Safe to re-run – checks for column existence before altering.
"""
import sys
from sqlalchemy import text, inspect
from app.database import engine


def column_exists(inspector, table: str, column: str) -> bool:
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def run_migration():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    with engine.begin() as conn:
        # ===============================================================
        # 1. CONTACTS TABLE — payment scheduling fields
        # ===============================================================
        if "contacts" not in tables:
            print("❌ 'contacts' table does not exist. Run create_db.py first.")
            sys.exit(1)

        contact_columns = {
            "sip_payment_day":           "INTEGER NULL",
            "loan_payment_day":          "INTEGER NULL",
            "sip_reminder_days_before":  "INTEGER NOT NULL DEFAULT 3",
            "loan_reminder_days_before": "INTEGER NOT NULL DEFAULT 3",
            "last_sip_reminder_sent_at": "TIMESTAMP NULL",
            "last_loan_reminder_sent_at":"TIMESTAMP NULL",
        }

        for col_name, col_def in contact_columns.items():
            if column_exists(inspector, "contacts", col_name):
                print(f"  ⏭  contacts.{col_name} already exists — skipping")
            else:
                conn.execute(text(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_def}"))
                print(f"  ✅ Added contacts.{col_name}")

        # Check constraints (best-effort, may not be supported by all engines)
        try:
            conn.execute(text(
                "ALTER TABLE contacts ADD CONSTRAINT ck_sip_day_range "
                "CHECK (sip_payment_day IS NULL OR (sip_payment_day >= 1 AND sip_payment_day <= 31))"
            ))
            print("  ✅ Added CHECK constraint ck_sip_day_range")
        except Exception:
            print("  ⏭  CHECK constraint ck_sip_day_range already exists or not supported")

        try:
            conn.execute(text(
                "ALTER TABLE contacts ADD CONSTRAINT ck_loan_day_range "
                "CHECK (loan_payment_day IS NULL OR (loan_payment_day >= 1 AND loan_payment_day <= 31))"
            ))
            print("  ✅ Added CHECK constraint ck_loan_day_range")
        except Exception:
            print("  ⏭  CHECK constraint ck_loan_day_range already exists or not supported")

        # Indexes
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jeweller_sip_day ON contacts (jeweller_id, sip_payment_day)"
            ))
            print("  ✅ Created index idx_jeweller_sip_day")
        except Exception:
            print("  ⏭  Index idx_jeweller_sip_day already exists")

        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jeweller_loan_day ON contacts (jeweller_id, loan_payment_day)"
            ))
            print("  ✅ Created index idx_jeweller_loan_day")
        except Exception:
            print("  ⏭  Index idx_jeweller_loan_day already exists")

        # ===============================================================
        # 2. MESSAGES TABLE — scheduled_at + message_type
        # ===============================================================
        if "messages" not in tables:
            print("❌ 'messages' table does not exist. Run create_db.py first.")
            sys.exit(1)

        if not column_exists(inspector, "messages", "scheduled_at"):
            conn.execute(text("ALTER TABLE messages ADD COLUMN scheduled_at TIMESTAMP NULL"))
            print("  ✅ Added messages.scheduled_at")
        else:
            print("  ⏭  messages.scheduled_at already exists — skipping")

        if not column_exists(inspector, "messages", "message_type"):
            conn.execute(text(
                "ALTER TABLE messages ADD COLUMN message_type VARCHAR(20) NOT NULL DEFAULT 'CAMPAIGN'"
            ))
            print("  ✅ Added messages.message_type")
        else:
            print("  ⏭  messages.message_type already exists — skipping")

        # Indexes
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_status_scheduled ON messages (status, scheduled_at)"
            ))
            print("  ✅ Created index idx_status_scheduled")
        except Exception:
            print("  ⏭  Index idx_status_scheduled already exists")

        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_type_status ON messages (message_type, status)"
            ))
            print("  ✅ Created index idx_type_status")
        except Exception:
            print("  ⏭  Index idx_type_status already exists")

    print("\n🎉 Migration completed successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("Payment Reminder Scheduling Migration")
    print("=" * 60)
    run_migration()
