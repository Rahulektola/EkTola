"""
Admin Dashboard Router
Full admin CRUD for jeweller management, contact/campaign management, impersonation
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, or_
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.models.campaign import Campaign, CampaignRun
from app.models.message import Message
from app.core.dependencies import get_current_admin
from app.core.security import create_access_token
from app.utils.enums import ApprovalStatus, MessageStatus, CampaignStatus, SegmentType, Language
from app.utils.whatsapp import normalize_phone_number, validate_phone_number
from app.schemas.admin import (
    JewellerDetailResponse, JewellerListResponse,
    JewellerUpdateRequest, AdminNotesRequest, MetaStatusUpdateRequest,
    RejectJewellerRequest, ApproveJewellerResponse,
    AdminContactListResponse, AdminContactsPageResponse,
    AdminCampaignCreateRequest, AdminCampaignListResponse, AdminCampaignsPageResponse,
    AdminMessageResponse, AdminMessagesPageResponse,
    ImpersonateResponse, JewellerAnalyticsResponse,
    WhatsAppStatusResponse,
    DeletedContactResponse, DeletedContactsListResponse,
    ContactPurgeRequest, ContactPurgeResponse,
    ContactRestoreRequest, ContactRestoreResponse,
)

import pandas as pd
import io

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== HELPERS ====================

def _get_jeweller_or_404(db: Session, jeweller_id: int) -> Jeweller:
    """Fetch jeweller by ID or raise 404"""
    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )
    return jeweller


def _build_jeweller_detail(db: Session, jeweller: Jeweller) -> JewellerDetailResponse:
    """Build full detail response with aggregates"""
    total_contacts = db.query(func.count(Contact.id)).filter(
        Contact.jeweller_id == jeweller.id,
        Contact.is_deleted == False
    ).scalar() or 0

    total_campaigns = db.query(func.count(Campaign.id)).filter(
        Campaign.jeweller_id == jeweller.id
    ).scalar() or 0

    total_messages = db.query(func.count(Message.id)).filter(
        Message.jeweller_id == jeweller.id
    ).scalar() or 0

    # Get user email
    user = db.query(User).filter(User.id == jeweller.user_id).first()
    email = user.email if user else None
    
    # Map is_approved boolean to ApprovalStatus enum
    approval_status = ApprovalStatus.APPROVED if jeweller.is_approved else ApprovalStatus.PENDING

    return JewellerDetailResponse(
        id=jeweller.id,
        user_id=jeweller.user_id,
        business_name=jeweller.business_name,
        owner_name=None,  # Not in current schema
        phone_number=jeweller.phone_number,
        address=None,  # Not in current schema
        location=None,  # Not in current schema
        waba_id=jeweller.waba_id,
        phone_number_id=jeweller.phone_number_id,
        is_whatsapp_business=bool(jeweller.waba_id),  # Derive from waba_id
        meta_app_status=bool(jeweller.waba_id),  # Derive from waba_id
        is_approved=jeweller.is_approved,
        approval_status=approval_status,
        rejection_reason=None,  # Not in current schema
        approved_at=None,  # Not in current schema
        approved_by_user_id=None,  # Not in current schema
        is_active=jeweller.is_active,
        admin_notes=None,  # Not in current schema
        timezone=jeweller.timezone,
        created_at=jeweller.created_at,
        updated_at=jeweller.updated_at,
        total_contacts=total_contacts,
        total_campaigns=total_campaigns,
        total_messages=total_messages,
        email=email,
    )


# ==================== 1. JEWELLER LIST & SEARCH ====================

@router.get("/jewellers", response_model=JewellerListResponse)
def list_jewellers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ApprovalStatus] = Query(None, alias="status"),
    q: Optional[str] = Query(None, description="Search by shop name or phone number"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    List all jewellers with filtering, search, pagination.
    Filters: status (PENDING/APPROVED/REJECTED), search by name/phone.
    """
    query = db.query(Jeweller)

    # Status filter (map enum to is_approved boolean)
    if status_filter:
        if status_filter == ApprovalStatus.APPROVED:
            query = query.filter(Jeweller.is_approved == True)
        elif status_filter == ApprovalStatus.PENDING:
            query = query.filter(Jeweller.is_approved == False)
        # REJECTED not supported in current schema

    # Search
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Jeweller.business_name.ilike(search_term),
                Jeweller.phone_number.ilike(search_term),
            )
        )

    # Status counts (unfiltered for badges)
    pending_count = db.query(func.count(Jeweller.id)).filter(
        Jeweller.is_approved == False
    ).scalar() or 0
    approved_count = db.query(func.count(Jeweller.id)).filter(
        Jeweller.is_approved == True
    ).scalar() or 0
    rejected_count = 0  # Not supported in current schema

    # Sort
    sort_col = getattr(Jeweller, sort_by, Jeweller.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    total = query.count()
    jewellers = query.offset((page - 1) * page_size).limit(page_size).all()

    return JewellerListResponse(
        jewellers=[_build_jeweller_detail(db, j) for j in jewellers],
        total=total,
        page=page,
        page_size=page_size,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
    )


@router.get("/jewellers/pending", response_model=JewellerListResponse)
def get_pending_jewellers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Get all jewellers pending approval (convenience endpoint)"""
    pending = db.query(Jeweller).filter(
        Jeweller.is_approved == False
    ).order_by(Jeweller.created_at.desc()).all()

    return JewellerListResponse(
        jewellers=[_build_jeweller_detail(db, j) for j in pending],
        total=len(pending),
        page=1,
        page_size=len(pending),
        pending_count=len(pending),
        approved_count=0,
        rejected_count=0,
    )


# ==================== 2. JEWELLER DETAIL ====================

@router.get("/jewellers/{jeweller_id}", response_model=JewellerDetailResponse)
def get_jeweller_detail(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Get single jeweller full profile with aggregates"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)
    return _build_jeweller_detail(db, jeweller)


# ==================== 3. JEWELLER EDITING ====================

@router.patch("/jewellers/{jeweller_id}", response_model=JewellerDetailResponse)
def update_jeweller(
    jeweller_id: int,
    request: JewellerUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Admin can edit any jeweller field (business name, phone, address, etc.)"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(jeweller, field, value)

    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)

    return _build_jeweller_detail(db, jeweller)


@router.put("/jewellers/{jeweller_id}/notes", response_model=JewellerDetailResponse)
def update_admin_notes(
    jeweller_id: int,
    request: AdminNotesRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Update admin internal notes (private, never visible to jeweller)"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)
    jeweller.admin_notes = request.admin_notes
    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)
    return _build_jeweller_detail(db, jeweller)


@router.put("/jewellers/{jeweller_id}/meta-status", response_model=JewellerDetailResponse)
def update_meta_integration(
    jeweller_id: int,
    request: MetaStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Update Meta WhatsApp integration details & credentials for a jeweller"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(jeweller, field, value)

    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)
    return _build_jeweller_detail(db, jeweller)


# ==================== 4. APPROVAL WORKFLOW ====================

@router.post("/jewellers/{jeweller_id}/approve", response_model=ApproveJewellerResponse)
def approve_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Approve a jeweller account.
    Sets is_approved to True.
    """
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    if jeweller.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeweller is already approved"
        )

    jeweller.is_approved = True
    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)

    return ApproveJewellerResponse(
        id=jeweller.id,
        business_name=jeweller.business_name,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=jeweller.updated_at,
        message=f"Jeweller '{jeweller.business_name}' has been approved successfully.",
    )


@router.post("/jewellers/{jeweller_id}/reject", response_model=ApproveJewellerResponse)
def reject_jeweller(
    jeweller_id: int,
    request: RejectJewellerRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Reject a jeweller account.
    Sets is_approved to False (rejection_reason not stored in current schema).
    """
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    jeweller.is_approved = False
    jeweller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jeweller)

    return ApproveJewellerResponse(
        id=jeweller.id,
        business_name=jeweller.business_name,
        approval_status=ApprovalStatus.REJECTED,
        rejection_reason=request.rejection_reason,
        message=f"Jeweller '{jeweller.business_name}' has been rejected.",
    )


# ==================== 5. DELETE JEWELLER ====================

@router.delete("/jewellers/{jeweller_id}")
def delete_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Delete jeweller account and associated user (cascades contacts, campaigns, messages)"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    user_id = jeweller.user_id
    db.delete(jeweller)

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)

    db.commit()
    return {"message": "Jeweller deleted successfully", "jeweller_id": jeweller_id}


# ==================== 6. CONTACT MANAGEMENT ====================

@router.get("/jewellers/{jeweller_id}/contacts", response_model=AdminContactsPageResponse)
def get_jeweller_contacts(
    jeweller_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    segment: Optional[SegmentType] = None,
    q: Optional[str] = Query(None, description="Search by name or phone"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """View any jeweller's contact list with filtering and search"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    query = db.query(Contact).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.is_deleted == False,
    )

    if segment:
        query = query.filter(Contact.segment == segment)

    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Contact.name.ilike(search_term),
                Contact.phone_number.ilike(search_term),
            )
        )

    total = query.count()
    contacts = query.order_by(Contact.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return AdminContactsPageResponse(
        contacts=[AdminContactListResponse.model_validate(c) for c in contacts],
        total=total,
        page=page,
        page_size=page_size,
        jeweller_id=jeweller_id,
        jeweller_name=jeweller.business_name,
    )


@router.get("/jewellers/{jeweller_id}/contacts/diagnostics")
def get_jeweller_contacts_diagnostics(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Diagnostic endpoint to debug contact display issues.
    Returns detailed information about contacts for a jeweller.
    """
    jeweller = _get_jeweller_or_404(db, jeweller_id)
    
    # Get total contact counts with different filters
    total_all = db.query(Contact).filter(Contact.jeweller_id == jeweller_id).count()
    total_active = db.query(Contact).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.is_deleted == False
    ).count()
    total_deleted = db.query(Contact).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.is_deleted == True
    ).count()
    
    # Get sample contacts
    sample_contacts = db.query(Contact).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.is_deleted == False
    ).order_by(Contact.created_at.desc()).limit(5).all()
    
    # Get contact distribution by segment
    segment_distribution = db.query(
        Contact.segment,
        func.count(Contact.id).label('count')
    ).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.is_deleted == False
    ).group_by(Contact.segment).all()
    
    return {
        "jeweller_id": jeweller_id,
        "jeweller_name": jeweller.business_name,
        "diagnostics": {
            "total_contacts_all": total_all,
            "total_contacts_active": total_active,
            "total_contacts_deleted": total_deleted,
            "segment_distribution": [
                {"segment": s.segment, "count": s.count} 
                for s in segment_distribution
            ],
            "sample_contacts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "phone_number": c.phone_number,
                    "segment": c.segment,
                    "created_at": c.created_at.isoformat(),
                    "is_deleted": c.is_deleted,
                }
                for c in sample_contacts
            ],
        },
        "api_test": {
            "endpoint": f"/admin/jewellers/{jeweller_id}/contacts",
            "message": "Use this endpoint to fetch contacts normally"
        }
    }


@router.post("/jewellers/{jeweller_id}/contacts/upload")
async def admin_upload_contacts(
    jeweller_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Admin uploads CSV/Excel contacts on behalf of a specific jeweller.
    Expected columns: Name, Mobile, Purpose (SIP/LOAN/BOTH), Date (optional)
    """
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported"
        )

    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    df.columns = df.columns.str.strip().str.lower()

    required_columns = ['name', 'mobile', 'purpose']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}. Expected: Name, Mobile, Purpose, Date"
        )

    purpose_to_segment = {
        "SIP": SegmentType.MARKETING,
        "LOAN": SegmentType.GOLD_LOAN,
        "BOTH": SegmentType.MARKETING,
    }

    total_rows = len(df)
    imported = 0
    updated = 0
    failed = 0
    failure_details = []

    for idx, row in df.iterrows():
        try:
            name = str(row.get('name', '')).strip()
            mobile = str(row.get('mobile', '')).strip()
            purpose = str(row.get('purpose', '')).strip().upper()
            date_val = str(row.get('date', '')) if 'date' in df.columns else ''

            if not mobile or not name:
                raise ValueError("Name and mobile are required")
            if purpose not in ['SIP', 'LOAN', 'BOTH']:
                raise ValueError(f"Invalid purpose: {purpose}. Must be SIP, LOAN, or BOTH")

            normalized_mobile = normalize_phone_number(mobile)
            if not validate_phone_number(normalized_mobile):
                raise ValueError(f"Invalid mobile number: {mobile}")

            segment = purpose_to_segment.get(purpose, SegmentType.MARKETING)

            existing = db.query(Contact).filter(
                Contact.jeweller_id == jeweller_id,
                Contact.phone_number == normalized_mobile,
            ).first()

            if existing:
                existing.name = name
                existing.segment = segment
                existing.notes = f"Purpose: {purpose}, Date: {date_val}"
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                new_contact = Contact(
                    jeweller_id=jeweller_id,
                    phone_number=normalized_mobile,
                    name=name,
                    segment=segment,
                    preferred_language=Language.ENGLISH,
                    notes=f"Purpose: {purpose}, Date: {date_val}",
                )
                db.add(new_contact)
                imported += 1
                print(f"[Admin Upload] Created contact for jeweller_id={jeweller_id}: {name} ({normalized_mobile})")

        except Exception as e:
            failed += 1
            failure_details.append({
                "row": idx + 2,
                "name": str(row.get('name', 'N/A')),
                "mobile": str(row.get('mobile', 'N/A')),
                "reason": str(e),
            })

    db.commit()

    return {
        "total_rows": total_rows,
        "imported": imported,
        "updated": updated,
        "failed": failed,
        "failure_details": failure_details,
        "jeweller_id": jeweller_id,
        "jeweller_name": jeweller.business_name,
        "message": f"Upload completed for {jeweller.business_name}",
    }


@router.patch("/contacts/{contact_id}", response_model=AdminContactListResponse)
def admin_edit_contact(
    contact_id: int,
    name: Optional[str] = None,
    phone_number: Optional[str] = None,
    segment: Optional[SegmentType] = None,
    preferred_language: Optional[Language] = None,
    opted_out: Optional[bool] = None,
    notes: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Admin can edit any contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    if name is not None:
        contact.name = name
    if phone_number is not None:
        contact.phone_number = phone_number
    if segment is not None:
        contact.segment = segment
    if preferred_language is not None:
        contact.preferred_language = preferred_language
    if opted_out is not None:
        contact.opted_out = opted_out
        if opted_out:
            contact.opted_out_at = datetime.utcnow()
    if notes is not None:
        contact.notes = notes
    if tags is not None:
        contact.tags = tags

    contact.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contact)
    return AdminContactListResponse.model_validate(contact)


@router.delete("/contacts/{contact_id}")
def admin_delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Soft-delete a contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.is_deleted = True
    contact.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Contact deleted", "contact_id": contact_id}


# ==================== 7. CAMPAIGN MANAGEMENT ====================

@router.get("/jewellers/{jeweller_id}/campaigns", response_model=AdminCampaignsPageResponse)
def get_jeweller_campaigns(
    jeweller_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[CampaignStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """View any jeweller's campaigns"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    query = db.query(Campaign).filter(Campaign.jeweller_id == jeweller_id)
    if status_filter:
        query = query.filter(Campaign.status == status_filter)

    total = query.count()
    campaigns = query.order_by(Campaign.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    campaign_responses = []
    for c in campaigns:
        total_runs = db.query(func.count(CampaignRun.id)).filter(
            CampaignRun.campaign_id == c.id
        ).scalar() or 0
        total_msgs = db.query(func.count(Message.id)).filter(
            Message.jeweller_id == jeweller_id
        ).scalar() or 0

        campaign_responses.append(AdminCampaignListResponse(
            id=c.id,
            jeweller_id=c.jeweller_id,
            name=c.name,
            description=c.description,
            campaign_type=c.campaign_type,
            sub_segment=c.sub_segment,
            status=c.status,
            template_id=c.template_id,
            recurrence_type=c.recurrence_type.value if c.recurrence_type else "",
            start_date=str(c.start_date),
            start_time=str(c.start_time),
            end_date=str(c.end_date) if c.end_date else None,
            created_at=c.created_at,
            updated_at=c.updated_at,
            total_runs=total_runs,
            total_messages_sent=total_msgs,
        ))

    return AdminCampaignsPageResponse(
        campaigns=campaign_responses,
        total=total,
        page=page,
        page_size=page_size,
        jeweller_id=jeweller_id,
        jeweller_name=jeweller.business_name,
    )


@router.post("/jewellers/{jeweller_id}/campaigns", status_code=status.HTTP_201_CREATED)
def admin_create_campaign(
    jeweller_id: int,
    request: AdminCampaignCreateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Admin creates a campaign on behalf of a jeweller.
    Uses the jeweller's WhatsApp API credentials when sending.
    """
    from app.utils.enums import CampaignType, RecurrenceType
    from datetime import date, time as dt_time

    jeweller = _get_jeweller_or_404(db, jeweller_id)

    if not jeweller.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create campaign for unapproved jeweller"
        )

    # Validate UTILITY requires sub_segment
    if request.campaign_type == CampaignType.UTILITY and not request.sub_segment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sub_segment is required for UTILITY campaigns"
        )

    # Parse dates/times
    try:
        start_date = date.fromisoformat(request.start_date)
        start_time = dt_time.fromisoformat(request.start_time)
        end_date = date.fromisoformat(request.end_date) if request.end_date else None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date/time format: {str(e)}"
        )

    new_campaign = Campaign(
        jeweller_id=jeweller_id,
        created_by_user_id=current_admin.id,
        name=request.name,
        description=request.description,
        campaign_type=request.campaign_type,
        sub_segment=request.sub_segment,
        template_id=request.template_id,
        recurrence_type=RecurrenceType(request.recurrence_type),
        start_date=start_date,
        start_time=start_time,
        end_date=end_date,
        timezone=jeweller.timezone,
        status=CampaignStatus.DRAFT,
        variable_mapping=str(request.variable_mapping) if request.variable_mapping else None,
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)

    return {
        "id": new_campaign.id,
        "jeweller_id": jeweller_id,
        "name": new_campaign.name,
        "status": new_campaign.status.value,
        "message": f"Campaign '{new_campaign.name}' created for {jeweller.business_name}",
    }


@router.post("/campaigns/{campaign_id}/start")
def admin_start_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Admin can activate/start any campaign"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.status == CampaignStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign is already active")

    campaign.status = CampaignStatus.ACTIVE
    campaign.updated_at = datetime.utcnow()
    db.commit()

    return {
        "campaign_id": campaign.id,
        "status": campaign.status.value,
        "message": f"Campaign '{campaign.name}' is now active.",
    }


# ==================== 8. MESSAGE HISTORY ====================

@router.get("/jewellers/{jeweller_id}/messages", response_model=AdminMessagesPageResponse)
def get_jeweller_messages(
    jeweller_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: Optional[MessageStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """View message history for a specific jeweller"""
    _get_jeweller_or_404(db, jeweller_id)

    query = db.query(Message).filter(Message.jeweller_id == jeweller_id)
    if status_filter:
        query = query.filter(Message.status == status_filter)

    total = query.count()
    messages = query.order_by(Message.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return AdminMessagesPageResponse(
        messages=[
            AdminMessageResponse(
                id=m.id,
                jeweller_id=m.jeweller_id,
                contact_id=m.contact_id,
                phone_number=m.phone_number,
                template_name=m.template_name,
                language=m.language.value if m.language else "en",
                message_body=m.message_body or "",
                status=m.status.value if m.status else "QUEUED",
                whatsapp_message_id=m.whatsapp_message_id,
                queued_at=m.queued_at,
                sent_at=m.sent_at,
                delivered_at=m.delivered_at,
                read_at=m.read_at,
                failed_at=m.failed_at,
                failure_reason=m.failure_reason,
            )
            for m in messages
        ],
        total=total,
        page=page,
        page_size=page_size,
        jeweller_id=jeweller_id,
    )


# ==================== 9. IMPERSONATION MODE ====================

@router.post("/impersonate/{jeweller_id}", response_model=ImpersonateResponse)
def impersonate_jeweller(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    'Login As' / Impersonation Mode.
    Returns a token that lets the admin see exactly what the jeweller sees.
    The token has jeweller_id set so jeweller endpoints work, but is_admin stays True
    for audit trail.
    """
    jeweller = _get_jeweller_or_404(db, jeweller_id)

    # Create a scoped token — acts as this jeweller
    token_data = {
        "user_id": jeweller.user_id,
        "email": current_admin.email,
        "is_admin": False,  # Must be False so jeweller endpoints accept it
        "jeweller_id": jeweller.id,
        "impersonated_by": current_admin.id,  # Audit trail
    }
    access_token = create_access_token(token_data)

    return ImpersonateResponse(
        access_token=access_token,
        jeweller_id=jeweller.id,
        jeweller_name=jeweller.business_name,
        message=f"Impersonating jeweller '{jeweller.business_name}'. Use this token for jeweller endpoints.",
    )


# ==================== 10. ADMIN ANALYTICS DRILL-DOWN ====================

@router.get("/jewellers/{jeweller_id}/analytics", response_model=JewellerAnalyticsResponse)
def get_jeweller_analytics(
    jeweller_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Single jeweller drill-down analytics for admin"""
    jeweller = _get_jeweller_or_404(db, jeweller_id)
    start_date = datetime.utcnow() - timedelta(days=days)

    total_contacts = db.query(func.count(Contact.id)).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.is_deleted == False,
    ).scalar() or 0

    opted_out = db.query(func.count(Contact.id)).filter(
        Contact.jeweller_id == jeweller_id,
        Contact.opted_out == True,
        Contact.is_deleted == False,
    ).scalar() or 0

    total_campaigns = db.query(func.count(Campaign.id)).filter(
        Campaign.jeweller_id == jeweller_id,
    ).scalar() or 0

    active_campaigns = db.query(func.count(Campaign.id)).filter(
        Campaign.jeweller_id == jeweller_id,
        Campaign.status == CampaignStatus.ACTIVE,
    ).scalar() or 0

    total_messages = db.query(func.count(Message.id)).filter(
        Message.jeweller_id == jeweller_id,
    ).scalar() or 0

    messages_period = db.query(func.count(Message.id)).filter(
        Message.jeweller_id == jeweller_id,
        Message.created_at >= start_date,
    ).scalar() or 0

    # Delivery / read rates
    stats = db.query(
        func.count(Message.id).label('total'),
        func.sum(func.cast(Message.status == MessageStatus.DELIVERED, Integer)).label('delivered'),
        func.sum(func.cast(Message.status == MessageStatus.READ, Integer)).label('read'),
    ).filter(
        Message.jeweller_id == jeweller_id,
    ).first()

    total_stat = stats.total or 0
    delivery_rate = (stats.delivered / total_stat * 100) if total_stat > 0 else 0
    read_rate = (stats.read / stats.delivered * 100) if stats.delivered and stats.delivered > 0 else 0

    # Campaign success rates
    runs = db.query(CampaignRun).filter(
        CampaignRun.jeweller_id == jeweller_id,
        CampaignRun.status == "COMPLETED",
    ).order_by(CampaignRun.completed_at.desc()).limit(10).all()

    campaign_success_rates = []
    for run in runs:
        campaign = db.query(Campaign).filter(Campaign.id == run.campaign_id).first()
        dr = (run.messages_delivered / run.messages_sent * 100) if run.messages_sent > 0 else 0
        rr = (run.messages_read / run.messages_delivered * 100) if run.messages_delivered > 0 else 0
        campaign_success_rates.append({
            "campaign_id": run.campaign_id,
            "campaign_name": campaign.name if campaign else "Unknown",
            "run_id": run.id,
            "messages_sent": run.messages_sent,
            "delivered": run.messages_delivered,
            "read": run.messages_read,
            "failed": run.messages_failed,
            "delivery_rate": round(dr, 2),
            "read_rate": round(rr, 2),
            "completed_at": str(run.completed_at),
        })

    # Daily message volume
    daily_volume = db.query(
        func.date(Message.created_at).label('date'),
        func.count(Message.id).label('count'),
    ).filter(
        Message.jeweller_id == jeweller_id,
        Message.created_at >= start_date,
    ).group_by(func.date(Message.created_at)).all()

    daily_message_volume = [
        {"date": str(dv.date), "count": dv.count} for dv in daily_volume
    ]

    return JewellerAnalyticsResponse(
        jeweller_id=jeweller_id,
        business_name=jeweller.business_name,
        total_contacts=total_contacts,
        opted_out_contacts=opted_out,
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_messages=total_messages,
        messages_last_30_days=messages_period,
        delivery_rate=round(delivery_rate, 2),
        read_rate=round(read_rate, 2),
        campaign_success_rates=campaign_success_rates,
        daily_message_volume=daily_message_volume,
    )


# ==================== 11. WHATSAPP STATUS ====================

@router.get("/jewellers/{jeweller_id}/whatsapp-status", response_model=WhatsAppStatusResponse)
def get_jeweller_whatsapp_status(
    jeweller_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Get WhatsApp connection status for a jeweller.
    
    Shows:
    - Connection status
    - WABA details
    - Phone number details
    - Token expiry information
    - Business verification status
    
    **Admin only**
    """
    jeweller = _get_jeweller_or_404(db, jeweller_id)
    
    # Check if WhatsApp is connected
    connected = bool(
        jeweller.waba_id and 
        jeweller.phone_number_id and 
        jeweller.access_token
    )
    
    # Calculate token expiry days
    token_expires_in_days = None
    if jeweller.access_token_expires_at:
        delta = jeweller.access_token_expires_at - datetime.utcnow()
        token_expires_in_days = delta.days
    
    return WhatsAppStatusResponse(
        connected=connected,
        waba_id=jeweller.waba_id,
        waba_name=jeweller.waba_name,
        phone_number_id=jeweller.phone_number_id,
        phone_display_number=jeweller.phone_display_number,
        business_verification_status=jeweller.business_verification_status,
        connected_at=jeweller.whatsapp_connected_at,
        token_expires_at=jeweller.access_token_expires_at,
        token_expires_in_days=token_expires_in_days,
        last_token_refresh=jeweller.last_token_refresh,
        fb_app_scoped_user_id=jeweller.fb_app_scoped_user_id,
    )


# ==================== 12. DELETED CONTACTS MANAGEMENT ====================

@router.get("/contacts/deleted", response_model=DeletedContactsListResponse)
def list_deleted_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    jeweller_id: Optional[int] = Query(None, description="Filter by jeweller ID"),
    older_than_days: Optional[int] = Query(None, ge=1, description="Only show contacts deleted more than X days ago"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    List all soft-deleted contacts across all jewellers or for a specific jeweller.
    
    Use this to review deleted contacts before restoration or permanent purge.
    
    **Admin only**
    """
    query = db.query(Contact).filter(Contact.is_deleted == True)
    
    jeweller_name = None
    if jeweller_id:
        jeweller = _get_jeweller_or_404(db, jeweller_id)
        jeweller_name = jeweller.business_name
        query = query.filter(Contact.jeweller_id == jeweller_id)
    
    if older_than_days:
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        query = query.filter(Contact.deleted_at <= cutoff)
    
    total = query.count()
    contacts = query.order_by(Contact.deleted_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    now = datetime.utcnow()
    contact_responses = []
    for c in contacts:
        days_since = (now - c.deleted_at).days if c.deleted_at else 0
        contact_responses.append(DeletedContactResponse(
            id=c.id,
            jeweller_id=c.jeweller_id,
            phone_number=c.phone_number,
            name=c.name,
            customer_id=c.customer_id,
            segment=c.segment,
            preferred_language=c.preferred_language,
            deleted_at=c.deleted_at,
            days_since_deletion=days_since,
        ))
    
    return DeletedContactsListResponse(
        contacts=contact_responses,
        total=total,
        page=page,
        page_size=page_size,
        jeweller_id=jeweller_id,
        jeweller_name=jeweller_name,
    )


@router.post("/contacts/purge", response_model=ContactPurgeResponse)
def purge_deleted_contacts(
    request: ContactPurgeRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Permanently delete (hard delete) contacts that have been soft-deleted for more than X days.
    
    **WARNING**: This action is irreversible. All associated message history will also be deleted.
    
    - `older_than_days`: Only purge contacts deleted more than this many days ago (default: 30)
    - `jeweller_id`: Optionally limit purge to a specific jeweller
    
    **Admin only**
    """
    cutoff = datetime.utcnow() - timedelta(days=request.older_than_days)
    
    query = db.query(Contact).filter(
        Contact.is_deleted == True,
        Contact.deleted_at <= cutoff
    )
    
    if request.jeweller_id:
        # Verify jeweller exists
        _get_jeweller_or_404(db, request.jeweller_id)
        query = query.filter(Contact.jeweller_id == request.jeweller_id)
    
    # Get count before deletion
    purge_count = query.count()
    
    if purge_count == 0:
        return ContactPurgeResponse(
            purged_count=0,
            message="No contacts found matching purge criteria",
            jeweller_id=request.jeweller_id,
            older_than_days=request.older_than_days,
        )
    
    # Permanently delete (cascade will delete messages)
    query.delete(synchronize_session=False)
    db.commit()
    
    jeweller_msg = f" for jeweller {request.jeweller_id}" if request.jeweller_id else ""
    return ContactPurgeResponse(
        purged_count=purge_count,
        message=f"Permanently deleted {purge_count} contacts{jeweller_msg} (deleted more than {request.older_than_days} days ago)",
        jeweller_id=request.jeweller_id,
        older_than_days=request.older_than_days,
    )


@router.post("/contacts/restore", response_model=ContactRestoreResponse)
def restore_deleted_contacts(
    request: ContactRestoreRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Restore soft-deleted contacts by their IDs.
    
    Contacts will be restored to active status and visible in dashboards again.
    
    **Admin only**
    """
    restored_ids = []
    failed_ids = []
    
    for contact_id in request.contact_ids:
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.is_deleted == True
        ).first()
        
        if contact:
            contact.is_deleted = False
            contact.deleted_at = None
            contact.updated_at = datetime.utcnow()
            restored_ids.append(contact_id)
        else:
            failed_ids.append(contact_id)
    
    db.commit()
    
    return ContactRestoreResponse(
        restored_count=len(restored_ids),
        failed_count=len(failed_ids),
        message=f"Restored {len(restored_ids)} contacts" + (f", {len(failed_ids)} not found or already active" if failed_ids else ""),
        restored_ids=restored_ids,
        failed_ids=failed_ids,
    )
