from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis
    REDIS_URL: str
    
    # WhatsApp Cloud API Settings
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str = ""  # Your WhatsApp Business Phone Number ID
    WHATSAPP_ACCESS_TOKEN: str = ""  # Your WhatsApp Business API access token
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""  # WhatsApp Business Account ID for template management
    WHATSAPP_APP_ID: str = ""  # Facebook App ID
    WHATSAPP_APP_SECRET: str = ""  # Facebook App Secret
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = ""  # Token for webhook verification
    WHATSAPP_OTP_TEMPLATE_NAME: str = "otp_verification"  # Approved template name
    
    # Environment
    ENVIRONMENT: str = "development"
    
    #Admin access code
    ADMIN_ACCESS_CODE: str = ""

    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
