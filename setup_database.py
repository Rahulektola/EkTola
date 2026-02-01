"""
Database Setup Script

This script will:
1. Test database connection
2. Create all tables using SQLAlchemy
3. Show database status
"""
import sys
from sqlalchemy import create_engine, text
from app.database import Base, engine
from app.models import *  # Import all models

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"   PostgreSQL version: {version}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"\n💡 Please check your .env file:")
        print(f"   DATABASE_URL should be: postgresql://username:password@localhost:5432/ektola")
        return False

def create_tables():
    """Create all database tables"""
    try:
        print(f"\n📦 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print(f"✅ All tables created successfully!")
        
        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"\n📋 Created tables:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print(f"⚠️  No tables found")
                
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

def show_status():
    """Show database status"""
    try:
        with engine.connect() as conn:
            # Count tables
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM pg_tables 
                WHERE schemaname = 'public';
            """))
            table_count = result.fetchone()[0]
            
            print(f"\n📊 Database Status:")
            print(f"   Total tables: {table_count}")
            print(f"   Database ready: {'✅ Yes' if table_count > 0 else '❌ No'}")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 EkTola Database Setup")
    print("=" * 60)
    
    # Test connection
    if not test_connection():
        sys.exit(1)
    
    # Create tables
    if not create_tables():
        sys.exit(1)
    
    # Show status
    show_status()
    
    print("\n" + "=" * 60)
    print("✅ Database setup complete!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Create first admin: python create_first_admin.py")
    print("   2. Start the server: uvicorn app.main:app --reload")
    print("   3. View API docs: http://localhost:8000/docs")
