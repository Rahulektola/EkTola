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
            print("\nCreating admin user...")
            from app.core.security import get_password_hash
            hashed_password = get_password_hash("Admin123!@#")
            cursor.execute("""
                INSERT INTO users (email, hashed_password, is_admin, is_active, created_at, updated_at)
                VALUES (%s, %s, 1, 1, NOW(), NOW())
            """, ('admin@ektola.com', hashed_password))
            connection.commit()
            print("✅ Admin user created: admin@ektola.com / Admin123!@#")
            
    connection.close()
    
except Exception as e:
    print(f"❌ Failed: {e}")
