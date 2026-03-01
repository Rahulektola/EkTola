"""
Database Audit Script for Contacts
Checks for data integrity issues with jeweller_id associations
"""
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from app.database import engine
# Import all models to ensure relationships work
from app.models.user import User
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.models.template import Template
from app.models.campaign import Campaign, CampaignRun
from app.models.message import Message
from app.models.webhook import WebhookEvent

def audit_contacts():
    """Audit contacts table for data integrity issues"""
    Session = sessionmaker(bind=engine)
    db = Session()
    
    print("=" * 80)
    print("CONTACT DATABASE AUDIT")
    print("=" * 80)
    
    try:
        # 1. Check for contacts with NULL jeweller_id
        null_jeweller_count = db.query(Contact).filter(Contact.jeweller_id == None).count()
        print(f"\n1. Contacts with NULL jeweller_id: {null_jeweller_count}")
        
        if null_jeweller_count > 0:
            null_contacts = db.query(Contact).filter(Contact.jeweller_id == None).limit(10).all()
            print("\n   Sample contacts with NULL jeweller_id:")
            print(f"   {'ID':<10} {'Name':<30} {'Phone':<15}")
            print(f"   {'-'*10} {'-'*30} {'-'*15}")
            for c in null_contacts:
                print(f"   {c.id:<10} {(c.name or 'N/A'):<30} {c.phone_number:<15}")
        
        # 2. Check for contacts with invalid jeweller_id (not in jewellers table)
        print("\n2. Checking for orphaned contacts (invalid jeweller_id)...")
        orphaned = db.query(Contact).outerjoin(Jeweller, Contact.jeweller_id == Jeweller.id).filter(
            Contact.jeweller_id != None,
            Jeweller.id == None
        ).count()
        print(f"   Orphaned contacts: {orphaned}")
        
        # 3. Distribution of contacts by jeweller
        print("\n3. Contact distribution by jeweller:")
        distribution = db.query(
            Jeweller.id,
            Jeweller.business_name,
            func.count(Contact.id).label('contact_count')
        ).outerjoin(Contact, Jeweller.id == Contact.jeweller_id).filter(
            Contact.is_deleted == False
        ).group_by(Jeweller.id).order_by(func.count(Contact.id).desc()).all()
        
        if distribution:
            print(f"   {'Jeweller ID':<15} {'Business Name':<40} {'Contacts':<10}")
            print(f"   {'-'*15} {'-'*40} {'-'*10}")
            for j in distribution:
                print(f"   {j.id:<15} {j.business_name:<40} {j.contact_count:<10}")
        else:
            print("   No jewellers with contacts found")
        
        # 4. Total counts
        total_contacts = db.query(Contact).filter(Contact.is_deleted == False).count()
        total_jewellers = db.query(Jeweller).count()
        
        print(f"\n4. Summary:")
        print(f"   Total jewellers: {total_jewellers}")
        print(f"   Total active contacts: {total_contacts}")
        print(f"   Contacts with NULL jeweller_id: {null_jeweller_count}")
        print(f"   Orphaned contacts: {orphaned}")
        
        # 5. Check for jewellers with 0 contacts
        jewellers_no_contacts = db.query(Jeweller).outerjoin(
            Contact, Jeweller.id == Contact.jeweller_id
        ).filter(Contact.id == None).count()
        
        print(f"   Jewellers with 0 contacts: {jewellers_no_contacts}")
        
        if jewellers_no_contacts > 0:
            print("\n   Jewellers with no contacts:")
            no_contact_jewellers = db.query(Jeweller).outerjoin(
                Contact, Jeweller.id == Contact.jeweller_id
            ).filter(Contact.id == None).limit(10).all()
            print(f"   {'ID':<10} {'Business Name':<40} {'Phone':<15}")
            print(f"   {'-'*10} {'-'*40} {'-'*15}")
            for j in no_contact_jewellers:
                print(f"   {j.id:<10} {j.business_name:<40} {j.phone_number:<15}")
        
        print("\n" + "=" * 80)
        print("AUDIT COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error during audit: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    audit_contacts()
