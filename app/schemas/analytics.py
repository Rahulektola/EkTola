from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from app.schemas.campaign import CampaignStatsResponse
from app.schemas.message import MessageStatsResponse, FailureBreakdown
from app.schemas.contact import ContactSegmentStats


# ============ Jeweller Dashboard Schemas ============

class JewellerDashboardResponse(BaseModel):
    """Jeweller dashboard overview"""
    total_contacts: int
    opted_out_contacts: int
    active_campaigns: int
    total_messages_sent: int
    recent_delivery_rate: float  # Last 30 days
    recent_read_rate: float  # Last 30 days
    contact_distribution: List[ContactSegmentStats]
    recent_campaign_runs: List[CampaignStatsResponse]


# ============ Admin Dashboard Schemas ============

class JewellerUsageStats(BaseModel):
    """Per-jeweller usage statistics"""
    jeweller_id: int
    business_name: str
    total_contacts: int
    total_campaigns: int
    total_messages_sent: int
    messages_last_30_days: int
    delivery_rate: float
    read_rate: float
    last_active: Optional[datetime] = None


class AdminDashboardResponse(BaseModel):
    """Admin cross-jeweller dashboard"""
    total_jewellers: int
    active_jewellers: int
    total_contacts_across_jewellers: int
    total_messages_sent: int
    messages_last_30_days: int
    overall_delivery_rate: float
    overall_read_rate: float
    jeweller_stats: List[JewellerUsageStats]


class LanguageDistribution(BaseModel):
    """Message distribution by language"""
    language: str
    message_count: int
    percentage: float


class CampaignTypeDistribution(BaseModel):
    """Campaign distribution by type"""
    campaign_type: str
    count: int
    percentage: float


class AdminAnalyticsResponse(BaseModel):
    """Detailed admin analytics"""
    total_messages: int
    language_distribution: List[LanguageDistribution]
    campaign_type_distribution: List[CampaignTypeDistribution]
    failure_breakdown: List[FailureBreakdown]
    daily_message_volume: List[Dict[str, int]]  # [{"date": "2026-01-24", "count": 150}]
