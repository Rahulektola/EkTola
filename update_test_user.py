"""
Update existing test user with phone number
"""
from sqlalchemy import create_engine, text
import bcrypt

engine = create_engine('postgresql://postgres:postgres@localhost:5432/ektola_db')
conn = engine.connect()

try:
    # Hash password
    pwd = bcrypt.hashpw('test1234'.encode('utf-8')[:72], bcrypt.gensalt()).decode('utf-8')
    
    # Update user
    conn.execute(text("""
        UPDATE users 
        SET phone_number = '+919876543210', 
            hashed_password = :pwd 
        WHERE email = 'test@jeweller.com'
    """), {'pwd': pwd})
    
    # Get user ID
    result = conn.execute(text("SELECT id FROM users WHERE email = 'test@jeweller.com'")).fetchone()
    user_id = result[0]
    
    # Update jeweller
    conn.execute(text("""
        UPDATE jewellers 
        SET phone_number = '+919876543210' 
        WHERE user_id = :uid
    """), {'uid': user_id})
    
    conn.commit()
    print("✅ Test user updated successfully!")
    print("\nLogin credentials:")
    print("  Phone: +919876543210 (or just 9876543210)")
    print("  Password: test1234")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    conn.rollback()
finally:
    conn.close()
