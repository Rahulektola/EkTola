"""
Token encryption utilities for secure storage of WhatsApp access tokens.
Uses Fernet (symmetric encryption) from cryptography library.
"""
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TokenEncryptionError(Exception):
    """Raised when token encryption/decryption fails"""
    pass


def get_fernet_key() -> bytes:
    """
    Get Fernet encryption key from settings.
    Returns the key as bytes.
    """
    key = settings.WHATSAPP_TOKEN_ENCRYPTION_KEY
    if not key:
        raise TokenEncryptionError(
            "WHATSAPP_TOKEN_ENCRYPTION_KEY not configured. "
            "Generate one using: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    
    # Convert string key to bytes if needed
    if isinstance(key, str):
        key = key.encode()
    
    return key


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a plaintext token for secure database storage.
    
    Args:
        plaintext: The plaintext access token
        
    Returns:
        Encrypted token as string (base64 encoded)
        
    Raises:
        TokenEncryptionError: If encryption fails
    """
    if not plaintext:
        return ""
    
    try:
        fernet = Fernet(get_fernet_key())
        encrypted_bytes = fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Token encryption failed: {str(e)}")
        raise TokenEncryptionError(f"Failed to encrypt token: {str(e)}")


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypt an encrypted token for API usage.
    
    Args:
        ciphertext: The encrypted token (base64 encoded string)
        
    Returns:
        Decrypted plaintext token
        
    Raises:
        TokenEncryptionError: If decryption fails
    """
    if not ciphertext:
        return ""
    
    try:
        fernet = Fernet(get_fernet_key())
        decrypted_bytes = fernet.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        logger.error("Invalid token or wrong encryption key")
        raise TokenEncryptionError("Invalid token or wrong encryption key")
    except Exception as e:
        logger.error(f"Token decryption failed: {str(e)}")
        raise TokenEncryptionError(f"Failed to decrypt token: {str(e)}")


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    Use this to create WHATSAPP_TOKEN_ENCRYPTION_KEY value.
    
    Returns:
        Base64 encoded encryption key as string
    """
    return Fernet.generate_key().decode()


def is_encryption_configured() -> bool:
    """
    Check if token encryption is properly configured.
    
    Returns:
        True if encryption key is set, False otherwise
    """
    try:
        key = settings.WHATSAPP_TOKEN_ENCRYPTION_KEY
        if not key:
            return False
        
        # Validate key format by trying to create Fernet instance
        Fernet(key.encode() if isinstance(key, str) else key)
        return True
    except Exception:
        return False
