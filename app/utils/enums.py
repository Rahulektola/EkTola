from enum import Enum


class SegmentType(str, Enum):
    """Contact segment types - MVP locked"""
    GOLD_LOAN = "GOLD_LOAN"
    GOLD_SIP = "GOLD_SIP"
    MARKETING = "MARKETING"


class CampaignType(str, Enum):
    """Campaign types"""
    UTILITY = "UTILITY"
    MARKETING = "MARKETING"


class CampaignStatus(str, Enum):
    """Campaign lifecycle status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class MessageStatus(str, Enum):
    """WhatsApp message delivery status"""
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class RecurrenceType(str, Enum):
    """Campaign recurrence patterns"""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ONE_TIME = "ONE_TIME"


class Language(str, Enum):
    """Supported languages for messaging"""
    ENGLISH = "en"
    HINDI = "hi"
    KANNADA = "kn"
    TAMIL = "ta"
    PUNJABI = "pa"
    
    @classmethod
    def get_fallback(cls):
        """Default fallback language"""
        return cls.ENGLISH
