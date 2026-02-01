import httpx
from app.config import settings
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class WhatsAppService:
    """WhatsApp Business API service"""
    
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
    
    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send plain text message (used for OTPs)
        
        Args:
            to: Phone number in international format (e.g., +919876543210)
            message: Text message content
            
        Returns:
            WhatsApp API response
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Text message sent to {to}")
                return result
        except httpx.HTTPError as e:
            logger.error(f"WhatsApp API error sending text message: {str(e)}")
            raise
    
    async def send_template_message(
        self, 
        to: str, 
        template_name: str, 
        language_code: str, 
        parameters: List[str]
    ) -> Dict[str, Any]:
        """
        Send template message (used for campaigns)
        
        Args:
            to: Phone number in international format
            template_name: Approved template name
            language_code: Language code (e.g., 'en', 'hi')
            parameters: List of parameter values for template variables
            
        Returns:
            WhatsApp API response
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        # Build template components
        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": param} for param in parameters]
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Template message sent to {to}")
                return result
        except httpx.HTTPError as e:
            logger.error(f"WhatsApp API error sending template message: {str(e)}")
            raise
    
    async def send_media_message(
        self, 
        to: str, 
        media_type: str,
        media_id: Optional[str] = None,
        media_link: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send media message (image, video, document, audio)
        
        Args:
            to: Phone number in international format
            media_type: 'image', 'video', 'document', or 'audio'
            media_id: WhatsApp media ID (if already uploaded)
            media_link: Public URL to media file
            caption: Optional caption for the media
            
        Returns:
            WhatsApp API response
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        media_object = {}
        if media_id:
            media_object["id"] = media_id
        elif media_link:
            media_object["link"] = media_link
        else:
            raise ValueError("Either media_id or media_link must be provided")
        
        if caption:
            media_object["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_object
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Media message sent to {to}")
                return result
        except httpx.HTTPError as e:
            logger.error(f"WhatsApp API error sending media message: {str(e)}")
            raise
