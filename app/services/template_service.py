"""
Template Management Service
Synchronizes WhatsApp templates with local database
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.template import Template, TemplateTranslation
from app.services.whatsapp_service import whatsapp_service, TemplateResult
from app.utils.enums import CampaignType, Language, SegmentType

logger = logging.getLogger(__name__)


class TemplateService:
    """
    Service for managing WhatsApp templates
    Handles synchronization between WhatsApp Cloud API and local database
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def sync_templates_from_whatsapp(self) -> Dict[str, Any]:
        """
        Fetch templates from WhatsApp and sync with local database
        
        Returns:
            Dict with sync results (created, updated, skipped counts)
        """
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # Get templates from WhatsApp
            wa_templates = await whatsapp_service.get_templates()
            
            if not wa_templates:
                logger.warning("No templates retrieved from WhatsApp")
                return {
                    "success": True,
                    "created": 0,
                    "updated": 0,
                    "skipped": 0,
                    "message": "No templates found in WhatsApp account"
                }
            
            for wa_template in wa_templates:
                template_name = wa_template.get("name")
                
                try:
                    # Check if template exists in database
                    existing = self.db.query(Template).filter(
                        Template.template_name == template_name
                    ).first()
                    
                    if existing:
                        # Update existing template translation status
                        for translation in existing.translations:
                            if translation.language.value == wa_template.get("language"):
                                translation.whatsapp_template_id = wa_template.get("id")
                                translation.approval_status = wa_template.get("status", "PENDING")
                                translation.updated_at = datetime.utcnow()
                                updated_count += 1
                    else:
                        # Template doesn't exist locally, skip (admin should create it)
                        skipped_count += 1
                        logger.info(f"Skipping template {template_name} - not found in local database")
                    
                except Exception as e:
                    logger.error(f"Error processing template {template_name}: {e}")
                    errors.append({"template": template_name, "error": str(e)})
            
            self.db.commit()
            
            return {
                "success": True,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": errors if errors else None,
            }
            
        except Exception as e:
            logger.error(f"Error syncing templates: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def create_template_in_whatsapp(
        self,
        template_id: int,
    ) -> Dict[str, Any]:
        """
        Create a template in WhatsApp from local database template
        
        Args:
            template_id: Local database template ID
            
        Returns:
            Dict with creation results
        """
        template = self.db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            return {
                "success": False,
                "error": "Template not found in database",
            }
        
        results = []
        
        for translation in template.translations:
            # Create template in WhatsApp for each language
            result = await whatsapp_service.create_template(
                name=template.template_name,
                category=template.category,
                language=translation.language.value,
                body_text=translation.body_text,
                header_text=translation.header_text,
                footer_text=translation.footer_text,
            )
            
            if result.success:
                # Update local record with WhatsApp template ID
                translation.whatsapp_template_id = result.template_id
                translation.approval_status = result.status or "PENDING"
                translation.updated_at = datetime.utcnow()
                
                results.append({
                    "language": translation.language.value,
                    "success": True,
                    "template_id": result.template_id,
                    "status": result.status,
                })
            else:
                results.append({
                    "language": translation.language.value,
                    "success": False,
                    "error": result.error,
                })
        
        self.db.commit()
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "template_name": template.template_name,
            "results": results,
            "total_languages": len(results),
            "successful": success_count,
        }
    
    async def delete_template_from_whatsapp(
        self,
        template_id: int,
    ) -> Dict[str, Any]:
        """
        Delete a template from WhatsApp
        
        Args:
            template_id: Local database template ID
            
        Returns:
            Dict with deletion results
        """
        template = self.db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            return {
                "success": False,
                "error": "Template not found in database",
            }
        
        result = await whatsapp_service.delete_template(template.template_name)
        
        if result.success:
            # Clear WhatsApp IDs from translations
            for translation in template.translations:
                translation.whatsapp_template_id = None
                translation.approval_status = "DELETED"
                translation.updated_at = datetime.utcnow()
            
            self.db.commit()
        
        return {
            "success": result.success,
            "template_name": result.template_name,
            "error": result.error,
        }
    
    async def get_template_status(
        self,
        template_id: int,
    ) -> Dict[str, Any]:
        """
        Get the WhatsApp approval status of a template
        
        Args:
            template_id: Local database template ID
            
        Returns:
            Dict with template status information
        """
        template = self.db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            return {
                "success": False,
                "error": "Template not found in database",
            }
        
        # Get status from WhatsApp
        wa_template = await whatsapp_service.get_template_by_name(template.template_name)
        
        if wa_template:
            # Update local status
            for translation in template.translations:
                if translation.language.value == wa_template.get("language"):
                    translation.approval_status = wa_template.get("status", "PENDING")
                    translation.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "success": True,
                "template_name": template.template_name,
                "whatsapp_status": wa_template.get("status"),
                "whatsapp_id": wa_template.get("id"),
                "category": wa_template.get("category"),
            }
        else:
            return {
                "success": True,
                "template_name": template.template_name,
                "whatsapp_status": "NOT_FOUND",
                "message": "Template not found in WhatsApp account",
            }
    
    def get_approved_templates(
        self,
        campaign_type: Optional[CampaignType] = None,
        language: Optional[Language] = None,
    ) -> List[Template]:
        """
        Get all approved templates from database
        
        Args:
            campaign_type: Optional filter by campaign type
            language: Optional filter by language
            
        Returns:
            List of approved Template objects
        """
        query = self.db.query(Template).filter(
            Template.is_active == True
        )
        
        if campaign_type:
            query = query.filter(Template.campaign_type == campaign_type)
        
        templates = query.all()
        
        # Filter by approved translations if language specified
        if language:
            approved_templates = []
            for template in templates:
                for translation in template.translations:
                    if (translation.language == language and 
                        translation.approval_status == "APPROVED"):
                        approved_templates.append(template)
                        break
            return approved_templates
        
        return templates
    
    def render_template(
        self,
        template_id: int,
        language: Language,
        variables: Dict[str, str],
    ) -> Optional[str]:
        """
        Render a template with variables filled in
        
        Args:
            template_id: Database template ID
            language: Language for the translation
            variables: Dict mapping variable names to values
            
        Returns:
            Rendered template body text or None if not found
        """
        template = self.db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            return None
        
        # Find the translation for the language
        translation = None
        for trans in template.translations:
            if trans.language == language:
                translation = trans
                break
        
        if not translation:
            return None
        
        # Get variable names from template
        variable_names = []
        if template.variable_names:
            variable_names = template.variable_names.split(",")
        
        # Render the template
        body_text = translation.body_text
        
        for idx, var_name in enumerate(variable_names, 1):
            placeholder = f"{{{{{idx}}}}}"  # {{1}}, {{2}}, etc.
            value = variables.get(var_name.strip(), "")
            body_text = body_text.replace(placeholder, value)
        
        return body_text


class MessageService:
    """
    Service for managing campaign messages
    Handles message queuing, sending, and status tracking
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.template_service = TemplateService(db)
    
    async def send_campaign_message(
        self,
        phone_number: str,
        template_name: str,
        language_code: str,
        params: List[str],
        message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a single campaign message
        
        Args:
            phone_number: Recipient phone number
            template_name: WhatsApp template name
            language_code: Language code for the template
            params: List of template parameters
            message_id: Optional local message ID for tracking
            
        Returns:
            Dict with send result
        """
        from app.models.message import Message
        from app.utils.enums import MessageStatus
        
        result = await whatsapp_service.send_template_message(
            phone_number=phone_number,
            template_name=template_name,
            language_code=language_code,
            body_params=params,
        )
        
        # Update message record if provided
        if message_id:
            message = self.db.query(Message).filter(Message.id == message_id).first()
            if message:
                if result.success:
                    message.whatsapp_message_id = result.message_id
                    message.status = MessageStatus.SENT
                    message.sent_at = datetime.utcnow()
                else:
                    message.status = MessageStatus.FAILED
                    message.failed_at = datetime.utcnow()
                    message.failure_reason = result.error
                    message.retry_count += 1
                
                message.updated_at = datetime.utcnow()
                self.db.commit()
        
        return {
            "success": result.success,
            "message_id": result.message_id,
            "phone_number": result.phone_number,
            "error": result.error,
        }
    
    async def send_bulk_campaign_messages(
        self,
        campaign_run_id: int,
        messages: List[Dict[str, Any]],
        template_name: str,
        language_code: str,
    ) -> Dict[str, Any]:
        """
        Send messages for a campaign run
        
        Args:
            campaign_run_id: Campaign run ID
            messages: List of message data with phone_number and params
            template_name: WhatsApp template name
            language_code: Language code
            
        Returns:
            Dict with bulk send results
        """
        from app.models.campaign import CampaignRun
        
        campaign_run = self.db.query(CampaignRun).filter(
            CampaignRun.id == campaign_run_id
        ).first()
        
        if not campaign_run:
            return {
                "success": False,
                "error": "Campaign run not found",
            }
        
        # Update campaign run status
        campaign_run.status = "RUNNING"
        campaign_run.started_at = datetime.utcnow()
        self.db.commit()
        
        results = []
        sent_count = 0
        failed_count = 0
        
        for msg_data in messages:
            result = await self.send_campaign_message(
                phone_number=msg_data["phone_number"],
                template_name=template_name,
                language_code=language_code,
                params=msg_data.get("params", []),
                message_id=msg_data.get("message_id"),
            )
            
            results.append(result)
            
            if result.get("success"):
                sent_count += 1
            else:
                failed_count += 1
        
        # Update campaign run stats
        campaign_run.messages_sent = sent_count
        campaign_run.messages_failed = failed_count
        campaign_run.status = "COMPLETED"
        campaign_run.completed_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "success": True,
            "campaign_run_id": campaign_run_id,
            "total": len(results),
            "sent": sent_count,
            "failed": failed_count,
        }
    
    def update_message_status(
        self,
        whatsapp_message_id: str,
        status: str,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Update message status from webhook callback
        
        Args:
            whatsapp_message_id: WhatsApp message ID
            status: New status (delivered, read, failed)
            timestamp: Optional timestamp from webhook
            
        Returns:
            True if message was found and updated
        """
        from app.models.message import Message
        from app.utils.enums import MessageStatus
        
        message = self.db.query(Message).filter(
            Message.whatsapp_message_id == whatsapp_message_id
        ).first()
        
        if not message:
            logger.warning(f"Message not found for WhatsApp ID: {whatsapp_message_id}")
            return False
        
        # Map status and update
        status_map = whatsapp_service.map_status_to_internal(status)
        message.status = status_map
        
        timestamp = timestamp or datetime.utcnow()
        
        if status_map == MessageStatus.DELIVERED:
            message.delivered_at = timestamp
        elif status_map == MessageStatus.READ:
            message.read_at = timestamp
        elif status_map == MessageStatus.FAILED:
            message.failed_at = timestamp
        
        message.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Update campaign run stats if applicable
        if message.campaign_run_id:
            self._update_campaign_run_stats(message.campaign_run_id)
        
        return True
    
    def _update_campaign_run_stats(self, campaign_run_id: int) -> None:
        """
        Update campaign run statistics based on message statuses
        
        Args:
            campaign_run_id: Campaign run ID to update
        """
        from app.models.campaign import CampaignRun
        from app.models.message import Message
        from app.utils.enums import MessageStatus
        
        campaign_run = self.db.query(CampaignRun).filter(
            CampaignRun.id == campaign_run_id
        ).first()
        
        if not campaign_run:
            return
        
        # Count messages by status
        messages = self.db.query(Message).filter(
            Message.campaign_run_id == campaign_run_id
        ).all()
        
        delivered = sum(1 for m in messages if m.status == MessageStatus.DELIVERED)
        read = sum(1 for m in messages if m.status == MessageStatus.READ)
        failed = sum(1 for m in messages if m.status == MessageStatus.FAILED)
        
        campaign_run.messages_delivered = delivered
        campaign_run.messages_read = read
        campaign_run.messages_failed = failed
        campaign_run.updated_at = datetime.utcnow()
        
        self.db.commit()
