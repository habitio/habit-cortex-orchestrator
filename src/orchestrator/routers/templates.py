"""
Templates API endpoints.

Manages three types of templates for product instances:
1. Email Templates - Custom email builder with subject and HTML body
2. ListMonk Templates - References to external ListMonk template IDs  
3. SMS Templates - Direct message storage with variable placeholders
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.database import get_db, EmailTemplate, ListMonkTemplate, SMSTemplate, Product
from orchestrator.database.models import UserSession
from orchestrator.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products/{product_id}/templates", tags=["templates"])


# Pydantic schemas

# Custom Email Templates
class EmailTemplateCreate(BaseModel):
    """Request model for creating a custom email template."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-friendly template name")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject line")
    body_html: str = Field(..., min_length=1, description="HTML email body")
    body_text: Optional[str] = Field(None, description="Plain text fallback")
    description: Optional[str] = Field(None, description="Template description")
    template_type: str = Field(default="transactional", description="Template category")
    available_variables: list[str] = Field(default=[], description="Available template variables")


class EmailTemplateUpdate(BaseModel):
    """Request model for updating a custom email template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    body_html: Optional[str] = Field(None, min_length=1)
    body_text: Optional[str] = None
    description: Optional[str] = None
    template_type: Optional[str] = None
    available_variables: Optional[list[str]] = None


# ListMonk Templates
class ListMonkTemplateCreate(BaseModel):
    """Request model for creating a ListMonk template reference."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-friendly template name")
    listmonk_template_id: int = Field(..., gt=0, description="ListMonk template ID")
    description: Optional[str] = Field(None, description="Template description")
    template_type: str = Field(default="transactional", description="Template category")
    available_variables: list[str] = Field(default=[], description="Available template variables")


class ListMonkTemplateUpdate(BaseModel):
    """Request model for updating a ListMonk template reference."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    listmonk_template_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    template_type: Optional[str] = None
    available_variables: Optional[list[str]] = None


# SMS Templates
class SMSTemplateCreate(BaseModel):
    """Request model for creating an SMS template."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-friendly template name")
    message: str = Field(..., min_length=1, description="SMS message content with {{variables}}")
    description: Optional[str] = Field(None, description="Template description")
    template_type: str = Field(default="transactional", description="Template category")
    available_variables: list[str] = Field(default=[], description="Available template variables")


class SMSTemplateUpdate(BaseModel):
    """Request model for updating an SMS template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    message: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    template_type: Optional[str] = None
    available_variables: Optional[list[str]] = None


# Helper functions
def get_product_or_404(db: Session, product_id: int) -> Product:
    """Get product by ID or raise 404."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    return product


def extract_variables_from_html(html: str) -> list[str]:
    """Extract {{variable}} placeholders from HTML content."""
    pattern = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}'
    return list(set(re.findall(pattern, html)))


# ===== EMAIL TEMPLATES =====

@router.get("/email")
async def list_email_templates(
    product_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all email templates for a product.
    
    Returns templates ordered by name.
    """
    # Verify product exists
    get_product_or_404(db, product_id)
    
    templates = db.query(EmailTemplate)\
        .filter(EmailTemplate.product_id == product_id)\
        .order_by(EmailTemplate.name)\
        .all()
    
    return [template.to_dict() for template in templates]


@router.post("/email", status_code=status.HTTP_201_CREATED)
async def create_email_template(
    product_id: int,
    template_data: EmailTemplateCreate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new custom email template.
    
    Template name must be unique within the product.
    Automatically extracts variables from subject and body.
    """
    # Verify product exists
    get_product_or_404(db, product_id)
    
    # Check for duplicate name
    existing = db.query(EmailTemplate)\
        .filter(
            EmailTemplate.product_id == product_id,
            EmailTemplate.name == template_data.name
        )\
        .first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email template '{template_data.name}' already exists for this product"
        )
    
    # Auto-detect variables from content if not provided
    if not template_data.available_variables:
        subject_vars = extract_variables_from_html(template_data.subject)
        body_vars = extract_variables_from_html(template_data.body_html)
        template_data.available_variables = list(set(subject_vars + body_vars))
    
    # Create template
    template = EmailTemplate(
        product_id=product_id,
        name=template_data.name,
        subject=template_data.subject,
        body_html=template_data.body_html,
        body_text=template_data.body_text,
        description=template_data.description,
        template_type=template_data.template_type,
        available_variables=template_data.available_variables
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Created custom email template '{template.name}' for product {product_id}")
    
    return template.to_dict()


@router.get("/email/{template_id}")
async def get_email_template(
    product_id: int,
    template_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single email template by ID."""
    # Verify product exists
    get_product_or_404(db, product_id)
    
    template = db.query(EmailTemplate)\
        .filter(
            EmailTemplate.id == template_id,
            EmailTemplate.product_id == product_id
        )\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email template {template_id} not found"
        )
    
    return template.to_dict()


@router.put("/email/{template_id}")
async def update_email_template(
    product_id: int,
    template_id: int,
    template_data: EmailTemplateUpdate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an email template."""
    # Verify product exists
    get_product_or_404(db, product_id)
    
    template = db.query(EmailTemplate)\
        .filter(
            EmailTemplate.id == template_id,
            EmailTemplate.product_id == product_id
        )\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email template {template_id} not found"
        )
    
    # Check for duplicate name if changing name
    if template_data.name and template_data.name != template.name:
        existing = db.query(EmailTemplate)\
            .filter(
                EmailTemplate.product_id == product_id,
                EmailTemplate.name == template_data.name,
                EmailTemplate.id != template_id
            )\
            .first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email template '{template_data.name}' already exists"
            )
    
    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.listmonk_template_id is not None:
        template.listmonk_template_id = template_data.listmonk_template_id
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.template_type is not None:
        template.template_type = template_data.template_type
    if template_data.available_variables is not None:
        template.available_variables = template_data.available_variables
    
    db.commit()
    db.refresh(template)
    
    logger.info(f"Updated email template {template_id} for product {product_id}")
    
    return template.to_dict()


@router.delete("/email/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_template(
    product_id: int,
    template_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an email template."""
    # Verify product exists
    get_product_or_404(db, product_id)
    
    template = db.query(EmailTemplate)\
        .filter(
            EmailTemplate.id == template_id,
            EmailTemplate.product_id == product_id
        )\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email template {template_id} not found"
        )
    
    db.delete(template)
    db.commit()
    
    logger.info(f"Deleted custom email template {template_id} from product {product_id}")


# ===== LISTMONK TEMPLATES =====

@router.get("/listmonk")
async def list_listmonk_templates(
    product_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all ListMonk template references for a product.
    
    Returns templates ordered by name.
    """
    get_product_or_404(db, product_id)
    
    templates = db.query(ListMonkTemplate)\
        .filter(ListMonkTemplate.product_id == product_id)\
        .order_by(ListMonkTemplate.name)\
        .all()
    
    return [template.to_dict() for template in templates]


@router.post("/listmonk", status_code=status.HTTP_201_CREATED)
async def create_listmonk_template(
    product_id: int,
    template_data: ListMonkTemplateCreate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new ListMonk template reference.
    
    Template name must be unique within the product.
    """
    get_product_or_404(db, product_id)
    
    # Check for duplicate name
    existing = db.query(ListMonkTemplate)\
        .filter(ListMonkTemplate.product_id == product_id, ListMonkTemplate.name == template_data.name)\
        .first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ListMonk template '{template_data.name}' already exists for this product"
        )
    
    template = ListMonkTemplate(
        product_id=product_id,
        name=template_data.name,
        listmonk_template_id=template_data.listmonk_template_id,
        description=template_data.description,
        template_type=template_data.template_type,
        available_variables=template_data.available_variables,
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Created ListMonk template '{template.name}' for product {product_id}")
    return template.to_dict()


@router.get("/listmonk/{template_id}")
async def get_listmonk_template(
    product_id: int,
    template_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single ListMonk template reference by ID."""
    get_product_or_404(db, product_id)
    
    template = db.query(ListMonkTemplate)\
        .filter(ListMonkTemplate.id == template_id, ListMonkTemplate.product_id == product_id)\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ListMonk template {template_id} not found"
        )
    
    return template.to_dict()


@router.put("/listmonk/{template_id}")
async def update_listmonk_template(
    product_id: int,
    template_id: int,
    updates: ListMonkTemplateUpdate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a ListMonk template reference."""
    get_product_or_404(db, product_id)
    
    template = db.query(ListMonkTemplate)\
        .filter(ListMonkTemplate.id == template_id, ListMonkTemplate.product_id == product_id)\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ListMonk template {template_id} not found"
        )
    
    # Check for duplicate name if changing name
    if updates.name and updates.name != template.name:
        existing = db.query(ListMonkTemplate)\
            .filter(ListMonkTemplate.product_id == product_id, ListMonkTemplate.name == updates.name)\
            .first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"ListMonk template '{updates.name}' already exists for this product"
            )
    
    # Update fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    logger.info(f"Updated ListMonk template {template_id} for product {product_id}")
    return template.to_dict()


@router.delete("/listmonk/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listmonk_template(
    product_id: int,
    template_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a ListMonk template reference."""
    get_product_or_404(db, product_id)
    
    template = db.query(ListMonkTemplate)\
        .filter(ListMonkTemplate.id == template_id, ListMonkTemplate.product_id == product_id)\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ListMonk template {template_id} not found"
        )
    
    db.delete(template)
    db.commit()
    
    logger.info(f"Deleted ListMonk template {template_id} for product {product_id}")
    return None


# ===== SMS TEMPLATES =====

@router.get("/sms")
async def list_sms_templates(
    product_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all SMS templates for a product.
    
    Returns templates ordered by name.
    """
    # Verify product exists
    get_product_or_404(db, product_id)
    
    templates = db.query(SMSTemplate)\
        .filter(SMSTemplate.product_id == product_id)\
        .order_by(SMSTemplate.name)\
        .all()
    
    return [template.to_dict() for template in templates]


@router.post("/sms", status_code=status.HTTP_201_CREATED)
async def create_sms_template(
    product_id: int,
    template_data: SMSTemplateCreate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new SMS template.
    
    SMS templates store message content with {{variable}} placeholders.
    """
    # Verify product exists
    get_product_or_404(db, product_id)
    
    # Check for duplicate name
    existing = db.query(SMSTemplate)\
        .filter(
            SMSTemplate.product_id == product_id,
            SMSTemplate.name == template_data.name
        )\
        .first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"SMS template '{template_data.name}' already exists for this product"
        )
    
    # Auto-detect variables if not provided
    if not template_data.available_variables:
        template_data.available_variables = extract_variables_from_html(template_data.message)
    
    # Calculate character count
    char_count = len(template_data.message)
    
    # Create template
    template = SMSTemplate(
        product_id=product_id,
        name=template_data.name,
        message=template_data.message,
        description=template_data.description,
        template_type=template_data.template_type,
        available_variables=template_data.available_variables,
        char_count=char_count
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Created SMS template '{template.name}' for product {product_id}")
    
    return template.to_dict()


@router.get("/sms/{template_id}")
async def get_sms_template(
    product_id: int,
    template_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single SMS template by ID."""
    # Verify product exists
    get_product_or_404(db, product_id)
    
    template = db.query(SMSTemplate)\
        .filter(
            SMSTemplate.id == template_id,
            SMSTemplate.product_id == product_id
        )\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS template {template_id} not found"
        )
    
    return template.to_dict()


@router.put("/sms/{template_id}")
async def update_sms_template(
    product_id: int,
    template_id: int,
    template_data: SMSTemplateUpdate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an SMS template."""
    # Verify product exists
    get_product_or_404(db, product_id)
    
    template = db.query(SMSTemplate)\
        .filter(
            SMSTemplate.id == template_id,
            SMSTemplate.product_id == product_id
        )\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS template {template_id} not found"
        )
    
    # Check for duplicate name if changing name
    if template_data.name and template_data.name != template.name:
        existing = db.query(SMSTemplate)\
            .filter(
                SMSTemplate.product_id == product_id,
                SMSTemplate.name == template_data.name,
                SMSTemplate.id != template_id
            )\
            .first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SMS template '{template_data.name}' already exists"
            )
    
    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.message is not None:
        template.message = template_data.message
        template.char_count = len(template_data.message)
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.template_type is not None:
        template.template_type = template_data.template_type
    if template_data.available_variables is not None:
        template.available_variables = template_data.available_variables
    
    db.commit()
    db.refresh(template)
    
    logger.info(f"Updated SMS template {template_id} for product {product_id}")
    
    return template.to_dict()


@router.delete("/sms/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sms_template(
    product_id: int,
    template_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an SMS template."""
    # Verify product exists
    get_product_or_404(db, product_id)
    
    template = db.query(SMSTemplate)\
        .filter(
            SMSTemplate.id == template_id,
            SMSTemplate.product_id == product_id
        )\
        .first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS template {template_id} not found"
        )
    
    db.delete(template)
    db.commit()
    
    logger.info(f"Deleted SMS template {template_id} from product {product_id}")
