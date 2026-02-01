"""
WhatsApp Cloud API Service for Campaign Messages
Handles sending template-based messages with variable replacement
"""
import httpx
import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.template import Template, TemplateTranslation
from app.models.contact import Contact
from app.utils.enums import Language

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp messages via Cloud API"""
    
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        
    async def send_template_message(
        self,
        phone_number: str,
        template_name: str,
        language_code: str,
        variables: Dict[str, str],
        db: Session
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message with personalized variables
        
        Args:
            phone_number: E.164 format phone number
            template_name: WhatsApp template name (approved)
            language_code: Template language (en, hi, mr, gu, ta)
            variables: Dict of variables to replace in template
            db: Database session
            
        Returns:
            dict: Response with success status and message ID
        """
        
        # Development mode: Return mock success
        if not self.phone_number_id or not self.access_token:
            logger.warning(f"WhatsApp not configured. Mock sending to {phone_number}")
            return {
                "success": True,
                "message_id": f"dev_{phone_number}_{template_name}",
                "phone_number": phone_number,
                "development_mode": True
            }
        
        # Build API request
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Build template parameters from variables
        parameters = [
            {"type": "text", "text": str(value)}
            for value in variables.values()
        ]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ] if parameters else []
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                message_id = result.get("messages", [{}])[0].get("id")
                
                logger.info(f"✅ WhatsApp message sent: {message_id} to {phone_number}")
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "phone_number": phone_number
                }
                
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response else {}
            error_msg = error_data.get("error", {}).get("message", str(e))
            
            logger.error(f"❌ WhatsApp API error ({e.response.status_code}): {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": error_data.get("error", {}).get("code"),
                "phone_number": phone_number
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send WhatsApp message: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone_number": phone_number
            }
    
    
    def extract_template_variables(self, template_body: str) -> List[str]:
        """
        Extract variable names from template body
        Example: "Hi {{1}}, your loan of {{2}} is due" -> ["1", "2"]
        
        Args:
            template_body: Template text with {{1}}, {{2}} placeholders
            
        Returns:
            List of variable positions
        """
        pattern = r'\{\{(\d+)\}\}'
        matches = re.findall(pattern, template_body)
        return matches
    
    
    def build_variables_from_contact(
        self,
        contact: Contact,
        template: Template,
        language: Language,
        db: Session
    ) -> Dict[str, str]:
        """
        Build variables dict by mapping template placeholders to contact data
        
        Args:
            contact: Contact object with customer data
            template: Template object
            language: Desired language
            db: Database session
            
        Returns:
            Dict mapping variable positions to values
        """
        # Get template translation
        translation = db.query(TemplateTranslation).filter(
            TemplateTranslation.template_id == template.id,
            TemplateTranslation.language == language
        ).first()
        
        if not translation:
            logger.warning(f"No translation found for template {template.id} in {language}")
            return {}
        
        # Extract required variables from template
        variable_positions = self.extract_template_variables(translation.body)
        
        # Map variables to contact data
        # This mapping should be configured per template in production
        # For now, using a simple mapping strategy
        variables = {}
        
        # Common variable mappings
        contact_data = {
            "name": contact.name or "Customer",
            "phone": contact.phone_number,
            "email": contact.email or "",
            "segment": contact.segment.value if contact.segment else "",
        }
        
        # If template has variables defined in JSON, use them
        if template.variables:
            for pos in variable_positions:
                var_key = template.variables.get(f"var{pos}", "name")
                variables[pos] = contact_data.get(var_key, "")
        else:
            # Default: first variable is name
            if "1" in variable_positions:
                variables["1"] = contact.name or "Customer"
        
        return variables
    
    
    async def send_campaign_message(
        self,
        contact: Contact,
        template: Template,
        language: Language,
        custom_variables: Optional[Dict[str, str]],
        db: Session
    ) -> Dict[str, Any]:
        """
        Send a campaign message to a contact
        
        Args:
            contact: Contact to send message to
            template: Template to use
            language: Message language
            custom_variables: Optional custom variables (overrides auto-mapping)
            db: Database session
            
        Returns:
            Result dict with success status
        """
        # Build variables
        if custom_variables:
            variables = custom_variables
        else:
            variables = self.build_variables_from_contact(contact, template, language, db)
        
        # Send message
        result = await self.send_template_message(
            phone_number=contact.phone_number,
            template_name=template.whatsapp_template_name,
            language_code=language.value,
            variables=variables,
            db=db
        )
        
        return result


# Singleton instance
whatsapp_service = WhatsAppService()
