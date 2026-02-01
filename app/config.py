from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30  # For jewellers
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis
    REDIS_URL: str
    
    # WhatsApp API
    WHATSAPP_API_VERSION: str = "v18.0"
    
    # Platform WhatsApp (for sending OTPs to jewellers)
    PLATFORM_WHATSAPP_TOKEN: Optional[str] = None
    PLATFORM_PHONE_NUMBER_ID: Optional[str] = None
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
