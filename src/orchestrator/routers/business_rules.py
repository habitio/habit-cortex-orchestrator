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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BULK OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class BulkEnableDisable(BaseModel):
    """Schema for bulk enable/disable operations."""
    rule_ids: list[int] = Field(..., description="List of rule IDs to update")
    is_active: bool = Field(..., description="New active status")


class BulkDelete(BaseModel):
    """Schema for bulk delete operations."""
    rule_ids: list[int] = Field(..., description="List of rule IDs to delete")


class BulkPriorityUpdate(BaseModel):
    """Schema for bulk priority updates."""
    updates: list[dict[str, int]] = Field(
        ..., 
        description="List of {rule_id: int, priority: int} mappings"
    )


@router.post("/products/{product_id}/rules/bulk/enable-disable")
def bulk_enable_disable_rules(
    product_id: int,
    operation: BulkEnableDisable,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Bulk enable or disable multiple rules.
    
    Example request body:
    {
        "rule_ids": [1, 2, 3],
        "is_active": false
    }
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Fetch rules
    rules = db.query(BusinessRule).filter(
        BusinessRule.id.in_(operation.rule_ids),
        BusinessRule.product_id == product_id,
    ).all()
    
    if not rules:
        raise HTTPException(status_code=404, detail="No matching rules found")
    
    # Update all rules
    updated_ids = []
    for rule in rules:
        rule.is_active = operation.is_active
        updated_ids.append(rule.id)
    
    db.commit()
    
    action = "enabled" if operation.is_active else "disabled"
    return {
        "message": f"Successfully {action} {len(updated_ids)} rules",
        "product_id": product_id,
        "updated_rule_ids": updated_ids,
        "is_active": operation.is_active,
    }


@router.delete("/products/{product_id}/rules/bulk/delete")
def bulk_delete_rules(
    product_id: int,
    operation: BulkDelete,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Bulk delete multiple rules.
    
    Example request body:
    {
        "rule_ids": [1, 2, 3]
    }
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Fetch rules
    rules = db.query(BusinessRule).filter(
        BusinessRule.id.in_(operation.rule_ids),
        BusinessRule.product_id == product_id,
    ).all()
    
    if not rules:
        raise HTTPException(status_code=404, detail="No matching rules found")
    
    # Delete all rules
    deleted_ids = []
    for rule in rules:
        deleted_ids.append(rule.id)
        db.delete(rule)
    
    db.commit()
    
    return {
        "message": f"Successfully deleted {len(deleted_ids)} rules",
        "product_id": product_id,
        "deleted_rule_ids": deleted_ids,
    }


@router.post("/products/{product_id}/rules/bulk/update-priority")
def bulk_update_priority(
    product_id: int,
    operation: BulkPriorityUpdate,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Bulk update rule priorities.
    
    Example request body:
    {
        "updates": [
            {"rule_id": 1, "priority": 10},
            {"rule_id": 2, "priority": 20},
            {"rule_id": 3, "priority": 30}
        ]
    }
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Extract rule IDs and build priority map
    priority_map = {}
    for update in operation.updates:
        if "rule_id" not in update or "priority" not in update:
            raise HTTPException(
                status_code=400, 
                detail="Each update must have 'rule_id' and 'priority' fields"
            )
        priority_map[update["rule_id"]] = update["priority"]
    
    # Fetch rules
    rule_ids = list(priority_map.keys())
    rules = db.query(BusinessRule).filter(
        BusinessRule.id.in_(rule_ids),
        BusinessRule.product_id == product_id,
    ).all()
    
    if not rules:
        raise HTTPException(status_code=404, detail="No matching rules found")
    
    # Update priorities
    updated_ids = []
    for rule in rules:
        if rule.id in priority_map:
            rule.priority = priority_map[rule.id]
            updated_ids.append(rule.id)
    
    db.commit()
    
    return {
        "message": f"Successfully updated priority for {len(updated_ids)} rules",
        "product_id": product_id,
        "updated_rule_ids": updated_ids,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXPORT / IMPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/products/{product_id}/rules/export")
def export_business_rules(
    product_id: int,
    stage: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Export all business rules for a product in importable format.
    
    Query parameters:
    - stage: Export only rules for specific stage
    - include_inactive: Include inactive rules (default: false)
    
    Returns JSON that can be imported to another product/environment.
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Build query
    query = db.query(BusinessRule).filter(BusinessRule.product_id == product_id)
    
    if stage:
        query = query.filter(BusinessRule.stage == stage)
    
    if not include_inactive:
        query = query.filter(BusinessRule.is_active == True)
    
    query = query.order_by(BusinessRule.stage, BusinessRule.priority, BusinessRule.name)
    rules = query.all()
    
    # Export format (excludes IDs and timestamps for portability)
    exported_rules = []
    for rule in rules:
        exported_rules.append({
            "name": rule.name,
            "description": rule.description,
            "rule_type": rule.rule_type,
            "rule_definition": rule.rule_definition,
            "stage": rule.stage,
            "is_active": rule.is_active,
            "distributor_id": rule.distributor_id,
            "priority": rule.priority,
        })
    
    return {
        "export_metadata": {
            "source_product_id": product_id,
            "source_product_name": product.name,
            "export_timestamp": None,  # Could add datetime here
            "total_rules": len(exported_rules),
        },
        "rules": exported_rules,
    }


class RuleImportRequest(BaseModel):
    """Schema for importing rules."""
    rules: list[BusinessRuleCreate] = Field(..., description="List of rules to import")
    conflict_strategy: str = Field(
        default="skip",
        description="How to handle duplicates: 'skip', 'replace', or 'error'"
    )


@router.post("/products/{product_id}/rules/import")
def import_business_rules(
    product_id: int,
    import_request: RuleImportRequest,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Import business rules from export format.
    
    Conflict strategies:
    - skip: Skip rules with duplicate names (default)
    - replace: Replace existing rules with same name
    - error: Raise error if duplicate names found
    
    Example request body:
    {
        "conflict_strategy": "skip",
        "rules": [
            {
                "name": "Age Range Validation",
                "rule_definition": {...},
                "stage": "quote_simulate",
                ...
            }
        ]
    }
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    if import_request.conflict_strategy not in ["skip", "replace", "error"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid conflict_strategy. Must be 'skip', 'replace', or 'error'"
        )
    
    # Check for existing rules with same names
    existing_names = {
        rule.name: rule
        for rule in db.query(BusinessRule).filter(
            BusinessRule.product_id == product_id
        ).all()
    }
    
    stats = {
        "created": 0,
        "replaced": 0,
        "skipped": 0,
        "errors": [],
    }
    
    for rule_data in import_request.rules:
        rule_name = rule_data.name
        
        # Check for duplicate
        if rule_name in existing_names:
            if import_request.conflict_strategy == "error":
                raise HTTPException(
                    status_code=409,
                    detail=f"Duplicate rule name found: '{rule_name}'. Use conflict_strategy='skip' or 'replace'."
                )
            elif import_request.conflict_strategy == "skip":
                stats["skipped"] += 1
                continue
            elif import_request.conflict_strategy == "replace":
                # Delete existing rule
                existing_rule = existing_names[rule_name]
                db.delete(existing_rule)
                stats["replaced"] += 1
        
        # Create new rule
        new_rule = BusinessRule(
            product_id=product_id,
            name=rule_data.name,
            description=rule_data.description,
            rule_type=rule_data.rule_type,
            rule_definition=rule_data.rule_definition,
            stage=rule_data.stage,
            is_active=rule_data.is_active,
            distributor_id=rule_data.distributor_id,
            priority=rule_data.priority,
        )
        db.add(new_rule)
        stats["created"] += 1
    
    db.commit()
    
    return {
        "message": "Import completed successfully",
        "product_id": product_id,
        "product_name": product.name,
        "statistics": stats,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RULE TESTING / PREVIEW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RuleTestRequest(BaseModel):
    """Schema for testing a rule."""
    rule_definition: dict[str, Any] = Field(..., description="Rule to test")
    test_data: dict[str, Any] = Field(..., description="Sample data to validate")


def _evaluate_rule(rule_def: dict, data: dict) -> dict[str, Any]:
    """
    Evaluate a rule against test data.
    
    This is a simplified version of the validation logic.
    Returns validation result with pass/fail and messages.
    """
    result = {
        "passed": True,
        "errors": [],
        "warnings": [],
    }
    
    try:
        # Extract rule components
        field_path = rule_def.get("field", "")
        operator = rule_def.get("operator", "")
        expected_value = rule_def.get("value")
        error_message = rule_def.get("error_message", "Validation failed")
        
        # Navigate to field in data
        field_value = data
        for key in field_path.split("."):
            if isinstance(field_value, dict) and key in field_value:
                field_value = field_value[key]
            else:
                result["passed"] = False
                result["errors"].append(f"Field '{field_path}' not found in test data")
                return result
        
        # Apply operator
        if operator == "in_range":
            min_val, max_val = expected_value
            if not (min_val <= field_value <= max_val):
                result["passed"] = False
                result["errors"].append(f"{error_message} (value: {field_value}, expected: {min_val}-{max_val})")
        
        elif operator == "equals":
            if field_value != expected_value:
                result["passed"] = False
                result["errors"].append(f"{error_message} (value: {field_value}, expected: {expected_value})")
        
        elif operator == "not_equals":
            if field_value == expected_value:
                result["passed"] = False
                result["errors"].append(f"{error_message} (value: {field_value})")
        
        elif operator == "greater_than":
            if not (field_value > expected_value):
                result["passed"] = False
                result["errors"].append(f"{error_message} (value: {field_value}, must be > {expected_value})")
        
        elif operator == "less_than":
            if not (field_value < expected_value):
                result["passed"] = False
                result["errors"].append(f"{error_message} (value: {field_value}, must be < {expected_value})")
        
        elif operator == "regex_match":
            import re
            if not re.match(expected_value, str(field_value)):
                result["passed"] = False
                result["errors"].append(f"{error_message} (value: {field_value}, pattern: {expected_value})")
        
        elif operator == "length_equals":
            if len(str(field_value)) != expected_value:
                result["passed"] = False
                result["errors"].append(
                    f"{error_message} (length: {len(str(field_value))}, expected: {expected_value})"
                )
        
        else:
            result["warnings"].append(f"Unknown operator '{operator}' - cannot validate")
    
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"Rule evaluation error: {str(e)}")
    
    return result


@router.post("/rules/test")
def test_business_rule(
    test_request: RuleTestRequest,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Test a business rule against sample data without saving it.
    
    Useful for previewing rule behavior before creation/activation.
    
    Example request body:
    {
        "rule_definition": {
            "field": "insuree.age",
            "operator": "in_range",
            "value": [18, 65],
            "error_message": "Age must be between 18 and 65",
            "error_code": "AGE_OUT_OF_RANGE"
        },
        "test_data": {
            "insuree": {
                "age": 35,
                "nif": "123456789"
            }
        }
    }
    """
    result = _evaluate_rule(test_request.rule_definition, test_request.test_data)
    
    return {
        "test_result": result,
        "rule_definition": test_request.rule_definition,
        "test_data": test_request.test_data,
    }


@router.post("/rules/{rule_id}/test")
def test_existing_rule(
    rule_id: int,
    test_data: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Test an existing business rule against sample data.
    
    Example request body:
    {
        "insuree": {
            "age": 35,
            "nif": "123456789"
        }
    }
    """
    # Fetch rule
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    
    # Test the rule
    result = _evaluate_rule(rule.rule_definition, test_data)
    
    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "test_result": result,
        "test_data": test_data,
    }
