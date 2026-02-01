"""
Script to create the first Super Admin user for EkTola platform.
Run this after database migrations to set up initial admin access.

Usage:
    python create_super_admin.py
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.admin import Admin, AdminRole
from app.core.security import get_password_hash
import sys


def create_super_admin():
    """Create first super admin interactively"""
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print("🔐 EkTola Platform - Super Admin Creation")
        print("="*60 + "\n")
        
        # Get input
        email = input("Enter admin email: ").strip()
        if not email or "@" not in email:
            print("❌ Invalid email address!")
            return
        
        full_name = input("Enter full name: ").strip()
        if not full_name:
            print("❌ Full name is required!")
            return
        
        password = input("Enter password (min 8 chars): ").strip()
        if len(password) < 8:
            print("❌ Password must be at least 8 characters!")
            return
        
        phone = input("Enter phone number (optional, press Enter to skip): ").strip()
        phone = phone if phone else None
        
        # Check if exists
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            print(f"\n❌ Admin with email '{email}' already exists!")
            return
        
        # Create admin
        admin = Admin(
            full_name=full_name,
            email=email,
            phone_number=phone,
            hashed_password=get_password_hash(password),
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
            can_manage_jewellers=True,
            can_view_analytics=True,
            can_manage_templates=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\n" + "="*60)
        print("✅ Super Admin Created Successfully!")
        print("="*60)
        print(f"\nID:        {admin.id}")
        print(f"Name:      {admin.full_name}")
        print(f"Email:     {admin.email}")
        print(f"Phone:     {admin.phone_number or 'Not provided'}")
        print(f"Role:      {admin.role.value}")
        print(f"\n📝 You can now login at POST /auth/admin/login")
        print(f"   with email: {admin.email}")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
        db.rollback()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error creating super admin: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def list_existing_admins():
    """List all existing admins"""
    db = SessionLocal()
    try:
        admins = db.query(Admin).all()
        
        if not admins:
            print("\nℹ️  No admins found in database.\n")
            return
        
        print("\n" + "="*60)
        print(f"📋 Existing Admins ({len(admins)})")
        print("="*60 + "\n")
        
        for admin in admins:
            status = "✅ Active" if admin.is_active else "❌ Inactive"
            print(f"ID: {admin.id}")
            print(f"Name: {admin.full_name}")
            print(f"Email: {admin.email}")
            print(f"Role: {admin.role.value}")
            print(f"Status: {status}")
            print("-" * 60)
        print()
        
    except Exception as e:
        print(f"❌ Error listing admins: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_existing_admins()
    else:
        # Check if any admins exist
        db = SessionLocal()
        admin_count = db.query(Admin).count()
        db.close()
        
        if admin_count > 0:
            print(f"\nℹ️  {admin_count} admin(s) already exist in the system.")
            response = input("Do you want to create another admin? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("\n👋 Use --list flag to see existing admins.")
                sys.exit(0)
        
        create_super_admin()
