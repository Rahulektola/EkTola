"""
PostgreSQL Connection Tester

This script helps you find the correct DATABASE_URL for your .env file.
"""
import sys
from sqlalchemy import create_engine, text

def test_database_url(db_url):
    """Test if a database URL works"""
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            return True, version
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("🔍 PostgreSQL Connection Tester")
    print("=" * 70)
    print("\nThis will help you find the correct DATABASE_URL for your .env file")
    
    # Get database details
    print("\n📝 Enter your PostgreSQL connection details:")
    username = input("Username (default: postgres): ").strip() or "postgres"
    password = input("Password: ").strip()
    host = input("Host (default: localhost): ").strip() or "localhost"
    port = input("Port (default: 5432): ").strip() or "5432"
    database = input("Database (default: ektola): ").strip() or "ektola"
    
    # Build database URL
    db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    print(f"\n🔗 Testing connection...")
    print(f"   URL: postgresql://{username}:***@{host}:{port}/{database}")
    
    success, result = test_database_url(db_url)
    
    if success:
        print(f"\n✅ Connection successful!")
        print(f"   PostgreSQL version: {result}")
        print(f"\n📋 Add this to your .env file:")
        print(f"\nDATABASE_URL={db_url}")
        print(f"\n💡 You can now run: python setup_database.py")
    else:
        print(f"\n❌ Connection failed!")
        print(f"   Error: {result}")
        print(f"\n💡 Troubleshooting tips:")
        print(f"   1. Check if PostgreSQL is running:")
        print(f"      pg_ctl status -D \"C:\\Program Files\\PostgreSQL\\[version]\\data\"")
        print(f"   2. Verify your username and password")
        print(f"   3. Try connecting with psql:")
        print(f"      psql -U {username} -d {database}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
