"""
WhatsApp Cloud API Integration
Handles OTP sending via WhatsApp Business API
"""
import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_whatsapp_otp(phone_number: str, otp_code: str) -> dict:
    """
    Send OTP via WhatsApp using Cloud API
    
    Args:
        phone_number: E.164 format phone number (e.g., +919876543210)
        otp_code: 6-digit OTP code
        
    Returns:
        dict: API response with message ID or error
    """
    
    # For development: Return mock success if WhatsApp not configured
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.warning("WhatsApp API not configured. OTP sending skipped in development.")
        return {
            "success": True,
            "message_id": "dev_mode_" + otp_code,
            "otp": otp_code  # Return OTP for dev testing
        }
    
    # WhatsApp Cloud API endpoint
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    # Request headers
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Message payload using template
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": settings.WHATSAPP_OTP_TEMPLATE_NAME,
            "language": {
                "code": "en"  # Template language
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": otp_code
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"WhatsApp OTP sent successfully to {phone_number}")
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "phone_number": phone_number
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"WhatsApp API error: {e.response.status_code} - {e.response.text}")
        return {
            "success": False,
            "error": f"WhatsApp API error: {e.response.status_code}",
            "details": e.response.text
        }
        
    except Exception as e:
        logger.error(f"Failed to send WhatsApp OTP: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize phone number to E.164 format
    Accepts: +919876543210, +91 9876543210, 9876543210
    
    Args:
        phone_number: Phone number in various formats
        
    Returns:
        str: Phone number in E.164 format (+919876543210)
    """
    import re
    # Remove all spaces, dashes, and parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    # If it starts with +91, keep as is
    if cleaned.startswith('+91'):
        return cleaned
    
    # If it starts with 91 (without +), add +
    if cleaned.startswith('91') and len(cleaned) == 12:
        return '+' + cleaned
    
    # If it's 10 digits starting with 6-9, assume Indian number
    if re.match(r'^[6-9]\d{9}$', cleaned):
        return '+91' + cleaned
    
    # Return as is if already in other format
    return cleaned


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate phone number is in E.164 format
    
    Args:
        phone_number: Phone number to validate
        
    Returns:
        bool: True if valid E.164 format
    """
    import re
    # Normalize first
    normalized = normalize_phone_number(phone_number)
    # E.164 format: +[country code][number] (max 15 digits)
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, normalized))
