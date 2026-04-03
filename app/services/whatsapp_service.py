"""
WhatsApp Service using PyWa Library (v3.8.0+)
Handles messaging, template management, and webhook processing
Uses pywa for async support with FastAPI
Now supports multi-tenant: per-jeweller WhatsApp clients + platform client
"""
import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

try:
    from pywa import WhatsApp
    PYWA_AVAILABLE = True
    WhatsAppError = Exception  # Generic exception for error handling
except ImportError:
    PYWA_AVAILABLE = False
    WhatsApp = None
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


def get_template_language(language_code: str) -> str:
    """
    Convert language code to WhatsApp language string
    
    Args:
        language_code: ISO language code (en, hi, kn, etc.)
        
    Returns:
        Language string (e.g., 'en', 'en_US', 'hi')
    """
    # Map to WhatsApp language codes
    language_map = {
        "en": "en",
        "en_US": "en_US",
        "en_GB": "en_GB",
        "hi": "hi",
        "kn": "kn",
        "ta": "ta",
        "te": "te",
        "mr": "mr",
        "gu": "gu",
        "bn": "bn",
        "ml": "ml",
        "pa": "pa",
        "or": "or",
        "as": "as",
        "ur": "ur",
    }
    return language_map.get(language_code, "en")


# ==================== MULTI-TENANT CLIENT MANAGEMENT ====================

def get_jeweller_whatsapp_client(jeweller_id: int, db: Session) -> Optional[Any]:
    """
    Get WhatsApp client for a specific jeweller.
    Uses jeweller's own WABA credentials.
    
    Args:
        jeweller_id: ID of the jeweller
        db: Database session
        
    Returns:
        WhatsApp client instance or None if not configured
        
    Raises:
        WhatsAppServiceError: If jeweller not found or credentials invalid
    """
    from app.models.jeweller import Jeweller
    from app.core.encryption import decrypt_token, TokenEncryptionError
    
    if not PYWA_AVAILABLE:
        logger.warning(f"PyWa library not available for jeweller {jeweller_id}")
        return None
    
    # Get jeweller
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    if not jeweller:
        raise WhatsAppServiceError(f"Jeweller {jeweller_id} not found")
    
    # Check if WhatsApp is connected
    if not jeweller.waba_id or not jeweller.phone_number_id or not jeweller.access_token:
        raise WhatsAppServiceError(
            f"WhatsApp not connected for jeweller {jeweller_id}",
            error_code="WHATSAPP_NOT_CONNECTED"
        )
    
    # Check token expiry
    if jeweller.access_token_expires_at:
        if jeweller.access_token_expires_at < datetime.utcnow():
            raise WhatsAppServiceError(
                f"WhatsApp access token expired for jeweller {jeweller_id}",
                error_code="TOKEN_EXPIRED"
            )
        
        # Warn if token expires soon (within 7 days)
        days_until_expiry = (jeweller.access_token_expires_at - datetime.utcnow()).days
        if days_until_expiry < 7:
            logger.warning(f"WhatsApp token for jeweller {jeweller_id} expires in {days_until_expiry} days")
    
    # Decrypt access token
    try:
        decrypted_token = decrypt_token(jeweller.access_token)
    except TokenEncryptionError as e:
        logger.error(f"Failed to decrypt token for jeweller {jeweller_id}: {str(e)}")
        raise WhatsAppServiceError(
            f"Failed to decrypt WhatsApp token for jeweller {jeweller_id}",
            error_code="DECRYPTION_FAILED"
        )
    
    # Create and return WhatsApp client
    try:
        client = WhatsApp(
            phone_id=jeweller.phone_number_id,
            token=decrypted_token,
            business_account_id=jeweller.waba_id
        )
        logger.info(f"WhatsApp client created for jeweller {jeweller_id}")
        return client
    except Exception as e:
        logger.error(f"Failed to create WhatsApp client for jeweller {jeweller_id}: {str(e)}")
        raise WhatsAppServiceError(
            f"Failed to create WhatsApp client: {str(e)}",
            error_code="CLIENT_CREATION_FAILED"
        )


def get_platform_whatsapp_client() -> Optional[Any]:
    """
    Get the platform WhatsApp client for OTPs and admin notifications.
    Uses global platform credentials from settings.
    
    Returns:
        WhatsApp client instance or None if not configured
    """
    if not PYWA_AVAILABLE:
        logger.warning("PyWa library not available for platform client")
        return None
    
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.warning("Platform WhatsApp credentials not configured")
        return None
    
    try:
        client = WhatsApp(
            phone_id=settings.WHATSAPP_PHONE_NUMBER_ID,
            token=settings.WHATSAPP_ACCESS_TOKEN,
            business_account_id=settings.WHATSAPP_BUSINESS_ACCOUNT_ID or None
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create platform WhatsApp client: {str(e)}")
        return None


async def send_admin_notification(jeweller_id: int, event: str, db: Session) -> bool:
    """
    Send WhatsApp notification to all admins about jeweller events.
    Uses platform WhatsApp account.
    
    Args:
        jeweller_id: ID of the jeweller triggering the event
        event: Event type (e.g., "whatsapp_connected", "registration_pending")
        db: Database session
        
    Returns:
        True if at least one notification was sent successfully
    """
    from app.models.user import User
    from app.models.jeweller import Jeweller
    from app.services.whatsapp_service import WhatsAppService
    
    try:
        # Get jeweller info
        jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
        if not jeweller:
            logger.error(f"Jeweller {jeweller_id} not found for admin notification")
            return False
        
        # Get all admin users
        admins = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
        if not admins:
            logger.warning("No active admins found to notify")
            return False
        
        # Build notification message
        if event == "whatsapp_connected":
            message = (
                f"🔗 *WhatsApp Connected*\n\n"
                f"Jeweller: {jeweller.business_name}\n"
                f"ID: {jeweller_id}\n"
                f"Phone: {jeweller.phone_display_number or 'N/A'}\n"
                f"WABA: {jeweller.waba_name or jeweller.waba_id}\n\n"
                f"The jeweller has successfully connected their WhatsApp Business Account."
            )
        elif event == "registration_pending":
            message = (
                f"📝 *New Registration*\n\n"
                f"Jeweller: {jeweller.business_name}\n"
                f"Phone: {jeweller.phone_number}\n\n"
                f"Awaiting approval."
            )
        else:
            message = f"📢 Event: {event}\nJeweller: {jeweller.business_name} (ID: {jeweller_id})"
        
        # Get platform client
        client = get_platform_whatsapp_client()
        if not client:
            logger.warning("Platform WhatsApp client not available for admin notification")
            return False
        
        # Send to all admins
        success_count = 0
        for admin in admins:
            if not admin.phone_number:
                continue
            
            try:
                await client.send_message(
                    to=admin.phone_number,
                    text=message
                )
                success_count += 1
                logger.info(f"Admin notification sent to {admin.email}")
            except Exception as e:
                logger.error(f"Failed to send admin notification to {admin.email}: {str(e)}")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")
        return False


class WhatsAppService:
    """
    WhatsApp Cloud API Service using PyWa library (v3.8.0+)
    
    This class provides the PLATFORM WhatsApp client for:
    - OTP messages (authentication)
    - Admin notifications
    - System messages
    
    For jeweller-specific messaging (campaigns), use get_jeweller_whatsapp_client()
    
    Provides messaging, template management, and status tracking
    Uses pywa for async operations
    """
    
    _instance: Optional['WhatsAppService'] = None
    _client: Optional[Any] = None
    
    def __new__(cls):
        """Singleton pattern for platform WhatsApp client"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize platform WhatsApp client if not already done"""
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the PyWa async WhatsApp client for PLATFORM use (OTPs, admin messages)"""
        if not PYWA_AVAILABLE:
            logger.warning("PyWa library not available. Running in development mode.")
            self._client = None
            return
            
        if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
            logger.warning("WhatsApp API credentials not configured. Running in development mode.")
            self._client = None
            return
        
        try:
            # pywa 3.8.0 WhatsApp client with native async support
            self._client = WhatsApp(
                phone_id=settings.WHATSAPP_PHONE_NUMBER_ID,
                token=settings.WHATSAPP_ACCESS_TOKEN,
                business_account_id=settings.WHATSAPP_BUSINESS_ACCOUNT_ID or None,
            )
            logger.info("WhatsApp async client initialized successfully (pywa 3.8.0)")
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
        Send a template message to a phone number using pywa 3.8.0 API
        
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
            # Get the language string for pywa 3.8.0
            template_language = get_template_language(language_code)
            
            # Build components for template parameters
            # PyWa 3.8.0 uses simple parameter lists
            components = []
            
            # Add header component if params provided
            if header_params:
                components.append({
                    "type": "header",
                    "parameters": [{"type": "text", "text": param} for param in header_params]
                })
            
            # Add body component if params provided
            if body_params:
                components.append({
                    "type": "body",
                    "parameters": [{"type": "text", "text": param} for param in body_params]
                })
            
            # Send the template message using pywa 3.8.0 async API
            response = await self._client.send_template(
                to=phone_number,
                template=template_name,
                language=template_language,
                components=components if components else None,
            )
            
            # In pywa 3.x, response is a SentTemplate object with .id attribute
            message_id = response.id if hasattr(response, 'id') else str(response)
            
            logger.info(f"Template message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=message_id,
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
            # pywa 3.x send_message with keyword-only args
            response = await self._client.send_message(
                to=phone_number,
                text=text,
                preview_url=preview_url,
            )
            
            # In pywa 3.x, response is a SentMessage object
            message_id = response.id if hasattr(response, 'id') else str(response)
            
            logger.info(f"Text message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=message_id,
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
            # pywa 3.x send_image with keyword-only args
            response = await self._client.send_image(
                to=phone_number,
                image=image_url or image_id,
                caption=caption,
            )
            
            message_id = response.id if hasattr(response, 'id') else str(response)
            
            logger.info(f"Image message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=message_id,
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
            # pywa 3.x send_document with keyword-only args
            response = await self._client.send_document(
                to=phone_number,
                document=document_url or document_id,
                filename=filename,
                caption=caption,
            )
            
            message_id = response.id if hasattr(response, 'id') else str(response)
            
            logger.info(f"Document message sent successfully to {phone_number}")
            return MessageResult(
                success=True,
                message_id=message_id,
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
            # Use PyWa library exclusively for template management
            if not hasattr(self._client, 'get_templates'):
                logger.error("PyWa client does not support get_templates - ensure PyWa 3.8.0+ is installed")
                return []
            
            templates_result = await self._client.get_templates()
            template_list = []
            for template in templates_result:
                template_dict = {
                    "id": template.id if hasattr(template, 'id') else None,
                    "name": template.name if hasattr(template, 'name') else None,
                    "status": template.status.value if hasattr(template, 'status') else None,
                    "category": template.category.value if hasattr(template, 'category') else None,
                    "language": template.language.value if hasattr(template, 'language') else None,
                    "components": template.components if hasattr(template, 'components') else [],
                }
                # Apply status filter if specified
                if status_filter and template_dict["status"] != status_filter:
                    continue
                template_list.append(template_dict)
                # Apply limit
                if len(template_list) >= limit:
                    break
            
            logger.info(f"Retrieved {len(template_list)} templates via PyWa")
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
            
            # Use PyWa library exclusively - create_template method
            if not hasattr(self._client, 'create_template'):
                logger.error("PyWa client does not support create_template - ensure PyWa 3.8.0+ is installed")
                return TemplateResult(
                    success=False,
                    template_name=name,
                    error="Template creation not supported by PyWa client",
                )
            
            # PyWa create_template accepts structured component data
            result = await self._client.create_template(
                name=name,
                category=category.upper(),
                language=language,
                components=components,
            )
            
            logger.info(f"Template created successfully via PyWa: {name}")
            return TemplateResult(
                success=True,
                template_id=result.get("id") if isinstance(result, dict) else getattr(result, 'id', None),
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
            # Use PyWa library exclusively for template deletion
            if not hasattr(self._client, 'delete_template'):
                logger.error("PyWa client does not support delete_template - ensure PyWa 3.8.0+ is installed")
                return TemplateResult(
                    success=False,
                    template_name=template_name,
                    error="Template deletion not supported by PyWa client",
                )
            
            await self._client.delete_template(template_name=template_name)
            logger.info(f"Template deleted successfully via PyWa: {template_name}")
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
            await self._client.mark_message_as_read(message_id=message_id)
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
