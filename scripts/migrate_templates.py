"""
Migration: Align templates table with updated SQLAlchemy model.

The existing templates table has the old per-jeweller schema:
  id, jeweller_id, name, content, variables, language, is_system_template, is_active, created_at, updated_at

The new model expects an admin-managed WhatsApp template schema:
  id, template_name, display_name, campaign_type, sub_segment, description,
  category, is_active, variable_count, variable_names, created_at, updated_at
  + a separate template_translations table

This migration:
1. Adds missing columns to the templates table
2. Populates template_name / display_name from the existing `name` column
3. Creates the template_translations table
4. Migrates existing rows into a single English translation
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

def column_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
    ), {"tbl": table, "col": column})
    return result.scalar() > 0

def table_exists(conn, table):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :tbl"
    ), {"tbl": table})
    return result.scalar() > 0

def run_migration():
    with engine.connect() as conn:
        # ── Step 1: Add missing columns to templates ──────────────────────────

        if not column_exists(conn, "templates", "template_name"):
            print("Adding column: template_name")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN template_name VARCHAR(255) NULL"
            ))

        if not column_exists(conn, "templates", "display_name"):
            print("Adding column: display_name")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN display_name VARCHAR(255) NULL"
            ))

        if not column_exists(conn, "templates", "campaign_type"):
            print("Adding column: campaign_type")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN campaign_type ENUM('UTILITY','MARKETING') NULL"
            ))

        if not column_exists(conn, "templates", "sub_segment"):
            print("Adding column: sub_segment")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN sub_segment "
                "ENUM('GOLD_LOAN','GOLD_SIP','BOTH','MARKETING') NULL"
            ))

        if not column_exists(conn, "templates", "description"):
            print("Adding column: description")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN description TEXT NULL"
            ))

        if not column_exists(conn, "templates", "category"):
            print("Adding column: category")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN category VARCHAR(100) NULL DEFAULT 'MARKETING'"
            ))

        if not column_exists(conn, "templates", "variable_count"):
            print("Adding column: variable_count")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN variable_count INT NOT NULL DEFAULT 0"
            ))

        if not column_exists(conn, "templates", "variable_names"):
            print("Adding column: variable_names")
            conn.execute(text(
                "ALTER TABLE templates ADD COLUMN variable_names TEXT NULL"
            ))

        conn.commit()

        # ── Step 2: Populate template_name / display_name from `name` ─────────
        if column_exists(conn, "templates", "name"):
            print("Populating template_name and display_name from existing name column...")
            conn.execute(text(
                "UPDATE templates SET "
                "  template_name = IFNULL(template_name, LOWER(REPLACE(name, ' ', '_'))), "
                "  display_name  = IFNULL(display_name, name), "
                "  category      = IFNULL(category, 'MARKETING'), "
                "  campaign_type = IFNULL(campaign_type, 'MARKETING') "
                "WHERE template_name IS NULL OR display_name IS NULL"
            ))
            conn.commit()

        # Make template_name NOT NULL + UNIQUE once populated
        # (Only if there are no NULLs left)
        null_count = conn.execute(text(
            "SELECT COUNT(*) FROM templates WHERE template_name IS NULL"
        )).scalar()
        if null_count == 0:
            try:
                conn.execute(text(
                    "ALTER TABLE templates MODIFY template_name VARCHAR(255) NOT NULL"
                ))
                # Add unique index only if it doesn't exist
                idx_exists = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='templates' "
                    "AND INDEX_NAME='uq_template_name'"
                )).scalar()
                if not idx_exists:
                    conn.execute(text(
                        "ALTER TABLE templates ADD UNIQUE INDEX uq_template_name (template_name)"
                    ))
                conn.commit()
                print("template_name set to NOT NULL with UNIQUE index.")
            except Exception as e:
                print(f"Note: Could not add NOT NULL/UNIQUE on template_name: {e}")
                conn.rollback()

        # ── Step 3: Create template_translations table ────────────────────────
        if not table_exists(conn, "template_translations"):
            print("Creating table: template_translations")
            conn.execute(text("""
                CREATE TABLE template_translations (
                    id               INT AUTO_INCREMENT PRIMARY KEY,
                    template_id      INT NOT NULL,
                    language         ENUM('en','hi','kn','mr','ta','pa') NOT NULL,
                    header_text      VARCHAR(500) NULL,
                    body_text        TEXT NOT NULL,
                    footer_text      VARCHAR(500) NULL,
                    whatsapp_template_id VARCHAR(255) NULL,
                    approval_status  VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_tt_template FOREIGN KEY (template_id)
                        REFERENCES templates(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_template_lang (template_id, language)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            conn.commit()
            print("template_translations table created.")

        # ── Step 4: Migrate existing template rows to translations ─────────────
        if column_exists(conn, "templates", "content"):
            print("Migrating existing template content to template_translations...")
            # Only migrate rows that don't already have a translation
            rows = conn.execute(text(
                "SELECT t.id, t.content, t.language "
                "FROM templates t "
                "LEFT JOIN template_translations tt ON tt.template_id = t.id "
                "WHERE tt.id IS NULL AND t.content IS NOT NULL"
            )).fetchall()

            lang_map = {
                "ENGLISH": "en", "HINDI": "hi", "GUJARATI": "en",
                "MARATHI": "mr", "KANNADA": "kn", "TAMIL": "ta", "PUNJABI": "pa"
            }

            for row in rows:
                tid, content, lang_raw = row
                lang = lang_map.get(lang_raw or "ENGLISH", "en")
                conn.execute(text(
                    "INSERT IGNORE INTO template_translations "
                    "(template_id, language, body_text, approval_status) "
                    "VALUES (:tid, :lang, :body, 'APPROVED')"
                ), {"tid": tid, "lang": lang, "body": content})

            conn.commit()
            print(f"Migrated {len(rows)} existing template(s) to translations.")

        print("\n✅ Migration complete!")


if __name__ == "__main__":
    run_migration()
