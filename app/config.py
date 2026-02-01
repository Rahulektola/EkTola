from pydantic_settings import BaseSettings
from typing import Optional
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # Database - individual components
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    
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
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct DATABASE_URL from individual components with URL encoding"""
        # URL-encode password to handle special characters like @, #, etc.
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
