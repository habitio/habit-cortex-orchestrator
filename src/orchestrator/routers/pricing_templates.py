"""
Pricing Templates Router.

Provides CRUD endpoints for managing pricing calculation templates.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.session import get_db
from ..database.models import PricingTemplate, Product
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["pricing-templates"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTHENTICATED ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/products/{product_id}/pricing-templates")
async def list_pricing_templates(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    is_active: Optional[bool] = None,
    strategy: Optional[str] = None
):
    """
    List all pricing templates for a product.
    
    Query parameters:
    - is_active: Filter by active status
    - strategy: Filter by strategy name
    """
    # Verify product exists
    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Build query
    query = select(PricingTemplate).where(PricingTemplate.product_id == product_id)
    
    if is_active is not None:
        query = query.where(PricingTemplate.is_active == is_active)
    
    if strategy:
        query = query.where(PricingTemplate.strategy == strategy)
    
    query = query.order_by(PricingTemplate.name)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return {
        "templates": [template.to_dict() for template in templates],
        "total": len(templates)
    }


@router.get("/products/{product_id}/pricing-templates/{template_id}")
async def get_pricing_template(
    product_id: int,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific pricing template by ID."""
    result = await db.execute(
        select(PricingTemplate).where(
            PricingTemplate.id == template_id,
            PricingTemplate.product_id == product_id
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing template not found")
    
    return template.to_dict()


@router.post("/products/{product_id}/pricing-templates", status_code=status.HTTP_201_CREATED)
async def create_pricing_template(
    product_id: int,
    name: str,
    strategy: str,
    strategy_config: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    description: Optional[str] = None,
    strategy_version: str = "1.0.0",
    is_active: bool = True,
    distributor_id: Optional[str] = None
):
    """
    Create a new pricing template.
    
    Body parameters:
    - name: Human-friendly name
    - strategy: Strategy identifier (e.g., "simple_percentage")
    - strategy_config: Strategy-specific configuration JSON
    - description: Optional description
    - strategy_version: Version of the strategy (default: "1.0.0")
    - is_active: Whether template is active (default: true)
    - distributor_id: Optional distributor override
    """
    # Verify product exists
    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Create template
    template = PricingTemplate(
        product_id=product_id,
        name=name,
        description=description,
        strategy=strategy,
        strategy_version=strategy_version,
        strategy_config=strategy_config,
        is_active=is_active,
        distributor_id=distributor_id
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    logger.info(f"Created pricing template: {template.name} (ID: {template.id}) for product {product_id}")
    
    return template.to_dict()


@router.put("/products/{product_id}/pricing-templates/{template_id}")
async def update_pricing_template(
    product_id: int,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    name: Optional[str] = None,
    description: Optional[str] = None,
    strategy: Optional[str] = None,
    strategy_version: Optional[str] = None,
    strategy_config: Optional[dict] = None,
    is_active: Optional[bool] = None,
    distributor_id: Optional[str] = None
):
    """
    Update an existing pricing template.
    
    Only provided fields will be updated.
    """
    result = await db.execute(
        select(PricingTemplate).where(
            PricingTemplate.id == template_id,
            PricingTemplate.product_id == product_id
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing template not found")
    
    # Update fields
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if strategy is not None:
        template.strategy = strategy
    if strategy_version is not None:
        template.strategy_version = strategy_version
    if strategy_config is not None:
        template.strategy_config = strategy_config
    if is_active is not None:
        template.is_active = is_active
    if distributor_id is not None:
        template.distributor_id = distributor_id
    
    await db.commit()
    await db.refresh(template)
    
    logger.info(f"Updated pricing template: {template.name} (ID: {template.id})")
    
    return template.to_dict()


@router.delete("/products/{product_id}/pricing-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing_template(
    product_id: int,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a pricing template.
    
    WARNING: This will break workflows that reference this template.
    Consider setting is_active=false instead.
    """
    result = await db.execute(
        select(PricingTemplate).where(
            PricingTemplate.id == template_id,
            PricingTemplate.product_id == product_id
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing template not found")
    
    await db.delete(template)
    await db.commit()
    
    logger.info(f"Deleted pricing template: {template.name} (ID: {template.id})")
    
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC ENDPOINTS (for instances)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/public/products/{product_id}/pricing-templates/{template_id}")
async def get_pricing_template_public(
    product_id: int,
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific pricing template (public endpoint for instances).
    
    This endpoint is called by product instances to fetch pricing templates
    during workflow execution.
    """
    result = await db.execute(
        select(PricingTemplate).where(
            PricingTemplate.id == template_id,
            PricingTemplate.product_id == product_id,
            PricingTemplate.is_active == True
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing template not found or inactive")
    
    return template.to_dict()


@router.get("/public/products/{product_id}/pricing-templates")
async def list_pricing_templates_public(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    strategy: Optional[str] = None
):
    """
    List active pricing templates (public endpoint for instances).
    
    Query parameters:
    - strategy: Filter by strategy name
    """
    query = select(PricingTemplate).where(
        PricingTemplate.product_id == product_id,
        PricingTemplate.is_active == True
    )
    
    if strategy:
        query = query.where(PricingTemplate.strategy == strategy)
    
    query = query.order_by(PricingTemplate.name)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return {
        "templates": [template.to_dict() for template in templates],
        "total": len(templates)
    }
