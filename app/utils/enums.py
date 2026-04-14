from enum import Enum


class ApprovalStatus(str, Enum):
    """Jeweller approval status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SegmentType(str, Enum):
    """Contact segment types - MVP locked"""
    GOLD_LOAN = "GOLD_LOAN"
    GOLD_SIP = "GOLD_SIP"
    BOTH = "BOTH"
    MARKETING = "MARKETING"

    @staticmethod
    def merge(a: 'SegmentType', b: 'SegmentType') -> 'SegmentType':
        """Merge two segments together.
        SIP + LOAN -> BOTH, any + BOTH -> BOTH, same + same -> same,
        MARKETING + service -> BOTH.
        """
        if a == b:
            return a
        if a == SegmentType.BOTH or b == SegmentType.BOTH:
            return SegmentType.BOTH
        service = {SegmentType.GOLD_SIP, SegmentType.GOLD_LOAN}
        if {a, b} == service:
            return SegmentType.BOTH
        # One is MARKETING + one is a service segment
        if a == SegmentType.MARKETING or b == SegmentType.MARKETING:
            return SegmentType.BOTH
        return SegmentType.BOTH


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


class MessageType(str, Enum):
    """Distinguishes the origin / purpose of a message"""
    CAMPAIGN = "CAMPAIGN"         # Sent as part of a marketing / utility campaign
    SIP_REMINDER = "SIP_REMINDER" # Gold SIP payment due reminder
    LOAN_REMINDER = "LOAN_REMINDER"  # Gold Loan payment due reminder
    MANUAL_REMINDER = "MANUAL_REMINDER"  # Jeweller-triggered immediate reminder


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
    MARATHI = "mr"
    TAMIL = "ta"
    PUNJABI = "pa"
    
    @classmethod
    def get_fallback(cls):
        """Default fallback language"""
        return cls.ENGLISH
