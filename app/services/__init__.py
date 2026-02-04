"""
Services Module
Contains business logic services for WhatsApp messaging and template management
"""

from app.services.whatsapp_service import (
    WhatsAppService,
    whatsapp_service,
    MessageResult,
    TemplateResult,
    WhatsAppServiceError,
    send_whatsapp_otp,
    send_template_message,
)

from app.services.template_service import (
    TemplateService,
    MessageService,
)

__all__ = [
    # WhatsApp Service
    "WhatsAppService",
    "whatsapp_service",
    "MessageResult",
    "TemplateResult",
    "WhatsAppServiceError",
    "send_whatsapp_otp",
    "send_template_message",
    # Template Service
    "TemplateService",
    "MessageService",
]
