from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.core.dependencies import get_current_jeweller
from app.models.jeweller import Jeweller
from app.models.contact import Contact
from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactResponse,
    ContactListResponse, ContactImportReport, ContactSegmentStats
)
from app.utils.enums import SegmentType, Language
import pandas as pd
import io
from datetime import datetime

router = APIRouter(prefix="/contacts", tags=["Contacts"])


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
            
            # Check if contact exists
            existing = db.query(Contact).filter(
                Contact.jeweller_id == current_jeweller.id,
                Contact.phone_number == phone_number
            ).first()
            
            if existing:
                # Update existing contact
                existing.segment = SegmentType(segment)
                existing.preferred_language = Language(language)
                existing.name = row.get('name')
                existing.customer_id = row.get('customer_id')
                existing.notes = row.get('notes')
                existing.tags = row.get('tags')
                existing.updated_at = datetime.utcnow()
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
    contact.deleted_at = datetime.utcnow()
    db.commit()
    
    return None
