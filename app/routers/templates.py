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
from app.services.template_service import TemplateService
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


# ============ WhatsApp Template Sync Endpoints ============

@router.post("/admin/{template_id}/sync-to-whatsapp")
async def sync_template_to_whatsapp(
    template_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Create/sync template to WhatsApp Business Account
    This submits the template for WhatsApp approval
    """
    template_service = TemplateService(db)
    result = await template_service.create_template_in_whatsapp(template_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create template in WhatsApp")
        )
    
    return result


@router.get("/admin/{template_id}/whatsapp-status")
async def get_template_whatsapp_status(
    template_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Get WhatsApp approval status for a template
    """
    template_service = TemplateService(db)
    result = await template_service.get_template_status(template_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to get template status")
        )
    
    return result


@router.post("/admin/sync-from-whatsapp")
async def sync_templates_from_whatsapp(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Sync all templates from WhatsApp Business Account
    Updates local template approval statuses
    """
    template_service = TemplateService(db)
    result = await template_service.sync_templates_from_whatsapp()
    
    return result


@router.delete("/admin/{template_id}/whatsapp")
async def delete_template_from_whatsapp(
    template_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Delete template from WhatsApp Business Account
    """
    template_service = TemplateService(db)
    result = await template_service.delete_template_from_whatsapp(template_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to delete template from WhatsApp")
        )
    
    return result


@router.get("/admin/whatsapp-templates")
async def list_whatsapp_templates(
    limit: int = 100,
    status_filter: str = None,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: List all templates directly from WhatsApp Business Account
    """
    from app.utils.whatsapp import get_whatsapp_templates
    
    templates = await get_whatsapp_templates(
        limit=limit,
        status_filter=status_filter
    )
    
    return {
        "templates": templates,
        "total": len(templates)
    }
