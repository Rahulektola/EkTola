"""Check admin users in database"""
import pymysql
import os
from dotenv import load_dotenv

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
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        # Get all admin users
        cursor.execute("SELECT id, email, is_admin, is_active FROM users WHERE is_admin = 1")
        admins = cursor.fetchall()
        print("=== ADMIN USERS ===")
        for admin in admins:
            print(f"  - ID: {admin['id']}, Email: {admin['email']}, Active: {admin['is_active']}")
        
        if not admins:
            print("  ❌ No admin users found!")
            create = input("\nCreate admin user? (y/n): ").strip().lower()
            
            if create == 'y':
                from app.core.security import get_password_hash
                email = input("Enter admin email [admin@ektola.com]: ").strip() or "admin@ektola.com"
                password = input("Enter admin password: ").strip()
                
                if not password:
                    print("❌ Password cannot be empty!")
                else:
                    hashed_password = get_password_hash(password)
                    cursor.execute("""
                        INSERT INTO users (email, hashed_password, is_admin, is_active, created_at, updated_at)
                        VALUES (%s, %s, 1, 1, NOW(), NOW())
                    """, (email, hashed_password))
                    connection.commit()
                    print(f"✅ Admin user created: {email}")
                    print("⚠️  Remember to save this password securely!")
            
    connection.close()
    
except Exception as e:
    print(f"❌ Failed: {e}")
