"""
Template Management Service
Synchronizes WhatsApp templates with local database
"""
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.template import Template, TemplateTranslation
from app.services.whatsapp_service import whatsapp_service, TemplateResult
from app.utils.enums import CampaignType, Language, SegmentType

# Map WhatsApp language codes to local Language enum values
_LANGUAGE_ENUM_VALUES = {lang.value for lang in Language}

def _map_wa_language(wa_lang: str) -> Optional[Language]:
    """Map a WhatsApp language code (e.g. 'en_US', 'hi') to the local Language enum."""
    if not wa_lang:
        return None
    # Direct match?
    if wa_lang in _LANGUAGE_ENUM_VALUES:
        return Language(wa_lang)
    # Try base code (en_US -> en)
    base = wa_lang.split("_")[0]
    if base in _LANGUAGE_ENUM_VALUES:
        return Language(base)
    return None

logger = logging.getLogger(__name__)


# ============ Dummy value mapping for template preview ============

_DUMMY_VALUE_MAP: Dict[str, str] = {
    "customer": "Rahul",
    "amount": "\u20b95,000",
    "loan_amount": "\u20b950,000",
    "sip_amount": "\u20b95,000",
    "payment_amount": "\u20b95,000",
    "due_amount": "\u20b95,000",
    "date": "15-Jan-2026",
    "due_date": "15-Jan-2026",
    "payment_date": "15-Jan-2026",
    "start_date": "01-01-2026",
    "expiry_date": "31-11-2026",
    "phone": "98XXXX1234",
    "mobile": "98XXXX1234",
    "phone_number": "98XXXX1234",
    "jeweller_name": "Shree Jewellers",
    "shop_name": "Shree Jewellers",
    "business_name": "Shree Jewellers",
    "otp": "123456",
    "code": "123456",
    "discount": "20",
    "month": "January",
    "year": "2026",
    "plan_name": "Gold SIP Monthly",
    "scheme_name": "Gold SIP Monthly",
    "installment_number": "5",
    "total_installments": "12",
    "weight": "10g",
    "gold_weight": "10g",
    "rate": "\u20b97,200/g",
    # Generic positional names (auto-generated during WhatsApp sync)
    "header_param_1": "Rahul",    
    "body_param_1": "Shree Jewellers",
    "body_param_2": "April",
}


def extract_variable_names_from_text(text: Optional[str]) -> List[str]:
    """
    Extract unique variable names from template text containing {{variable}} placeholders.
    Supports both numeric ({{1}}, {{2}}) and named ({{customer}}, {{amount}}) placeholders.

    Args:
        text: Template text with {{...}} placeholders

    Returns:
        Deduplicated list of variable names in order of first appearance
    """
    if not text:
        return []

    # Find all {{...}} patterns and deduplicate preserving order
    seen: set = set()
    result: List[str] = []
    for m in re.findall(r'\{\{(\w+)\}\}', text):
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def generate_dummy_values(
    variable_names_csv: Optional[str],
    jeweller_name: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate dummy values for template variables based on variable names.

    Args:
        variable_names_csv: Comma-separated variable names (e.g. "customer_name,amount")
        jeweller_name: Optional jeweller business name to use for jeweller-related variables.

    Returns:
        Dict mapping each variable name to a human-readable dummy value.
    """
    if not variable_names_csv:
        return {}

    # Variables that should show the jeweller's actual business name
    _JEWELLER_KEYS = {
        "jeweller", "jeweller_name", "shop_name", "business_name",
        "body_param_1", "header_param_1",
    }

    result: Dict[str, str] = {}
    for var_name in variable_names_csv.split(","):
        var_name = var_name.strip()
        if not var_name:
            continue
        # Use actual jeweller name when available for jeweller-related variables
        if jeweller_name and var_name.lower() in _JEWELLER_KEYS:
            result[var_name] = jeweller_name
        else:
            result[var_name] = _DUMMY_VALUE_MAP.get(var_name.lower(), f"Sample_{var_name}")

    return result


def generate_dummy_values_from_text(
    header_text: Optional[str],
    body_text: Optional[str],
    footer_text: Optional[str],
    jeweller_name: Optional[str] = None,
) -> tuple:
    """
    Extract variables directly from template text and generate dummy values.
    Used as fallback when DB variable_names is empty.

    For numeric placeholders ({{1}}, {{2}}), maps them to descriptive names
    (header_param_1, body_param_1) for better dummy value lookup while keeping
    the original numeric keys for placeholder matching.

    Returns:
        (header_var_names, body_var_names, dummy_values)
    """
    header_vars = extract_variable_names_from_text(header_text)
    body_vars = extract_variable_names_from_text(body_text)
    footer_vars = extract_variable_names_from_text(footer_text)

    # Variables that should use the jeweller's business name
    _JEWELLER_KEYS = {
        "jeweller", "jeweller_name", "shop_name", "business_name",
        "body_param_1", "header_param_1",
    }

    # Build dummy values, using descriptive lookup names for numeric variables
    dummy_values: Dict[str, str] = {}

    def _add_vars(var_list: List[str], prefix: str) -> None:
        for idx, var_name in enumerate(var_list, 1):
            if var_name in dummy_values:
                continue
            if var_name.isdigit():
                # Numeric placeholder → use descriptive name for lookup
                lookup = f"{prefix}_param_{idx}"
            else:
                lookup = var_name
            if jeweller_name and lookup.lower() in _JEWELLER_KEYS:
                dummy_values[var_name] = jeweller_name
            else:
                dummy_values[var_name] = _DUMMY_VALUE_MAP.get(
                    lookup.lower(), _DUMMY_VALUE_MAP.get(var_name.lower(), f"Sample_{var_name}")
                )

    _add_vars(header_vars, "header")
    _add_vars(body_vars, "body")
    _add_vars(footer_vars, "footer")

    return header_vars, body_vars, dummy_values


def render_text_with_variables(
    text: Optional[str],
    variable_names: List[str],
    values: Dict[str, str],
) -> Optional[str]:
    """
    Replace placeholders in text with provided values.
    Supports both numeric ({{1}}, {{2}}) and named ({{customer}}, {{amount}}) placeholders.

    Args:
        text: Template text with {{...}} placeholders.
        variable_names: Ordered list of variable names.
        values: Dict mapping variable name -> replacement value.

    Returns:
        Rendered text, or None if input text is None.
    """
    if text is None:
        return None

    rendered = text
    
    # First, try to replace named placeholders directly
    # This handles templates like "Hi {{customer}}, your amount is {{amount}}"
    for var_name, value in values.items():
        named_placeholder = f"{{{{{var_name}}}}}"
        # Case-insensitive matching for better UX
        if named_placeholder in rendered:
            rendered = rendered.replace(named_placeholder, value)
    
    # Then, handle numeric placeholders with positional mapping
    # This handles templates like "Hi {{1}}, your amount is {{2}}"
    for idx, var_name in enumerate(variable_names, 1):
        numeric_placeholder = f"{{{{{idx}}}}}"  # {{1}}, {{2}}, etc.
        if numeric_placeholder in rendered:
            value = values.get(var_name.strip(), "")
            rendered = rendered.replace(numeric_placeholder, value)
    
    return rendered


class TemplateService:
    """
    Service for managing WhatsApp templates
    Handles synchronization between WhatsApp Business API (via PyWa) and local database
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def sync_templates_from_whatsapp(self) -> Dict[str, Any]:
        """
        Fetch templates from WhatsApp and sync with local database.
        Creates new local records for templates that don't exist yet.
        
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
                wa_language_raw = wa_template.get("language")
                wa_status = wa_template.get("status", "PENDING")
                wa_category = wa_template.get("category", "UTILITY")
                wa_id = wa_template.get("id")

                # Map WhatsApp language to local enum
                local_lang = _map_wa_language(wa_language_raw)
                if local_lang is None:
                    logger.warning(f"Skipping template {template_name}: unsupported language '{wa_language_raw}'")
                    skipped_count += 1
                    continue

                try:
                    # Check if template exists in database
                    existing = self.db.query(Template).filter(
                        Template.template_name == template_name
                    ).first()
                    
                    if existing:
                        # Update or add translation
                        matched = False
                        for translation in existing.translations:
                            if translation.language == local_lang:
                                translation.whatsapp_template_id = wa_id
                                translation.approval_status = wa_status
                                translation.updated_at = datetime.utcnow()
                                matched = True
                                updated_count += 1
                                break
                        if not matched:
                            # Language translation doesn't exist locally — create it
                            body_text, header_text, footer_text, header_var_names, body_var_names = self._extract_component_texts(
                                wa_template.get("components", [])
                            )
                            new_trans = TemplateTranslation(
                                template_id=existing.id,
                                language=local_lang,
                                body_text=body_text or template_name,
                                header_text=header_text,
                                footer_text=footer_text,
                                whatsapp_template_id=wa_id,
                                approval_status=wa_status,
                            )
                            self.db.add(new_trans)
                            updated_count += 1
                    else:
                        # Template doesn't exist locally — create it from WhatsApp data
                        body_text, header_text, footer_text, header_var_names, body_var_names = self._extract_component_texts(
                            wa_template.get("components", [])
                        )

                        # Determine campaign_type from WhatsApp category
                        campaign_type = CampaignType.MARKETING if wa_category == "MARKETING" else CampaignType.UTILITY

                        # Combine header and body variable names
                        all_var_names = []
                        
                        # Process header variables
                        for idx, var_name in enumerate(header_var_names, 1):
                            # If it's a numeric placeholder, generate descriptive name
                            if var_name.isdigit():
                                all_var_names.append(f"header_param_{idx}")
                            else:
                                # It's a named placeholder, preserve the name
                                all_var_names.append(var_name)
                        
                        # Process body variables
                        for idx, var_name in enumerate(body_var_names, 1):
                            # If it's a numeric placeholder, generate descriptive name
                            if var_name.isdigit():
                                all_var_names.append(f"body_param_{idx}")
                            else:
                                # It's a named placeholder, preserve the name
                                all_var_names.append(var_name)
                        
                        variable_count = len(all_var_names)
                        variable_names_csv = ",".join(all_var_names) if all_var_names else None

                        # Build display name from template_name
                        display_name = template_name.replace("_", " ").title()

                        new_template = Template(
                            template_name=template_name,
                            display_name=display_name,
                            campaign_type=campaign_type,
                            category=wa_category,
                            variable_count=variable_count,
                            variable_names=variable_names_csv,
                            is_active=True,
                        )
                        self.db.add(new_template)
                        self.db.flush()  # Get new_template.id

                        new_trans = TemplateTranslation(
                            template_id=new_template.id,
                            language=local_lang,
                            body_text=body_text or template_name,
                            header_text=header_text,
                            footer_text=footer_text,
                            whatsapp_template_id=wa_id,
                            approval_status=wa_status,
                        )
                        self.db.add(new_trans)
                        created_count += 1
                        logger.info(f"Created template {template_name} from WhatsApp ({local_lang.value}, {wa_status})")
                    
                except Exception as e:
                    logger.error(f"Error processing template {template_name}: {e}")
                    errors.append({"template": template_name, "error": str(e)})
                    self.db.rollback()
            
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

    @staticmethod
    def _extract_component_texts(components) -> tuple:
        """Extract body, header, footer text and variable information from WhatsApp template components.

        Returns:
            (body_text, header_text, footer_text, header_var_names, body_var_names)
            where var_names are lists of actual variable names found in the text
        """
        body_text = None
        header_text = None
        footer_text = None
        for comp in (components or []):
            comp_type = None
            if isinstance(comp, dict):
                comp_type = comp.get("type", "")
            else:
                comp_type = getattr(comp, "type", "")
                if hasattr(comp_type, "value"):
                    comp_type = comp_type.value

            comp_type_upper = str(comp_type).upper()

            if comp_type_upper == "BODY":
                body_text = comp.get("text") if isinstance(comp, dict) else getattr(comp, "text", None)
            elif comp_type_upper == "HEADER":
                header_text = comp.get("text") if isinstance(comp, dict) else getattr(comp, "text", None)
            elif comp_type_upper == "FOOTER":
                footer_text = comp.get("text") if isinstance(comp, dict) else getattr(comp, "text", None)

        # Extract variable names from header and body
        header_var_names = extract_variable_names_from_text(header_text)
        body_var_names = extract_variable_names_from_text(body_text)
        
        return body_text, header_text, footer_text, header_var_names, body_var_names
    
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
            variable_names = [name.strip() for name in template.variable_names.split(",")]
        
        # Render the template using the enhanced render function
        body_text = render_text_with_variables(
            text=translation.body_text,
            variable_names=variable_names,
            values=variables
        )
        
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
