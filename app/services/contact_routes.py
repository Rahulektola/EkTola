from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from typing import List, Optional
from app.database import get_db
from app.core.dependencies import get_current_jeweller
from app.core.datetime_utils import now_utc
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactResponse,
    ContactListResponse, ContactImportReport, ContactSegmentStats,
    DashboardContactCreate, DashboardContactResponse, DashboardBulkUploadReport,
    ContactBulkDelete, ContactBulkDeleteResponse,
    BulkContactUpdateRequest, BulkContactUpdateResponse,
    PaymentScheduleUpdate, PaymentScheduleClear,
    BulkPaymentScheduleRequest, BulkPaymentScheduleResponse,
    PaymentScheduleResponse, PaymentScheduleListResponse,
    ReminderPreviewResponse,
)
from app.utils.enums import SegmentType, Language
from app.services.whatsapp_service import normalize_phone_number, validate_phone_number
import pandas as pd
import io
from datetime import datetime

router = APIRouter(prefix="/contacts", tags=["Contacts"])


# ============ Dashboard-Compatible Endpoints ============

@router.post("/add-one", response_model=DashboardContactResponse, status_code=status.HTTP_201_CREATED)
def add_one_contact(
    request: DashboardContactCreate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Add single contact from dashboard (simplified format)
    Accepts: name, mobile, purpose (SIP/LOAN/BOTH), date
    """
    # Normalize and validate phone number
    normalized_mobile = normalize_phone_number(request.mobile)
    if not validate_phone_number(normalized_mobile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile number format. Use 10 digits or +91 format"
        )
    
    # Map purpose to segment
    purpose_to_segment = {
        "SIP": SegmentType.GOLD_SIP,
        "LOAN": SegmentType.GOLD_LOAN,
        "BOTH": SegmentType.BOTH
    }
    
    segment = purpose_to_segment.get(request.purpose, SegmentType.MARKETING)
    
    # Check if contact exists — merge segments instead of rejecting
    existing = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.phone_number == normalized_mobile
    ).first()
    
    if existing:
        # Merge segment with existing record
        existing.segment = SegmentType.merge(existing.segment, segment)
        existing.name = request.name or existing.name
        existing.notes = f"Purpose: {request.purpose}, Date: {request.date}"
        existing.updated_at = now_utc()
        if existing.is_deleted:
            existing.is_deleted = False
            existing.deleted_at = None
        db.commit()
        db.refresh(existing)
        
        return DashboardContactResponse(
            id=existing.id,
            name=existing.name,
            mobile=existing.phone_number,
            purpose=request.purpose,
            date=request.date,
            created_at=existing.created_at
        )
    
    # Create new contact
    new_contact = Contact(
        jeweller_id=current_jeweller.id,
        phone_number=normalized_mobile,
        name=request.name,
        segment=segment,
        preferred_language=Language.ENGLISH,  # Default
        notes=f"Purpose: {request.purpose}, Date: {request.date}"
    )
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    # Return dashboard format
    return DashboardContactResponse(
        id=new_contact.id,
        name=new_contact.name,
        mobile=new_contact.phone_number,
        purpose=request.purpose,
        date=request.date,
        created_at=new_contact.created_at
    )


@router.post("/bulk-upload-dashboard", response_model=DashboardBulkUploadReport)
async def bulk_upload_dashboard(
    file: UploadFile = File(...),
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Bulk upload contacts from dashboard
    Expected columns: Name, Mobile, Purpose, Date
    Purpose can be: SIP, LOAN, or BOTH
    """
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported"
        )
    
    # Read file
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
    
    # Normalize column names (case-insensitive)
    df.columns = df.columns.str.strip().str.lower()
    
    # Check for required columns
    required_columns = ['name', 'mobile', 'purpose']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}. Expected: Name, Mobile, Purpose, Date"
        )
    
    total_rows = len(df)
    imported = 0
    updated = 0
    merged = 0  # intra-CSV duplicates collapsed
    failed = 0
    failure_details = []
    
    # Map purpose to segment
    purpose_to_segment = {
        "SIP": SegmentType.GOLD_SIP,
        "LOAN": SegmentType.GOLD_LOAN,
        "BOTH": SegmentType.BOTH
    }
    
    # ---- Phase 1: Validate all rows and pre-merge intra-CSV duplicates ----
    # Maps normalized_mobile -> {name, segment, notes, original_rows}
    deduped: dict = {}  # phone -> merged record
    
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
                raise ValueError(f"Invalid mobile number format: {mobile}")
            
            segment = purpose_to_segment.get(purpose, SegmentType.MARKETING)
            
            if normalized_mobile in deduped:
                # Merge with existing entry in same CSV
                entry = deduped[normalized_mobile]
                entry['segment'] = SegmentType.merge(entry['segment'], segment)
                entry['name'] = entry['name'] or name  # keep first non-empty name
                if date_val and date_val != 'nan':
                    entry['notes'] += f", Date: {date_val}"
                entry['original_rows'].append(idx + 2)
                merged += 1
            else:
                deduped[normalized_mobile] = {
                    'name': name,
                    'segment': segment,
                    'notes': f"Purpose: {purpose}, Date: {date_val}",
                    'original_rows': [idx + 2],
                }
        
        except Exception as e:
            failed += 1
            failure_details.append({
                "row": idx + 2,
                "name": str(row.get('name', 'N/A')),
                "mobile": str(row.get('mobile', 'N/A')),
                "reason": str(e)
            })
    
    # ---- Phase 2: Upsert deduplicated records into DB, merging with existing ----
    # Batch-fetch all existing contacts in a single query instead of one query per phone number
    phone_numbers = list(deduped.keys())
    existing_contacts = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.phone_number.in_(phone_numbers)
    ).all()
    existing_map = {c.phone_number: c for c in existing_contacts}
    
    for normalized_mobile, entry in deduped.items():
        try:
            existing = existing_map.get(normalized_mobile)
            
            if existing:
                # Merge segment with existing DB record
                existing.segment = SegmentType.merge(existing.segment, entry['segment'])
                existing.name = entry['name'] or existing.name
                existing.notes = entry['notes']
                existing.updated_at = now_utc()
                if existing.is_deleted:
                    existing.is_deleted = False
                    existing.deleted_at = None
                updated += 1
            else:
                new_contact = Contact(
                    jeweller_id=current_jeweller.id,
                    phone_number=normalized_mobile,
                    name=entry['name'],
                    segment=entry['segment'],
                    preferred_language=Language.ENGLISH,
                    notes=entry['notes']
                )
                db.add(new_contact)
                imported += 1
                print(f"[Jeweller Upload] Created contact for jeweller_id={current_jeweller.id}: {entry['name']} ({normalized_mobile})")
        
        except Exception as e:
            failed += 1
            failure_details.append({
                "rows": entry['original_rows'],
                "name": entry['name'],
                "mobile": normalized_mobile,
                "reason": str(e)
            })
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while saving contacts: {str(e)}"
        )
    
    merge_msg = f", merged {merged} duplicate(s) within file" if merged > 0 else ""
    
    return DashboardBulkUploadReport(
        total_rows=total_rows,
        imported=imported,
        updated=updated,
        merged=merged,
        failed=failed,
        failure_details=failure_details,
        message=f"Successfully imported {imported} contacts, updated {updated}, failed {failed}{merge_msg}"
    )


# ============ Original Advanced Endpoints ============


@router.post("/upload", response_model=ContactImportReport)
async def upload_contacts(
    file: UploadFile = File(...),
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Bulk upload contacts from CSV/XLSX file
    
    Required columns: phone_number, segment, preferred_language
    Optional columns: name, customer_id, notes, tags
    
    Returns import report with success/failure details
    """
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported"
        )
    
    # Read file
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
    
    # Validate required columns
    required_columns = ['phone_number', 'segment', 'preferred_language']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}"
        )
    
    total_rows = len(df)
    imported = 0
    updated = 0
    failed = 0
    failure_details = []
    
    # Batch-fetch all existing contacts for this jeweller to avoid N queries
    all_phone_numbers = [str(row['phone_number']).strip() for _, row in df.iterrows()]
    existing_contacts = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.phone_number.in_(all_phone_numbers)
    ).all()
    existing_map = {c.phone_number: c for c in existing_contacts}
    
    for idx, row in df.iterrows():
        try:
            phone_number = str(row['phone_number']).strip()
            segment = row['segment'].upper()
            language = row['preferred_language'].lower()
            
            # Validate enum values
            if segment not in [s.value for s in SegmentType]:
                raise ValueError(f"Invalid segment: {segment}")
            if language not in [l.value for l in Language]:
                raise ValueError(f"Invalid language: {language}")
            
            # Look up from pre-fetched map instead of individual query
            existing = existing_map.get(phone_number)
            
            if existing:
                # Update existing contact
                existing.segment = SegmentType(segment)
                existing.preferred_language = Language(language)
                existing.name = row.get('name')
                existing.customer_id = row.get('customer_id')
                existing.notes = row.get('notes')
                existing.tags = row.get('tags')
                existing.updated_at = now_utc()
                updated += 1
            else:
                # Create new contact
                new_contact = Contact(
                    jeweller_id=current_jeweller.id,
                    phone_number=phone_number,
                    segment=SegmentType(segment),
                    preferred_language=Language(language),
                    name=row.get('name'),
                    customer_id=row.get('customer_id'),
                    notes=row.get('notes'),
                    tags=row.get('tags')
                )
                db.add(new_contact)
                imported += 1
        
        except Exception as e:
            failed += 1
            failure_details.append({
                "row": idx + 2,  # Excel row number (1-indexed + header)
                "phone": str(row.get('phone_number', 'N/A')),
                "reason": str(e)
            })
    
    db.commit()
    
    return ContactImportReport(
        total_rows=total_rows,
        imported=imported,
        updated=updated,
        failed=failed,
        failure_details=failure_details
    )


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    request: ContactCreate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Create single contact (for mobile selection feature)"""
    # Check if contact exists
    existing = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.phone_number == request.phone_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact with this phone number already exists"
        )
    
    new_contact = Contact(
        jeweller_id=current_jeweller.id,
        **request.model_dump()
    )
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    return new_contact


@router.get("/", response_model=ContactListResponse)
def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    segment: Optional[SegmentType] = None,
    opted_out: Optional[bool] = None,
    search: Optional[str] = None,
    payment_day: Optional[int] = Query(None, ge=1, le=31, description="Filter by SIP or Loan payment day"),
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """List contacts with pagination and filters"""
    query = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    )
    
    # Apply filters
    if segment:
        query = query.filter(Contact.segment == segment)
    if opted_out is not None:
        query = query.filter(Contact.opted_out == opted_out)
    if search:
        query = query.filter(
            (Contact.name.ilike(f"%{search}%")) |
            (Contact.phone_number.ilike(f"%{search}%"))
        )
    if payment_day is not None:
        query = query.filter(
            (Contact.sip_payment_day == payment_day) |
            (Contact.loan_payment_day == payment_day)
        )
    
    # Get total count
    total = query.count()
    
    # Paginate
    contacts = query.offset((page - 1) * page_size).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return ContactListResponse(
        contacts=contacts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=List[ContactSegmentStats])
def get_contact_stats(
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get contact distribution by segment"""
    stats = db.query(
        Contact.segment,
        func.count(Contact.id).label('count'),
        func.sum(func.cast(Contact.opted_out, Integer)).label('opted_out_count')
    ).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).group_by(Contact.segment).all()
    
    return [
        ContactSegmentStats(
            segment=stat.segment,
            count=stat.count,
            opted_out_count=stat.opted_out_count or 0
        )
        for stat in stats
    ]


@router.post("/bulk-delete", response_model=ContactBulkDeleteResponse)
def bulk_delete_contacts(
    request: ContactBulkDelete,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Bulk soft-delete contacts.
    Only deletes contacts that belong to the current jeweller.
    """
    contacts = db.query(Contact).filter(
        Contact.id.in_(request.contact_ids),
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).all()

    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching contacts found to delete"
        )

    now = now_utc()
    for contact in contacts:
        contact.is_deleted = True
        contact.deleted_at = now

    db.commit()

    return ContactBulkDeleteResponse(
        deleted_count=len(contacts),
        message=f"Successfully deleted {len(contacts)} contact(s)"
    )


@router.post("/bulk-update", response_model=BulkContactUpdateResponse)
def bulk_update_contacts(
    request: BulkContactUpdateRequest,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Bulk update contacts — change segment and/or payment schedule for multiple contacts at once.
    Only fields that are explicitly provided are changed; omitted fields are left as-is.
    Use clear_sip_schedule / clear_loan_schedule to explicitly remove payment schedules.
    """
    contacts = db.query(Contact).filter(
        Contact.id.in_(request.contact_ids),
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).all()

    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching contacts found to update"
        )

    updated = 0
    failed = 0
    failure_details = []

    for contact in contacts:
        try:
            # 1. Apply segment change first (if provided)
            effective_segment = contact.segment
            if request.segment is not None:
                contact.segment = request.segment
                effective_segment = request.segment

                # Clear incompatible schedules when segment changes
                can_sip = effective_segment in (SegmentType.GOLD_SIP, SegmentType.BOTH)
                can_loan = effective_segment in (SegmentType.GOLD_LOAN, SegmentType.BOTH)
                if not can_sip:
                    contact.sip_payment_day = None
                    contact.last_sip_reminder_sent_at = None
                if not can_loan:
                    contact.loan_payment_day = None
                    contact.last_loan_reminder_sent_at = None

            # 2. Clear schedules if explicitly requested
            if request.clear_sip_schedule:
                contact.sip_payment_day = None
                contact.last_sip_reminder_sent_at = None
            if request.clear_loan_schedule:
                contact.loan_payment_day = None
                contact.last_loan_reminder_sent_at = None

            # 3. Apply payment schedule updates (only if not clearing)
            can_sip = effective_segment in (SegmentType.GOLD_SIP, SegmentType.BOTH)
            can_loan = effective_segment in (SegmentType.GOLD_LOAN, SegmentType.BOTH)

            if request.sip_payment_day is not None and not request.clear_sip_schedule:
                if not can_sip:
                    raise ValueError("SIP schedule requires GOLD_SIP or BOTH segment")
                contact.sip_payment_day = request.sip_payment_day

            if request.sip_reminder_days_before is not None and not request.clear_sip_schedule:
                if can_sip:
                    contact.sip_reminder_days_before = request.sip_reminder_days_before

            if request.loan_payment_day is not None and not request.clear_loan_schedule:
                if not can_loan:
                    raise ValueError("Loan schedule requires GOLD_LOAN or BOTH segment")
                contact.loan_payment_day = request.loan_payment_day

            if request.loan_reminder_days_before is not None and not request.clear_loan_schedule:
                if can_loan:
                    contact.loan_reminder_days_before = request.loan_reminder_days_before

            contact.updated_at = now_utc()
            updated += 1

        except Exception as e:
            failed += 1
            failure_details.append({
                "contact_id": contact.id,
                "reason": str(e)
            })

    if updated > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

    return BulkContactUpdateResponse(
        updated=updated,
        failed=failed,
        failure_details=failure_details,
        message=f"Updated {updated} contact(s), {failed} failed"
    )


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get single contact by ID"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    return contact


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    request: ContactUpdate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Update contact details"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    contact.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contact)
    
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Soft delete contact"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    contact.is_deleted = True
    contact.deleted_at = now_utc()
    db.commit()
    
    return None


# ============ Payment Schedule Endpoints ============


@router.put("/{contact_id}/payment-schedule", response_model=ContactResponse)
def update_payment_schedule(
    contact_id: int,
    request: PaymentScheduleUpdate,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Update SIP/Loan payment schedule for a single contact.
    Set sip_payment_day / loan_payment_day to null to clear the schedule
    (no reminder will be sent for that type).
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Validate: SIP schedule only for SIP / BOTH contacts
    if request.sip_payment_day is not None and contact.segment not in (
        SegmentType.GOLD_SIP, SegmentType.BOTH
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SIP payment schedule can only be set for GOLD_SIP or BOTH contacts"
        )

    # Validate: Loan schedule only for LOAN / BOTH contacts
    if request.loan_payment_day is not None and contact.segment not in (
        SegmentType.GOLD_LOAN, SegmentType.BOTH
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan payment schedule can only be set for GOLD_LOAN or BOTH contacts"
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    contact.updated_at = now_utc()
    db.commit()
    db.refresh(contact)

    return contact


@router.delete("/{contact_id}/payment-schedule", response_model=ContactResponse)
def clear_payment_schedule(
    contact_id: int,
    request: PaymentScheduleClear,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Clear SIP and/or Loan payment schedule for a contact.
    After clearing, no reminders will be sent for the cleared type(s).
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    if request.clear_sip:
        contact.sip_payment_day = None
        contact.last_sip_reminder_sent_at = None
    if request.clear_loan:
        contact.loan_payment_day = None
        contact.last_loan_reminder_sent_at = None

    contact.updated_at = now_utc()
    db.commit()
    db.refresh(contact)

    return contact


@router.post("/bulk-payment-schedule", response_model=BulkPaymentScheduleResponse)
def bulk_update_payment_schedule(
    request: BulkPaymentScheduleRequest,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Bulk update payment schedules for multiple contacts.
    Only contacts belonging to the current jeweller are updated.
    """
    updated = 0
    failed = 0
    failure_details = []

    for item in request.schedules:
        try:
            contact = db.query(Contact).filter(
                Contact.id == item.contact_id,
                Contact.jeweller_id == current_jeweller.id,
                Contact.is_deleted == False
            ).first()

            if not contact:
                raise ValueError("Contact not found")

            # Validate segment compatibility
            if item.sip_payment_day is not None and contact.segment not in (
                SegmentType.GOLD_SIP, SegmentType.BOTH
            ):
                raise ValueError("SIP schedule requires GOLD_SIP or BOTH segment")
            if item.loan_payment_day is not None and contact.segment not in (
                SegmentType.GOLD_LOAN, SegmentType.BOTH
            ):
                raise ValueError("Loan schedule requires GOLD_LOAN or BOTH segment")

            data = item.model_dump(exclude={"contact_id"}, exclude_unset=True)
            for field, value in data.items():
                setattr(contact, field, value)

            contact.updated_at = now_utc()
            updated += 1

        except Exception as e:
            failed += 1
            failure_details.append({
                "contact_id": item.contact_id,
                "reason": str(e)
            })

    if updated > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

    return BulkPaymentScheduleResponse(
        updated=updated,
        failed=failed,
        failure_details=failure_details,
        message=f"Updated {updated} schedule(s), {failed} failed"
    )


@router.get("/payment-schedules", response_model=PaymentScheduleListResponse)
def list_payment_schedules(
    schedule_type: Optional[str] = Query(None, regex="^(sip|loan|all)$", description="Filter by schedule type"),
    has_schedule: Optional[bool] = Query(None, description="True = only scheduled, False = only unscheduled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    List contacts with their payment schedule information.
    Filterable by schedule type and whether a schedule is set.
    """
    query = db.query(Contact).filter(
        Contact.jeweller_id == current_jeweller.id,
        Contact.is_deleted == False,
        Contact.opted_out == False,
    )

    # Filter by segment that can have schedules
    if schedule_type == "sip":
        query = query.filter(Contact.segment.in_([SegmentType.GOLD_SIP, SegmentType.BOTH]))
        if has_schedule is True:
            query = query.filter(Contact.sip_payment_day.isnot(None))
        elif has_schedule is False:
            query = query.filter(Contact.sip_payment_day.is_(None))
    elif schedule_type == "loan":
        query = query.filter(Contact.segment.in_([SegmentType.GOLD_LOAN, SegmentType.BOTH]))
        if has_schedule is True:
            query = query.filter(Contact.loan_payment_day.isnot(None))
        elif has_schedule is False:
            query = query.filter(Contact.loan_payment_day.is_(None))
    else:
        # "all" or unfiltered — show any contact that has at least one schedule
        if has_schedule is True:
            query = query.filter(
                (Contact.sip_payment_day.isnot(None)) | (Contact.loan_payment_day.isnot(None))
            )
        elif has_schedule is False:
            query = query.filter(
                Contact.sip_payment_day.is_(None),
                Contact.loan_payment_day.is_(None)
            )

    total = query.count()
    contacts = query.order_by(Contact.name).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size

    return PaymentScheduleListResponse(
        contacts=[
            PaymentScheduleResponse(
                contact_id=c.id,
                name=c.name,
                phone_number=c.phone_number,
                segment=c.segment,
                sip_payment_day=c.sip_payment_day,
                loan_payment_day=c.loan_payment_day,
                sip_reminder_days_before=c.sip_reminder_days_before,
                loan_reminder_days_before=c.loan_reminder_days_before,
                last_sip_reminder_sent_at=c.last_sip_reminder_sent_at,
                last_loan_reminder_sent_at=c.last_loan_reminder_sent_at,
            )
            for c in contacts
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/reminder-preview", response_model=ReminderPreviewResponse)
def preview_upcoming_reminders(
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    Preview which contacts will receive payment reminders today/tomorrow.
    Helps jewellers see what messages are about to go out.
    """
    from datetime import timedelta
    import calendar

    now = now_utc() + timedelta(hours=5, minutes=30)  # IST
    today = now.date()

    def _contacts_due_for(reminder_type: str):
        """Return contacts whose reminder should fire today."""
        results = []
        if reminder_type == "sip":
            contacts = db.query(Contact).filter(
                Contact.jeweller_id == current_jeweller.id,
                Contact.is_deleted == False,
                Contact.opted_out == False,
                Contact.segment.in_([SegmentType.GOLD_SIP, SegmentType.BOTH]),
                Contact.sip_payment_day.isnot(None),
            ).all()
            for c in contacts:
                days_before = c.sip_reminder_days_before or 3
                # Calculate reminder date for this month
                year, month = today.year, today.month
                last_day = calendar.monthrange(year, month)[1]
                payment_day = min(c.sip_payment_day, last_day)
                from datetime import date as date_cls
                reminder_date = date_cls(year, month, payment_day) - timedelta(days=days_before)
                if reminder_date == today:
                    results.append(c)
        elif reminder_type == "loan":
            contacts = db.query(Contact).filter(
                Contact.jeweller_id == current_jeweller.id,
                Contact.is_deleted == False,
                Contact.opted_out == False,
                Contact.segment.in_([SegmentType.GOLD_LOAN, SegmentType.BOTH]),
                Contact.loan_payment_day.isnot(None),
            ).all()
            for c in contacts:
                days_before = c.loan_reminder_days_before or 3
                year, month = today.year, today.month
                last_day = calendar.monthrange(year, month)[1]
                payment_day = min(c.loan_payment_day, last_day)
                from datetime import date as date_cls
                reminder_date = date_cls(year, month, payment_day) - timedelta(days=days_before)
                if reminder_date == today:
                    results.append(c)
        return results

    sip_due = _contacts_due_for("sip")
    loan_due = _contacts_due_for("loan")

    def _to_response(c):
        return PaymentScheduleResponse(
            contact_id=c.id,
            name=c.name,
            phone_number=c.phone_number,
            segment=c.segment,
            sip_payment_day=c.sip_payment_day,
            loan_payment_day=c.loan_payment_day,
            sip_reminder_days_before=c.sip_reminder_days_before,
            loan_reminder_days_before=c.loan_reminder_days_before,
            last_sip_reminder_sent_at=c.last_sip_reminder_sent_at,
            last_loan_reminder_sent_at=c.last_loan_reminder_sent_at,
        )

    return ReminderPreviewResponse(
        sip_reminders_due_today=len(sip_due),
        loan_reminders_due_today=len(loan_due),
        sip_contacts=[_to_response(c) for c in sip_due],
        loan_contacts=[_to_response(c) for c in loan_due],
    )
