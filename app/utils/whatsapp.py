"""
WhatsApp Integration via PyWa Library
Handles OTP sending via WhatsApp Business API using PyWa library
"""
import re
import logging
from typing import Optional, List, Dict, Any

from app.config import settings
from app.services.whatsapp_service import (
    whatsapp_service,
    send_whatsapp_otp as _send_whatsapp_otp,
    send_template_message as _send_template_message,
    MessageResult,
    TemplateResult,
)

logger = logging.getLogger(__name__)


async def send_whatsapp_otp(phone_number: str, otp_code: str) -> dict:
    """
    Send OTP via WhatsApp using PyWa library
    
    Args:
        phone_number: E.164 format phone number (e.g., +919876543210)
        otp_code: 6-digit OTP code
        
    Returns:
        dict: API response with message ID or error
    """
    # Normalize phone number
    normalized_phone = normalize_phone_number(phone_number)
    
    # Use the service function
    return await _send_whatsapp_otp(normalized_phone, otp_code)


async def send_template_message(
    phone_number: str,
    template_name: str,
    language_code: str = "en",
    params: Optional[List[str]] = None,
    header_params: Optional[List[str]] = None,
) -> dict:
    """
    Send a template message via WhatsApp
    
    Args:
        phone_number: E.164 format phone number
        template_name: Approved WhatsApp template name
        language_code: Language code (en, hi, kn, etc.)
        params: List of parameters for body placeholders
        header_params: List of parameters for header placeholders
        
    Returns:
        dict: API response with message ID or error
    """
    normalized_phone = normalize_phone_number(phone_number)
    
    result = await whatsapp_service.send_template_message(
        phone_number=normalized_phone,
        template_name=template_name,
        language_code=language_code,
        body_params=params,
        header_params=header_params,
    )
    
    if result.success:
        return {
            "success": True,
            "message_id": result.message_id,
            "phone_number": result.phone_number,
        }
    else:
        return {
            "success": False,
            "error": result.error,
            "error_code": result.error_code,
        }


async def send_text_message(
    phone_number: str,
    text: str,
    preview_url: bool = False,
) -> dict:
    """
    Send a plain text message via WhatsApp (within 24-hour window only)
    
    Args:
        phone_number: E.164 format phone number
        text: Message text content
        preview_url: Whether to show URL preview
        
    Returns:
        dict: API response with message ID or error
    """
    normalized_phone = normalize_phone_number(phone_number)
    
    result = await whatsapp_service.send_text_message(
        phone_number=normalized_phone,
        text=text,
        preview_url=preview_url,
    )
    
    if result.success:
        return {
            "success": True,
            "message_id": result.message_id,
            "phone_number": result.phone_number,
        }
    else:
        return {
            "success": False,
            "error": result.error,
            "error_code": result.error_code,
        }


async def send_image_message(
    phone_number: str,
    image_url: Optional[str] = None,
    image_id: Optional[str] = None,
    caption: Optional[str] = None,
) -> dict:
    """
    Send an image message via WhatsApp
    
    Args:
        phone_number: E.164 format phone number
        image_url: URL of the image
        image_id: WhatsApp Media ID of the image
        caption: Optional caption for the image
        
    Returns:
        dict: API response with message ID or error
    """
    normalized_phone = normalize_phone_number(phone_number)
    
    result = await whatsapp_service.send_image_message(
        phone_number=normalized_phone,
        image_url=image_url,
        image_id=image_id,
        caption=caption,
    )
    
    if result.success:
        return {
            "success": True,
            "message_id": result.message_id,
            "phone_number": result.phone_number,
        }
    else:
        return {
            "success": False,
            "error": result.error,
            "error_code": result.error_code,
        }


async def send_document_message(
    phone_number: str,
    document_url: Optional[str] = None,
    document_id: Optional[str] = None,
    filename: Optional[str] = None,
    caption: Optional[str] = None,
) -> dict:
    """
    Send a document message via WhatsApp
    
    Args:
        phone_number: E.164 format phone number
        document_url: URL of the document
        document_id: WhatsApp Media ID of the document
        filename: Display filename for the document
        caption: Optional caption for the document
        
    Returns:
        dict: API response with message ID or error
    """
    normalized_phone = normalize_phone_number(phone_number)
    
    result = await whatsapp_service.send_document_message(
        phone_number=normalized_phone,
        document_url=document_url,
        document_id=document_id,
        filename=filename,
        caption=caption,
    )
    
    if result.success:
        return {
            "success": True,
            "message_id": result.message_id,
            "phone_number": result.phone_number,
        }
    else:
        return {
            "success": False,
            "error": result.error,
            "error_code": result.error_code,
        }


async def send_bulk_messages(
    recipients: List[Dict[str, Any]],
    template_name: str,
    language_code: str = "en",
) -> dict:
    """
    Send template messages to multiple recipients
    
    Args:
        recipients: List of dicts with 'phone_number' and optional 'params'
        template_name: Approved WhatsApp template name
        language_code: Language code
        
    Returns:
        dict: Summary of send results
    """
    # Normalize all phone numbers
    for recipient in recipients:
        recipient["phone_number"] = normalize_phone_number(recipient["phone_number"])
    
    results = await whatsapp_service.send_bulk_template_messages(
        recipients=recipients,
        template_name=template_name,
        language_code=language_code,
    )
    
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count
    
    return {
        "total": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": [
            {
                "phone_number": r.phone_number,
                "success": r.success,
                "message_id": r.message_id,
                "error": r.error,
            }
            for r in results
        ]
    }


# ==================== TEMPLATE MANAGEMENT ====================

async def get_whatsapp_templates(
    limit: int = 100,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all message templates from WhatsApp Business Account
    
    Args:
        limit: Maximum number of templates to retrieve
        status_filter: Filter by status (APPROVED, PENDING, REJECTED)
        
    Returns:
        List of template dictionaries
    """
    return await whatsapp_service.get_templates(
        limit=limit,
        status_filter=status_filter,
    )


async def get_template_by_name(template_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific template by name
    
    Args:
        template_name: Name of the template
        
    Returns:
        Template dictionary or None if not found
    """
    return await whatsapp_service.get_template_by_name(template_name)


async def create_whatsapp_template(
    name: str,
    category: str,
    language: str,
    body_text: str,
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    buttons: Optional[List[Dict[str, str]]] = None,
) -> dict:
    """
    Create a new message template (requires approval)
    
    Args:
        name: Template name (lowercase, underscores only)
        category: Template category (UTILITY, MARKETING, AUTHENTICATION)
        language: Language code (en, hi, etc.)
        body_text: Body text with {{1}}, {{2}} placeholders
        header_text: Optional header text
        footer_text: Optional footer text
        buttons: Optional list of button configurations
        
    Returns:
        dict with success status and template ID
    """
    result = await whatsapp_service.create_template(
        name=name,
        category=category,
        language=language,
        body_text=body_text,
        header_text=header_text,
        footer_text=footer_text,
        buttons=buttons,
    )
    
    if result.success:
        return {
            "success": True,
            "template_id": result.template_id,
            "template_name": result.template_name,
            "status": result.status,
        }
    else:
        return {
            "success": False,
            "template_name": result.template_name,
            "error": result.error,
        }


async def delete_whatsapp_template(template_name: str) -> dict:
    """
    Delete a message template
    
    Args:
        template_name: Name of the template to delete
        
    Returns:
        dict with success status
    """
    result = await whatsapp_service.delete_template(template_name)
    
    if result.success:
        return {
            "success": True,
            "template_name": result.template_name,
        }
    else:
        return {
            "success": False,
            "template_name": result.template_name,
            "error": result.error,
        }


# ==================== PHONE NUMBER UTILITIES ====================

def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize phone number to E.164 format
    Accepts: +919876543210, +91 9876543210, 9876543210
    
    Args:
        phone_number: Phone number in various formats
        
    Returns:
        str: Phone number in E.164 format (+919876543210)
    """
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
    # Normalize first
    normalized = normalize_phone_number(phone_number)
    # E.164 format: +[country code][number] (max 15 digits)
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, normalized))


def is_whatsapp_configured() -> bool:
    """
    Check if WhatsApp API is properly configured
    
    Returns:
        bool: True if WhatsApp client is configured
    """
    return whatsapp_service.is_configured

