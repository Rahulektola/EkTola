"""
Create sample jeweller data for testing admin dashboard
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set. Check your .env file.")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def create_sample_jewellers():
    """Create sample jewellers with different statuses"""
    session = Session()
    
    try:
        # Sample jeweller data
        jewellers_data = [
            {
                "business_name": "Golden Ornaments",
                "phone": "+919876543210",
                "email": "rajesh@golden.com",
                "is_approved": True,
                "contacts": 50
            },
            {
                "business_name": "Silver Touch Jewellery",
                "phone": "+919876543211",
                "email": "priya@silvertouch.com",
                "is_approved": False,
                "contacts": 30
            },
            {
                "business_name": "Diamond Palace",
                "phone": "+919876543212",
                "email": "amit@diamond.com",
                "is_approved": True,
                "contacts": 75
            },
            {
                "business_name": "Ruby Collections",
                "phone": "+919876543213",
                "email": "sunita@ruby.com",
                "is_approved": False,
                "contacts": 20
            },
            {
                "business_name": "Pearl Jewellers",
                "phone": "+919876543214",
                "email": "mohan@pearl.com",
                "is_approved": False,
                "contacts": 0
            },
            {
                "business_name": "Emerald Palace",
                "phone": "+919876543215",
                "email": "kavita@emerald.com",
                "is_approved": True,
                "contacts": 100
            }
        ]
        
        created_count = 0
        
        for jdata in jewellers_data:
            # Check if user already exists
            result = session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": jdata["email"]}
            )
            existing_user = result.fetchone()
            
            if existing_user:
                print(f"⚠ User {jdata['email']} already exists, skipping...")
                continue
            
            # Create user
            hashed_pwd = hash_password("jeweller123")
            session.execute(text("""
                INSERT INTO users (email, hashed_password, is_admin, is_active, created_at, updated_at)
                VALUES (:email, :password, :is_admin, :is_active, NOW(), NOW())
            """), {
                "email": jdata["email"],
                "password": hashed_pwd,
                "is_admin": False,
                "is_active": True
            })
            
            # Get user ID
            result = session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": jdata["email"]}
            )
            user_id = result.fetchone()[0]
            
            # Create jeweller profile
            created_at = datetime.now() - timedelta(days=random.randint(1, 30))
            
            session.execute(text("""
                INSERT INTO jewellers (
                    user_id, business_name, phone_number,
                    is_approved, is_active, timezone, created_at, updated_at
                )
                VALUES (
                    :user_id, :business_name, :phone,
                    :is_approved, :is_active, :timezone, :created_at, NOW()
                )
            """), {
                "user_id": user_id,
                "business_name": jdata["business_name"],
                "phone": jdata["phone"],
                "is_approved": jdata["is_approved"],
                "is_active": True,
                "timezone": "Asia/Kolkata",
                "created_at": created_at
            })
            
            # Get jeweller ID
            result = session.execute(
                text("SELECT id FROM jewellers WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            jeweller_id = result.fetchone()[0]
            
            # Create sample contacts for approved jewellers
            if jdata["is_approved"] and jdata["contacts"] > 0:
                for i in range(jdata["contacts"]):
                    phone = f"+9198765{43216 + i}"
                    session.execute(text("""
                        INSERT INTO contacts (
                            jeweller_id, name, phone_number, preferred_language, segment,
                            opted_out, is_deleted, created_at, updated_at
                        )
                        VALUES (
                            :jeweller_id, :name, :phone_number, :preferred_language, :segment,
                            :opted_out, :is_deleted, NOW(), NOW()
                        )
                    """), {
                        "jeweller_id": jeweller_id,
                        "name": f"Customer {i+1}",
                        "phone_number": phone,
                        "preferred_language": random.choice(["ENGLISH", "HINDI", "GUJARATI", "MARATHI"]),
                        "segment": random.choice(["GOLD_LOAN", "GOLD_SIP", "MARKETING"]),
                        "opted_out": False,
                        "is_deleted": False
                    })
            
            created_count += 1
            status_text = "APPROVED" if jdata["is_approved"] else "PENDING"
            print(f"✅ Created {jdata['business_name']} ({status_text}) with {jdata['contacts']} contacts")
        
        session.commit()
        
        print(f"\n✅ Successfully created {created_count} sample jewellers!")
        print("\nLogin credentials for jewellers:")
        print("  Password:approval:")
        print("  - Use admin dashboard to approve pending jewellers")
        print("  - Approved jewellers can login and create campaignsoval")
        print("  - REJECTED: Cannot use the system")
        
    except Exception as e:
        print(f"❌ Failed to create sample data: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    print("Creating sample jeweller data for testing...\n")
    create_sample_jewellers()
