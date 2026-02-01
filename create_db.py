"""
Create fresh database with phone authentication schema
"""

from app.database import Base, engine
from app.models.user import User
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.models.campaign import Campaign
from app.models.message import Message
from app.models.template import Template
from app.models.webhook import WebhookEvent

def create_all_tables():
    """Create all database tables"""
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
    print("\nTables created:")
    for table in Base.metadata.tables.keys():
        print(f"  - {table}")

if __name__ == "__main__":
    create_all_tables()
