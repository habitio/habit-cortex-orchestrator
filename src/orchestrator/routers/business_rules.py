"""Business rules management API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.database import get_db
from orchestrator.database.models import BusinessRule, Product, UserSession
from orchestrator.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["business-rules"])


class BusinessRuleCreate(BaseModel):
    """Schema for creating a business rule."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-friendly rule name")
    description: str | None = Field(None, description="Optional description")
    rule_type: str = Field(default="field_validation", description="Type of rule")
    rule_definition: dict[str, Any] = Field(..., description="Rule validation logic")
    stage: str = Field(..., description="Execution stage (e.g., quote_simulate)")
    is_active: bool = Field(default=True, description="Whether rule is active")
    distributor_id: str | None = Field(None, description="Optional distributor override")
    priority: int = Field(default=100, description="Execution priority (lower = first)")


class BusinessRuleUpdate(BaseModel):
    """Schema for updating a business rule."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    rule_type: str | None = None
    rule_definition: dict[str, Any] | None = None
    stage: str | None = None
    is_active: bool | None = None
    distributor_id: str | None = None
    priority: int | None = None


@router.get("/products/{product_id}/rules")
def list_business_rules(
    product_id: int,
    stage: str | None = None,
    rule_type: str | None = None,
    distributor_id: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List all business rules for a product.
    
    Query parameters:
    - stage: Filter by execution stage (quote_simulate, quote_checkout, etc.)
    - rule_type: Filter by rule type (field_validation, etc.)
    - distributor_id: Filter by distributor override
    - include_inactive: Include inactive rules (default: false)
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Build query
    query = db.query(BusinessRule).filter(BusinessRule.product_id == product_id)
    
    if stage:
        query = query.filter(BusinessRule.stage == stage)
    
    if rule_type:
        query = query.filter(BusinessRule.rule_type == rule_type)
    
    if distributor_id is not None:
        query = query.filter(BusinessRule.distributor_id == distributor_id)
    
    if not include_inactive:
        query = query.filter(BusinessRule.is_active == True)
    
    # Order by priority and name
    query = query.order_by(BusinessRule.priority, BusinessRule.name)
    
    rules = query.all()
    
    return {
        "product_id": product_id,
        "product_name": product.name,
        "total": len(rules),
        "rules": [rule.to_dict() for rule in rules],
    }


@router.post("/products/{product_id}/rules")
def create_business_rule(
    product_id: int,
    rule: BusinessRuleCreate,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new business rule for a product."""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Create new rule
    new_rule = BusinessRule(
        product_id=product_id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        rule_definition=rule.rule_definition,
        stage=rule.stage,
        is_active=rule.is_active,
        distributor_id=rule.distributor_id,
        priority=rule.priority,
    )
    
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    
    return {
        "message": "Business rule created successfully",
        "rule": new_rule.to_dict(),
    }


@router.get("/rules/{rule_id}")
def get_business_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific business rule by ID."""
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    
    return rule.to_dict()


@router.put("/rules/{rule_id}")
def update_business_rule(
    rule_id: int,
    updates: BusinessRuleUpdate,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a business rule."""
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    return {
        "message": "Business rule updated successfully",
        "rule": rule.to_dict(),
    }


@router.delete("/rules/{rule_id}")
def delete_business_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a business rule."""
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    
    rule_name = rule.name
    product_id = rule.product_id
    
    db.delete(rule)
    db.commit()
    
    return {
        "message": f"Business rule '{rule_name}' deleted successfully",
        "product_id": product_id,
        "deleted_rule_id": rule_id,
    }


@router.get("/products/{product_id}/rules/by-ids")
def get_business_rules_by_ids(
    product_id: int,
    rule_ids: str,  # Comma-separated list of IDs
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get multiple business rules by IDs.
    
    This endpoint is used by workflow steps to fetch specific rules.
    Query parameter: rule_ids=1,2,3
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Parse rule IDs
    try:
        ids = [int(id.strip()) for id in rule_ids.split(",") if id.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_ids format. Use comma-separated integers.")
    
    # Fetch rules
    rules = db.query(BusinessRule).filter(
        BusinessRule.id.in_(ids),
        BusinessRule.product_id == product_id,
    ).order_by(BusinessRule.priority).all()
    
    # Check for missing rules
    found_ids = {rule.id for rule in rules}
    missing_ids = set(ids) - found_ids
    
    return {
        "product_id": product_id,
        "requested_ids": ids,
        "found": len(rules),
        "missing_ids": list(missing_ids) if missing_ids else [],
        "rules": [rule.to_dict() for rule in rules],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC ENDPOINTS (for instances using shared key auth)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from orchestrator.routers.instance_api import verify_shared_key

@router.get("/public/products/{product_id}/rules/by-ids")
def get_business_rules_by_ids_public(
    product_id: int,
    rule_ids: str,
    x_cortex_shared_key: str = Header(None, alias="X-Cortex-Shared-Key"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Public endpoint for instances to fetch rules using shared key.
    
    Used by workflow steps during quote processing.
    Query parameter: rule_ids=1,2,3
    Header: X-Cortex-Shared-Key
    """
    # Verify shared key using the official dependency
    product = verify_shared_key(product_id, x_cortex_shared_key, db)
    
    # Parse rule IDs
    try:
        ids = [int(id.strip()) for id in rule_ids.split(",") if id.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_ids format")
    
    # Fetch rules
    rules = db.query(BusinessRule).filter(
        BusinessRule.id.in_(ids),
        BusinessRule.product_id == product_id,
    ).order_by(BusinessRule.priority).all()
    
    return {
        "product_id": product_id,
        "rules": [rule.to_dict() for rule in rules],
    }
