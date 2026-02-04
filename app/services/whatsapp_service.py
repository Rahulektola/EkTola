"""
WhatsApp Service using PyWa Library
Handles messaging, template management, and webhook processing
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from pywa import WhatsApp
    from pywa.types import Template as PyWaTemplate
    from pywa.errors import WhatsAppError
    PYWA_AVAILABLE = True
except ImportError:
    PYWA_AVAILABLE = False
    WhatsApp = None
    PyWaTemplate = None
    WhatsAppError = Exception

from app.config import settings
from app.utils.enums import Language, MessageStatus

logger = logging.getLogger(__name__)


class WhatsAppServiceError(Exception):
    """Custom exception for WhatsApp service errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


@dataclass
class MessageResult:
    """Result of a message send operation"""
    success: bool
    message_id: Optional[str] = None
    phone_number: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class TemplateResult:
    """Result of a template operation"""
    success: bool
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class WhatsAppService:
    """
    WhatsApp Cloud API Service using PyWa library
    Provides messaging, template management, and status tracking
    """
    
    _instance: Optional['WhatsAppService'] = None
    _client = None  # WhatsApp client instance
    
    def __new__(cls):
        """Singleton pattern for WhatsApp client"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize WhatsApp client if not already done"""
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the PyWa WhatsApp client"""
        if not PYWA_AVAILABLE:
            logger.warning("PyWa library not available. Running in development mode.")
            self._client = None
            return
            
        if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
            logger.warning("WhatsApp API credentials not configured. Running in development mode.")
            self._client = None
            return
        
        try:
            self._client = WhatsApp(
                phone_id=settings.WHATSAPP_PHONE_NUMBER_ID,
                token=settings.WHATSAPP_ACCESS_TOKEN,
                business_account_id=settings.WHATSAPP_BUSINESS_ACCOUNT_ID or None,
                api_version=settings.WHATSAPP_API_VERSION,
            )
            logger.info("WhatsApp client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp client: {e}")
            self._client = None
    
    @property
    def is_configured(self) -> bool:
        """Check if WhatsApp client is properly configured"""
        return self._client is not None and PYWA_AVAILABLE
    
    # ==================== MESSAGING METHODS ====================
    
    async def send_template_message(
        self,
        phone_number: str,
        template_name: str,
        language_code: str = "en",
        body_params: Optional[List[str]] = None,
        header_params: Optional[List[str]] = None,
        button_params: Optional[List[Dict[str, str]]] = None,
    ) -> MessageResult:
        """
        Send a template message to a phone number
        
        Args:
            phone_number: E.164 format phone number
            template_name: Approved WhatsApp template name
            language_code: Language code (en, hi, kn, etc.)
            body_params: List of parameters for body placeholders
            header_params: List of parameters for header placeholders
            button_params: List of button parameters for buttons
            
        Returns:
            MessageResult with success status and message ID
        """
        # Development mode fallback
        if not self.is_configured:
            logger.warning(f"[DEV MODE] Template message to {phone_number}: {template_name}")
            return MessageResult(
                success=True,
                message_id=f"dev_mode_{template_name}_{phone_number[-4:]}",
                phone_number=phone_number,
            )
        
        try:
            # Build template for pywa
            # Create body values
            body_values = []
            if body_params:
                for param in body_params:
                    body_values.append(PyWaTemplate.TextValue(value=param))
            
            # Create header values
            header_values = None
            if header_params:
                header_values = []
                for param in header_params:
                    header_values.append(PyWaTemplate.TextValue(value=param))
            
            # Create template object
            template = PyWaTemplate(
                name=template_name,
                language=PyWaTemplate.Language(code=language_code),
                body=body_values if body_values else None,
                header=header_values,
            )
            
            # Send the template message
            response = self._client.send_template(
                to=phone_number,
                template=template,
            )
            
            logger.info(f"Template message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=response.id if hasattr(response, 'id') else str(response),
                phone_number=phone_number,
            )
            
        except WhatsAppError as e:
            logger.error(f"WhatsApp API error sending template: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
                error_code=getattr(e, 'error_code', None),
            )
        except Exception as e:
            logger.error(f"Error sending template message: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
            )
    
    async def send_text_message(
        self,
        phone_number: str,
        text: str,
        preview_url: bool = False,
    ) -> MessageResult:
        """
        Send a plain text message (only within 24-hour window)
        
        Args:
            phone_number: E.164 format phone number
            text: Message text content
            preview_url: Whether to show URL preview
            
        Returns:
            MessageResult with success status and message ID
        """
        if not self.is_configured:
            logger.warning(f"[DEV MODE] Text message to {phone_number}: {text[:50]}...")
            return MessageResult(
                success=True,
                message_id=f"dev_mode_text_{phone_number[-4:]}",
                phone_number=phone_number,
            )
        
        try:
            response = self._client.send_message(
                to=phone_number,
                text=text,
                preview_url=preview_url,
            )
            
            logger.info(f"Text message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=response.id if hasattr(response, 'id') else str(response),
                phone_number=phone_number,
            )
            
        except WhatsAppError as e:
            logger.error(f"WhatsApp API error sending text: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
                error_code=getattr(e, 'error_code', None),
            )
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
            )
    
    async def send_image_message(
        self,
        phone_number: str,
        image_url: Optional[str] = None,
        image_id: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> MessageResult:
        """
        Send an image message
        
        Args:
            phone_number: E.164 format phone number
            image_url: URL of the image (use either url or id)
            image_id: WhatsApp Media ID of the image
            caption: Optional caption for the image
            
        Returns:
            MessageResult with success status and message ID
        """
        if not self.is_configured:
            logger.warning(f"[DEV MODE] Image message to {phone_number}")
            return MessageResult(
                success=True,
                message_id=f"dev_mode_image_{phone_number[-4:]}",
                phone_number=phone_number,
            )
        
        try:
            response = self._client.send_image(
                to=phone_number,
                image=image_url or image_id,
                caption=caption,
            )
            
            logger.info(f"Image message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=response.id if hasattr(response, 'id') else str(response),
                phone_number=phone_number,
            )
            
        except WhatsAppError as e:
            logger.error(f"WhatsApp API error sending image: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
                error_code=getattr(e, 'error_code', None),
            )
        except Exception as e:
            logger.error(f"Error sending image message: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
            )
    
    async def send_document_message(
        self,
        phone_number: str,
        document_url: Optional[str] = None,
        document_id: Optional[str] = None,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> MessageResult:
        """
        Send a document message
        
        Args:
            phone_number: E.164 format phone number
            document_url: URL of the document
            document_id: WhatsApp Media ID of the document
            filename: Display filename for the document
            caption: Optional caption for the document
            
        Returns:
            MessageResult with success status and message ID
        """
        if not self.is_configured:
            logger.warning(f"[DEV MODE] Document message to {phone_number}: {filename}")
            return MessageResult(
                success=True,
                message_id=f"dev_mode_doc_{phone_number[-4:]}",
                phone_number=phone_number,
            )
        
        try:
            response = self._client.send_document(
                to=phone_number,
                document=document_url or document_id,
                filename=filename,
                caption=caption,
            )
            
            logger.info(f"Document message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=response.id if hasattr(response, 'id') else str(response),
                phone_number=phone_number,
            )
            
        except WhatsAppError as e:
            logger.error(f"WhatsApp API error sending document: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
                error_code=getattr(e, 'error_code', None),
            )
        except Exception as e:
            logger.error(f"Error sending document message: {e}")
            return MessageResult(
                success=False,
                phone_number=phone_number,
                error=str(e),
            )
    
    async def send_otp_message(
        self,
        phone_number: str,
        otp_code: str,
    ) -> MessageResult:
        """
        Send OTP verification message using approved template
        
        Args:
            phone_number: E.164 format phone number
            otp_code: 6-digit OTP code
            
        Returns:
            MessageResult with success status and message ID
        """
        return await self.send_template_message(
            phone_number=phone_number,
            template_name=settings.WHATSAPP_OTP_TEMPLATE_NAME,
            language_code="en",
            body_params=[otp_code],
        )
    
    async def send_bulk_template_messages(
        self,
        recipients: List[Dict[str, Any]],
        template_name: str,
        language_code: str = "en",
    ) -> List[MessageResult]:
        """
        Send template messages to multiple recipients
        
        Args:
            recipients: List of dicts with 'phone_number' and optional 'params'
            template_name: Approved WhatsApp template name
            language_code: Language code
            
        Returns:
            List of MessageResult objects
        """
        results = []
        
        for recipient in recipients:
            phone = recipient.get("phone_number")
            params = recipient.get("params", [])
            
            result = await self.send_template_message(
                phone_number=phone,
                template_name=template_name,
                language_code=language_code,
                body_params=params,
            )
            results.append(result)
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Bulk send completed: {success_count}/{len(results)} successful")
        
        return results
    
    # ==================== TEMPLATE MANAGEMENT ====================
    
    async def get_templates(
        self,
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
        if not self.is_configured:
            logger.warning("[DEV MODE] Returning empty template list")
            return []
        
        if not settings.WHATSAPP_BUSINESS_ACCOUNT_ID:
            logger.error("Business Account ID not configured for template management")
            return []
        
        try:
            import httpx
            
            # API endpoint for fetching templates
            url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
            
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            }
            
            params = {
                "limit": limit,
            }
            
            if status_filter:
                params["status"] = status_filter
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                result = response.json()
            
            template_list = []
            for template in result.get("data", []):
                template_dict = {
                    "id": template.get("id"),
                    "name": template.get("name"),
                    "status": template.get("status"),
                    "category": template.get("category"),
                    "language": template.get("language"),
                    "components": template.get("components", []),
                }
                template_list.append(template_dict)
            
            logger.info(f"Retrieved {len(template_list)} templates")
            return template_list
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e, 'response') else str(e)
            logger.error(f"WhatsApp API error fetching templates: {error_detail}")
            return []
        except Exception as e:
            logger.error(f"Error fetching templates: {e}")
            return []
    
    async def get_template_by_name(
        self,
        template_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by name
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template dictionary or None if not found
        """
        templates = await self.get_templates()
        
        for template in templates:
            if template.get("name") == template_name:
                return template
        
        return None
    
    async def create_template(
        self,
        name: str,
        category: str,
        language: str,
        body_text: str,
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
    ) -> TemplateResult:
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
            TemplateResult with success status and template ID
        """
        if not self.is_configured:
            logger.warning(f"[DEV MODE] Template creation: {name}")
            return TemplateResult(
                success=True,
                template_id=f"dev_template_{name}",
                template_name=name,
                status="PENDING",
            )
        
        if not settings.WHATSAPP_BUSINESS_ACCOUNT_ID:
            logger.error("Business Account ID not configured for template creation")
            return TemplateResult(
                success=False,
                error="Business Account ID not configured",
            )
        
        try:
            import httpx
            
            # Build components list for WhatsApp API
            components = []
            
            # Add header component if provided
            if header_text:
                components.append({
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": header_text,
                })
            
            # Add body component (required)
            components.append({
                "type": "BODY",
                "text": body_text,
            })
            
            # Add footer component if provided
            if footer_text:
                components.append({
                    "type": "FOOTER",
                    "text": footer_text,
                })
            
            # Add buttons if provided
            if buttons:
                button_list = []
                for btn in buttons:
                    button_list.append({
                        "type": btn.get("type", "QUICK_REPLY"),
                        "text": btn.get("text", ""),
                    })
                components.append({
                    "type": "BUTTONS",
                    "buttons": button_list,
                })
            
            # API endpoint for template creation
            url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
            
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "name": name,
                "category": category.upper(),
                "language": language,
                "components": components,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"Template created successfully: {name}")
            return TemplateResult(
                success=True,
                template_id=result.get("id"),
                template_name=name,
                status="PENDING",
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e, 'response') else str(e)
            logger.error(f"WhatsApp API error creating template: {error_detail}")
            return TemplateResult(
                success=False,
                template_name=name,
                error=f"API Error: {error_detail}",
            )
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return TemplateResult(
                success=False,
                template_name=name,
                error=str(e),
            )
    
    async def delete_template(
        self,
        template_name: str,
    ) -> TemplateResult:
        """
        Delete a message template
        
        Args:
            template_name: Name of the template to delete
            
        Returns:
            TemplateResult with success status
        """
        if not self.is_configured:
            logger.warning(f"[DEV MODE] Template deletion: {template_name}")
            return TemplateResult(
                success=True,
                template_name=template_name,
            )
        
        if not settings.WHATSAPP_BUSINESS_ACCOUNT_ID:
            logger.error("Business Account ID not configured for template deletion")
            return TemplateResult(
                success=False,
                error="Business Account ID not configured",
            )
        
        try:
            import httpx
            
            # API endpoint for template deletion
            url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
            
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            }
            
            params = {
                "name": template_name,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers, params=params)
                response.raise_for_status()
            
            logger.info(f"Template deleted successfully: {template_name}")
            return TemplateResult(
                success=True,
                template_name=template_name,
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e, 'response') else str(e)
            logger.error(f"WhatsApp API error deleting template: {error_detail}")
            return TemplateResult(
                success=False,
                template_name=template_name,
                error=f"API Error: {error_detail}",
            )
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return TemplateResult(
                success=False,
                template_name=template_name,
                error=str(e),
            )
    
    # ==================== STATUS & UTILITY METHODS ====================
    
    def map_status_to_internal(self, wa_status: str) -> MessageStatus:
        """
        Map WhatsApp status to internal MessageStatus enum
        
        Args:
            wa_status: WhatsApp status string
            
        Returns:
            Internal MessageStatus enum value
        """
        status_mapping = {
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "read": MessageStatus.READ,
            "failed": MessageStatus.FAILED,
        }
        return status_mapping.get(wa_status.lower(), MessageStatus.QUEUED)
    
    async def mark_message_as_read(
        self,
        message_id: str,
    ) -> bool:
        """
        Mark a message as read
        
        Args:
            message_id: WhatsApp message ID
            
        Returns:
            True if successful
        """
        if not self.is_configured:
            return True
        
        try:
            self._client.mark_message_as_read(message_id=message_id)
            return True
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False


# Singleton instance
whatsapp_service = WhatsAppService()


# ==================== CONVENIENCE FUNCTIONS ====================

async def send_whatsapp_otp(phone_number: str, otp_code: str) -> dict:
    """
    Backward-compatible function for sending OTP
    
    Args:
        phone_number: E.164 format phone number
        otp_code: 6-digit OTP code
        
    Returns:
        dict with success status and message ID
    """
    result = await whatsapp_service.send_otp_message(phone_number, otp_code)
    
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


async def send_template_message(
    phone_number: str,
    template_name: str,
    language_code: str = "en",
    params: Optional[List[str]] = None,
) -> dict:
    """
    Send a template message (convenience function)
    
    Args:
        phone_number: E.164 format phone number
        template_name: Approved template name
        language_code: Language code
        params: List of template parameters
        
    Returns:
        dict with success status and message ID
    """
    result = await whatsapp_service.send_template_message(
        phone_number=phone_number,
        template_name=template_name,
        language_code=language_code,
        body_params=params,
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
