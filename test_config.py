"""Test database configuration"""
from app.config import settings

print("=" * 60)
print("Database Configuration Test")
print("=" * 60)
print(f"DB_USER: {settings.DB_USER}")
print(f"DB_HOST: {settings.DB_HOST}")
print(f"DB_PORT: {settings.DB_PORT}")
print(f"DB_NAME: {settings.DB_NAME}")
print(f"DB_PASSWORD: {'*' * len(settings.DB_PASSWORD)}")
print("\nConstructed DATABASE_URL:")
print(settings.DATABASE_URL)
print("=" * 60)
