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
    
    # WhatsApp Business API Settings (via PyWa) - Platform Account
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str = ""  # Platform WhatsApp Phone Number ID (for OTPs)
    WHATSAPP_ACCESS_TOKEN: str = ""  # Platform WhatsApp API access token
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""  # Platform WABA ID for template management
    WHATSAPP_APP_ID: str = ""  # Facebook App ID
    WHATSAPP_APP_SECRET: str = ""  # Facebook App Secret
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = ""  # Platform webhook verification token
    WHATSAPP_OTP_TEMPLATE_NAME: str = "otp_verification"  # Approved template name
    
    # WhatsApp Embedded Signup Settings
    WHATSAPP_TOKEN_ENCRYPTION_KEY: str = ""  # Fernet key for encrypting jeweller tokens
    FACEBOOK_CONFIG_ID: str = ""  # Facebook Embedded Signup Configuration ID
    WHATSAPP_CALLBACK_BASE_URL: str = ""  # Base URL for OAuth callbacks (e.g., https://yourdomain.com)
    
    # Environment
    ENVIRONMENT: str = "development"
    
    #Admin access code
    ADMIN_ACCESS_CODE: str = ""

    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
