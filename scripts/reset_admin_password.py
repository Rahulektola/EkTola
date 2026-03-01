"""Reset admin password"""
import pymysql
import os
from dotenv import load_dotenv
from app.core.security import get_password_hash

load_dotenv()

try:
    # Parse DATABASE_URL
    db_url = os.getenv("DATABASE_URL", "")
    parts = db_url.replace("mysql+pymysql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")
    
    connection = pymysql.connect(
        host=host_port[0],
        port=int(host_port[1]) if len(host_port) > 1 else 3306,
        user=user_pass[0],
        password=user_pass[1],
        database=host_port_db[1],
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        # Get email and new password from user
        email = input("Enter admin email [admin@ektola.com]: ").strip() or "admin@ektola.com"
        new_password = input("Enter new password: ").strip()
        
        if not new_password:
            print("❌ Password cannot be empty!")
            connection.close()
            exit(1)
        
        hashed = get_password_hash(new_password)
        
        cursor.execute("""
            UPDATE users 
            SET hashed_password = %s 
            WHERE email = %s AND is_admin = 1
        """, (hashed, email))
        connection.commit()
        
        if cursor.rowcount > 0:
            print("✅ Admin password reset successfully!")
            print(f"\nAdmin email: {email}")
        else:
            print(f"❌ No admin user found with email: {email}")
            
    connection.close()
    
except Exception as e:
    print(f"❌ Failed: {e}")
