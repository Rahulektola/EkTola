"""
Create First Admin Account

This script creates the first admin account for the platform.
Run this after setting up the database.
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.admin import Admin
from app.core.security import get_password_hash
from getpass import getpass
import sys

def create_first_admin():
    """Create the first admin account interactively"""
    db = SessionLocal()
    
    try:
        # Check if any admins exist
        existing_count = db.query(Admin).count()
        
        if existing_count > 0:
            print(f"⚠️  Admin accounts already exist ({existing_count} admins found)")
            response = input("Do you want to create another admin? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Aborted.")
                return
        
        print("\n" + "=" * 60)
        print("👤 Create Admin Account")
        print("=" * 60)
        
        # Get admin details
        full_name = input("\nFull Name: ").strip()
        email = input("Email: ").strip()
        phone_number = input("Phone Number (optional): ").strip() or None
        
        # Check if email already exists
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            print(f"❌ Error: Email '{email}' is already registered")
            return
        
        # Get password
        while True:
            password = getpass("Password: ")
            confirm_password = getpass("Confirm Password: ")
            
            if password != confirm_password:
                print("❌ Passwords don't match. Try again.\n")
                continue
            
            if len(password) < 8:
                print("❌ Password must be at least 8 characters long.\n")
                continue
            
            if len(password) > 50:
                print("❌ Password too long. Maximum 50 characters.\n")
                continue
            
            break
        
        # Create admin
        new_admin = Admin(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            hashed_password=get_password_hash(password),
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print("\n✅ Admin account created successfully!")
        print(f"\n📋 Admin Details:")
        print(f"   ID: {new_admin.id}")
        print(f"   Name: {new_admin.full_name}")
        print(f"   Email: {new_admin.email}")
        print(f"   Phone: {new_admin.phone_number or 'Not provided'}")
        
        print(f"\n🔐 You can now login at:")
        print(f"   POST http://localhost:8000/auth/admin/login")
        print(f"   Email: {email}")
        print(f"   Password: [the password you just entered]")
        
    except Exception as e:
        print(f"\n❌ Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    try:
        create_first_admin()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
