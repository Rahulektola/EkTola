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
        # Update admin password
        new_password = "Admin123!@#"
        hashed = get_password_hash(new_password)
        
        cursor.execute("""
            UPDATE users 
            SET hashed_password = %s 
            WHERE email = 'admin@example.com' AND is_admin = 1
        """, (hashed,))
        connection.commit()
        
        print("✅ Admin password reset successfully!")
        print(f"\nLogin credentials:")
        print(f"  Email: admin@example.com")
        print(f"  Password: {new_password}")
            
    connection.close()
    
except Exception as e:
    print(f"❌ Failed: {e}")
