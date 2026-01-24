from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.core.dependencies import get_current_admin, get_current_jeweller
from app.models.jeweller import Jeweller
from app.models.template import Template, TemplateTranslation
from app.schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateResponse, TemplateListResponse
)
from app.utils.enums import CampaignType
from datetime import datetime

router = APIRouter(prefix="/templates", tags=["Templates"])


# ============ Jeweller Endpoints (Read-only) ============

@router.get("/", response_model=TemplateListResponse)
def list_templates_for_jeweller(
    campaign_type: CampaignType = None,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """
    List available templates for jeweller to use in campaigns
    Filtered by campaign type if provided
    """
    query = db.query(Template).filter(Template.is_active == True)
    
    if campaign_type:
        query = query.filter(Template.campaign_type == campaign_type)
    
    templates = query.all()
    
    return TemplateListResponse(
        templates=templates,
        total=len(templates)
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template_for_jeweller(
    template_id: int,
    current_jeweller: Jeweller = Depends(get_current_jeweller),
    db: Session = Depends(get_db)
):
    """Get template details"""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template


# ============ Admin Endpoints (Full CRUD) ============

@router.get("/admin/all", response_model=TemplateListResponse)
def list_all_templates_admin(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: List all templates including inactive"""
    templates = db.query(Template).all()
    return TemplateListResponse(
        templates=templates,
        total=len(templates)
    )


@router.post("/admin/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template_admin(
    request: TemplateCreate,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: Create new WhatsApp template"""
    # Check if template name exists
    existing = db.query(Template).filter(
        Template.template_name == request.template_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )
    
    # Create template
    variable_names_json = ",".join(request.variable_names) if request.variable_names else None
    
    new_template = Template(
        template_name=request.template_name,
        display_name=request.display_name,
        campaign_type=request.campaign_type,
        sub_segment=request.sub_segment,
        description=request.description,
        category=request.category,
        variable_count=request.variable_count,
        variable_names=variable_names_json,
        is_active=True
    )
    db.add(new_template)
    db.flush()  # Get template.id
    
    # Create translations
    for trans in request.translations:
        translation = TemplateTranslation(
            template_id=new_template.id,
            **trans.model_dump()
        )
        db.add(translation)
    
    db.commit()
    db.refresh(new_template)
    
    return new_template


@router.patch("/admin/{template_id}", response_model=TemplateResponse)
def update_template_admin(
    template_id: int,
    request: TemplateUpdate,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: Update template"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/admin/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template_admin(
    template_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: Delete template (soft delete - mark as inactive)"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    template.is_active = False
    template.updated_at = datetime.utcnow()
    db.commit()
    
    return None
