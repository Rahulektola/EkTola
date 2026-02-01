"""
Create test jeweller user with phone authentication
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt

# Direct database connection
engine = create_engine('postgresql://postgres:postgres@localhost:5432/ektola_db')
Session = sessionmaker(bind=engine)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def create_test_jeweller():
    """Create a test jeweller with phone number"""
    session = Session()
    
    try:
        # Check if user already exists
        result = session.execute(text("SELECT id FROM users WHERE phone_number = :phone"), 
                                {"phone": "+919876543210"})
        if result.fetchone():
            print("⚠ Test user already exists!")
            return
        
        # Create user with phone number
        hashed_pwd = hash_password("test1234")
        session.execute(text("""
            INSERT INTO users (phone_number, email, hashed_password, is_admin, is_active, created_at, updated_at)
            VALUES (:phone, :email, :password, :is_admin, :is_active, NOW(), NOW())
        """), {
            "phone": "+919876543210",
            "email": "test@jeweller.com",
            "password": hashed_pwd,
            "is_admin": False,
            "is_active": True
        })
        
        # Get user ID
        result = session.execute(text("SELECT id FROM users WHERE phone_number = :phone"), 
                                {"phone": "+919876543210"})
        user_id = result.fetchone()[0]
        
        # Create jeweller profile
        session.execute(text("""
            INSERT INTO jewellers (user_id, business_name, phone_number, is_approved, is_active, timezone, created_at, updated_at)
            VALUES (:user_id, :business_name, :phone, :is_approved, :is_active, :timezone, NOW(), NOW())
        """), {
            "user_id": user_id,
            "business_name": "Golden Ornaments",
            "phone": "+919876543210",
            "is_approved": True,
            "is_active": True,
            "timezone": "Asia/Kolkata"
        })
        
        session.commit()
        
        print("✅ Test jeweller created successfully!")
        print("\nLogin credentials:")
        print("  Phone: +919876543210")
        print("  Password: test1234")
        print("\nYou can now test:")
        print("  1. Password login with phone number")
        print("  2. WhatsApp OTP login")
        
    except Exception as e:
        print(f"❌ Failed to create test user: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_test_jeweller()
