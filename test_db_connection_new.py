"""Test database connection with new credentials"""
from sqlalchemy import create_engine, text
from app.config import settings

print("=" * 60)
print("Testing Database Connection")
print("=" * 60)
print(f"User: {settings.DB_USER}")
print(f"Database: {settings.DB_NAME}")
print(f"URL: {settings.DATABASE_URL.replace(settings.DB_PASSWORD, '***')}")
print("=" * 60)

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print("✅ Connection successful!")
        print(f"PostgreSQL: {version}")
        
        # Check for tables
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public';
        """))
        table_count = result.fetchone()[0]
        print(f"\nTables in database: {table_count}")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
