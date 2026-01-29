"""Product workflow management endpoints."""

import logging
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.database import Product, ProductWorkflow, UserSession, get_db
from orchestrator.routers.auth import get_current_user
from orchestrator.routers.instance_api import verify_shared_key
from orchestrator.utils.logging_helpers import log_activity, log_audit
from orchestrator.step_config_schemas import get_step_config_schema, list_step_config_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["workflows"])
workflow_metadata_router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-metadata"])


# Pydantic schemas
class WorkflowStepConfig(BaseModel):
    """Configuration for a workflow step."""
    id: str = Field(..., description="Unique step ID within the workflow")
    type: str = Field(..., description="Step type (e.g., fetch_quote, validate_properties)")
    config: dict[str, Any] = Field(default_factory=dict, description="Step-specific configuration")
    description: str | None = Field(None, description="Human-readable description of what this step does")


class WorkflowDefinition(BaseModel):
    """Full workflow definition."""
    endpoint: str = Field(..., description="Endpoint this workflow applies to")
    steps: List[WorkflowStepConfig] = Field(..., description="Ordered list of workflow steps")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional workflow metadata")


class WorkflowCreate(BaseModel):
    """Schema for creating a new workflow."""
    endpoint: str = Field(
        ...,
        description="Endpoint this workflow applies to (e.g., quote_simulate, quote_setup)"
    )
    workflow_definition: WorkflowDefinition
    is_active: bool = Field(default=True, description="Whether this workflow is active")


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""
    workflow_definition: WorkflowDefinition | None = None
    is_active: bool | None = None


class WorkflowResponse(BaseModel):
    """Response schema for workflow data."""
    id: int
    product_id: int
    endpoint: str
    workflow_definition: dict
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Workflow CRUD endpoints

@router.post("/{product_id}/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    product_id: int,
    workflow: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> ProductWorkflow:
    """
    Create a new workflow for a product.
    
    The workflow defines the sequence of steps to execute for a specific endpoint.
    """
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Check if workflow already exists for this endpoint
    existing = db.query(ProductWorkflow).filter(
        ProductWorkflow.product_id == product_id,
        ProductWorkflow.endpoint == workflow.endpoint
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow for endpoint '{workflow.endpoint}' already exists. Use PUT to update."
        )
    
    # Create workflow
    new_workflow = ProductWorkflow(
        product_id=product_id,
        endpoint=workflow.endpoint,
        workflow_definition=workflow.workflow_definition.model_dump(),
        is_active=workflow.is_active,
        version=1
    )
    
    db.add(new_workflow)
    db.commit()
    db.refresh(new_workflow)
    
    # Log activity
    log_activity(
        db=db,
        product_id=product_id,
        event_type="workflow_created",
        message=f"Workflow created for endpoint '{workflow.endpoint}' on product '{product.name}'",
        severity="info",
        metadata={"endpoint": workflow.endpoint, "workflow_id": new_workflow.id}
    )
    
    # Log audit
    log_audit(
        db=db,
        user_email=current_user.email,
        action="create",
        resource_type="workflow",
        resource_id=new_workflow.id,
        changes={"workflow_definition": workflow.workflow_definition.model_dump()},
        metadata={"product_id": product_id, "endpoint": workflow.endpoint}
    )
    
    logger.info(f"Created workflow {new_workflow.id} for product {product_id}, endpoint {workflow.endpoint}")
    
    return new_workflow


@router.get("/{product_id}/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    product_id: int,
    endpoint: str | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> List[ProductWorkflow]:
    """
    List all workflows for a product.
    
    Optionally filter by endpoint or active status.
    """
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Build query
    query = db.query(ProductWorkflow).filter(ProductWorkflow.product_id == product_id)
    
    if endpoint:
        query = query.filter(ProductWorkflow.endpoint == endpoint)
    
    if active_only:
        query = query.filter(ProductWorkflow.is_active == True)
    
    workflows = query.order_by(ProductWorkflow.endpoint).all()
    
    return workflows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC ENDPOINTS (for instances using shared key auth)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/public/{product_id}/workflows", response_model=List[WorkflowResponse])
async def list_workflows_public(
    product_id: int,
    endpoint: str | None = None,
    active_only: bool = True,
    x_cortex_shared_key: str = Header(None, alias="X-Cortex-Shared-Key"),
    db: Session = Depends(get_db),
) -> List[ProductWorkflow]:
    """
    Public endpoint for instances to fetch workflows using shared key.
    
    Used by instances during startup to load workflow definitions.
    
    **Authentication:** X-Cortex-Shared-Key header (not user session)
    **Scope:** Returns only workflows for the authenticated product
    
    Query parameters:
    - endpoint: Optional filter by specific endpoint (e.g., quote_simulate)
    - active_only: Only return active workflows (default: true)
    """
    # Verify shared key and get product (ensures scoped access)
    product = verify_shared_key(product_id, x_cortex_shared_key, db)
    
    # Build query - scoped to this product only
    query = db.query(ProductWorkflow).filter(ProductWorkflow.product_id == product_id)
    
    if endpoint:
        query = query.filter(ProductWorkflow.endpoint == endpoint)
    
    if active_only:
        query = query.filter(ProductWorkflow.is_active == True)
    
    workflows = query.order_by(ProductWorkflow.endpoint).all()
    
    logger.info(f"Instance fetched {len(workflows)} workflows for product {product_id}")
    
    return workflows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# END PUBLIC ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/{product_id}/workflows/available-steps")
async def get_available_workflow_steps(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get list of available workflow steps for the visual flow builder.
    
    Returns step metadata from the instance including:
    - Categories (data, validation, calculation, update)
    - Available steps with config schemas
    
    This proxies to the instance's workflow-steps endpoint.
    """
    import httpx
    
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Proxy to instance - use docker host IP (works for swarm services with published ports)
    # Since orchestrator runs on host and can't resolve docker service names,
    # we use the host machine's IP address to reach the published port
    import socket
    host_ip = socket.gethostbyname(socket.gethostname())
    instance_url = f"http://{host_ip}:{product.port}/internal/habit-specs/workflow-steps"
    
    logger.info(f"Fetching workflow steps from: {instance_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(instance_url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch workflow steps from instance: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch workflow steps from instance: {str(e)}"
        )


@router.get("/{product_id}/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    product_id: int,
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> ProductWorkflow:
    """Get a specific workflow by ID."""
    workflow = db.query(ProductWorkflow).filter(
        ProductWorkflow.id == workflow_id,
        ProductWorkflow.product_id == product_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found for product {product_id}"
        )
    
    return workflow


@router.put("/{product_id}/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    product_id: int,
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> ProductWorkflow:
    """
    Update an existing workflow.
    
    Increments the version number on workflow_definition changes.
    """
    workflow = db.query(ProductWorkflow).filter(
        ProductWorkflow.id == workflow_id,
        ProductWorkflow.product_id == product_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found for product {product_id}"
        )
    
    # Track changes for audit
    changes = {}
    
    if workflow_update.workflow_definition is not None:
        old_def = workflow.workflow_definition
        new_def = workflow_update.workflow_definition.model_dump()
        workflow.workflow_definition = new_def
        workflow.version += 1  # Increment version on definition change
        changes["workflow_definition"] = {"old": old_def, "new": new_def}
        changes["version"] = {"old": workflow.version - 1, "new": workflow.version}
    
    if workflow_update.is_active is not None:
        old_active = workflow.is_active
        workflow.is_active = workflow_update.is_active
        changes["is_active"] = {"old": old_active, "new": workflow.is_active}
    
    db.commit()
    db.refresh(workflow)
    
    # Log activity
    product = db.query(Product).filter(Product.id == product_id).first()
    log_activity(
        db=db,
        product_id=product_id,
        event_type="workflow_updated",
        message=f"Workflow updated for endpoint '{workflow.endpoint}' on product '{product.name}'",
        severity="info",
        event_metadata={
            "endpoint": workflow.endpoint,
            "workflow_id": workflow.id,
            "version": workflow.version
        }
    )
    
    # Log audit
    log_audit(
        db=db,
        user_id=current_user.email,
        action="update",
        resource_type="workflow",
        resource_id=workflow.id,
        resource_name=f"{product.name} - {workflow.endpoint}",
        changes=changes
    )
    
    logger.info(f"Updated workflow {workflow.id}, now version {workflow.version}")
    
    return workflow


@router.delete("/{product_id}/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    product_id: int,
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Delete a workflow."""
    workflow = db.query(ProductWorkflow).filter(
        ProductWorkflow.id == workflow_id,
        ProductWorkflow.product_id == product_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found for product {product_id}"
        )
    
    endpoint = workflow.endpoint
    
    db.delete(workflow)
    db.commit()
    
    # Log activity
    product = db.query(Product).filter(Product.id == product_id).first()
    log_activity(
        db=db,
        product_id=product_id,
        event_type="workflow_deleted",
        message=f"Workflow deleted for endpoint '{endpoint}' on product '{product.name}'",
        severity="info",
        metadata={"endpoint": endpoint, "workflow_id": workflow_id}
    )
    
    # Log audit
    log_audit(
        db=db,
        user_email=current_user.email,
        action="delete",
        resource_type="workflow",
        resource_id=workflow_id,
        changes={},
        metadata={"product_id": product_id, "endpoint": endpoint}
    )
    
    logger.info(f"Deleted workflow {workflow_id} for product {product_id}")


# ============================================================================
# Workflow Configuration Metadata Endpoints
# ============================================================================

class QuoteField(BaseModel):
    """Metadata for a single quote field that can be updated."""
    
    name: str = Field(..., description="Field name (e.g., 'state', 'rate_base')")
    type: str = Field(..., description="Field type: string, number, object, array, boolean")
    description: str = Field(..., description="Human-readable description")
    options: List[str] | None = Field(None, description="Available values for enum fields")
    default_value_type: str = Field(..., description="'static' (user input) or 'contextual' (from workflow)")
    context_path: str | None = Field(None, description="Jinja2 template path (e.g., '{{rate_base}}')")
    required: bool = Field(False, description="Whether this field is required")
    available_after: str | None = Field(None, description="Workflow step that provides this value")


class ContextualVariable(BaseModel):
    """Metadata for a variable available from workflow context."""
    
    name: str = Field(..., description="Variable name")
    type: str = Field(..., description="Variable type")
    description: str = Field(..., description="Description of the variable")
    available_after: str = Field(..., description="Workflow step that produces this variable")


class QuoteFieldsRegistry(BaseModel):
    """Registry of all updatable quote fields and contextual variables."""
    
    fields: List[QuoteField] = Field(..., description="Available quote fields")
    contextual_variables: List[ContextualVariable] = Field(..., description="Variables from workflow context")


class UpdateQuoteValidationRequest(BaseModel):
    """Request to validate update_quote configuration."""
    
    fields: dict[str, Any] = Field(..., description="Field updates to validate")


class ValidationError(BaseModel):
    """Validation error details."""
    
    field: str = Field(..., description="Field name with error")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="'error' or 'warning'")


class UpdateQuoteValidationResponse(BaseModel):
    """Response from validation endpoint."""
    
    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[ValidationError] = Field(default_factory=list, description="Validation warnings")


# Quote Fields Registry
QUOTE_FIELDS_REGISTRY = [
    QuoteField(
        name="state",
        type="string",
        description="Quote state (lifecycle status)",
        options=["open", "simulated", "closed", "cancelled", "expired"],
        default_value_type="static",
        required=False,
    ),
    QuoteField(
        name="rate_base",
        type="number",
        description="Base premium rate calculated by pricing engine",
        default_value_type="contextual",
        context_path="{{rate_base}}",
        required=False,
        available_after="calculate_premium",
    ),
    QuoteField(
        name="premium_breakdown",
        type="object",
        description="Detailed premium calculation breakdown",
        default_value_type="contextual",
        context_path="{{premium_breakdown}}",
        required=False,
        available_after="calculate_premium",
    ),
    QuoteField(
        name="pricing_details",
        type="object",
        description="Full pricing calculation details including strategy used",
        default_value_type="contextual",
        context_path="{{pricing_details}}",
        required=False,
        available_after="calculate_premium",
    ),
    QuoteField(
        name="validation_results",
        type="object",
        description="Results from business rules validation",
        default_value_type="contextual",
        context_path="{{validation_results}}",
        required=False,
        available_after="validate_business_rules",
    ),
    QuoteField(
        name="custom_metadata",
        type="object",
        description="Custom metadata to attach to quote",
        default_value_type="static",
        required=False,
    ),
    QuoteField(
        name="tags",
        type="array",
        description="Quote tags for categorization and filtering",
        default_value_type="static",
        required=False,
    ),
    QuoteField(
        name="notes",
        type="string",
        description="Internal notes about the quote",
        default_value_type="static",
        required=False,
    ),
    QuoteField(
        name="policy_start_date",
        type="string",
        description="Policy start date (YYYY-MM-DD format)",
        default_value_type="calculated",
        required=False,
        context_path="{{policy_start_date}}",
    ),
    QuoteField(
        name="policy_end_date",
        type="string",
        description="Policy end date (YYYY-MM-DD format)",
        default_value_type="calculated",
        required=False,
        context_path="{{policy_end_date}}",
    ),
    QuoteField(
        name="payment_gateway",
        type="string",
        description="Payment gateway to use for this quote",
        default_value_type="calculated",
        required=False,
        context_path="{{payment_gateway}}",
    ),
]

CONTEXTUAL_VARIABLES = [
    ContextualVariable(
        name="rate_base",
        type="number",
        description="Calculated premium from pricing engine",
        available_after="calculate_premium",
    ),
    ContextualVariable(
        name="premium_breakdown",
        type="object",
        description="Detailed breakdown of premium calculation",
        available_after="calculate_premium",
    ),
    ContextualVariable(
        name="pricing_details",
        type="object",
        description="Full pricing calculation metadata",
        available_after="calculate_premium",
    ),
    ContextualVariable(
        name="validation_results",
        type="object",
        description="Results from business rules validation",
        available_after="validate_business_rules",
    ),
    ContextualVariable(
        name="quote",
        type="object",
        description="Full quote object from Habit platform",
        available_after="fetch_quote",
    ),
    ContextualVariable(
        name="quote_properties",
        type="array",
        description="Quote properties from Habit platform",
        available_after="fetch_quote_properties",
    ),
    ContextualVariable(
        name="insurees",
        type="array",
        description="Insurees (policyholders) data",
        available_after="fetch_insurees",
    ),
    ContextualVariable(
        name="protected_assets",
        type="array",
        description="Protected assets data",
        available_after="fetch_protected_assets",
    ),
    ContextualVariable(
        name="workflow",
        type="object",
        description="Workflow execution metadata (timestamp, version, etc.)",
        available_after="fetch_quote",
    ),
]


@workflow_metadata_router.get("/quote-fields", response_model=QuoteFieldsRegistry)
async def get_quote_fields() -> QuoteFieldsRegistry:
    """
    Get registry of all updatable quote fields and contextual variables.
    
    This endpoint returns metadata about:
    - All fields that can be updated on a quote
    - Which fields come from workflow context vs user input
    - Available contextual variables from workflow execution
    
    Used by the UI to build the Update Quote block configuration interface.
    
    Returns:
        QuoteFieldsRegistry with fields and contextual variables
    """
    logger.info("Fetching quote fields registry")
    
    return QuoteFieldsRegistry(
        fields=QUOTE_FIELDS_REGISTRY,
        contextual_variables=CONTEXTUAL_VARIABLES,
    )


@workflow_metadata_router.post("/validate-update-quote", response_model=UpdateQuoteValidationResponse)
async def validate_update_quote(request: UpdateQuoteValidationRequest) -> UpdateQuoteValidationResponse:
    """
    Validate update_quote workflow step configuration.
    
    Validates:
    - Field types match expected types
    - Jinja2 template syntax is valid
    - Required fields are present
    - Contextual variables reference valid workflow outputs
    
    Args:
        request: Configuration to validate
    
    Returns:
        Validation result with any errors or warnings
    """
    logger.info(f"Validating update_quote configuration: {request.fields}")
    
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    
    # Create field lookup
    field_lookup = {f.name: f for f in QUOTE_FIELDS_REGISTRY}
    
    for field_name, value in request.fields.items():
        # Check if field exists in registry
        if field_name not in field_lookup:
            warnings.append(ValidationError(
                field=field_name,
                message=f"Field '{field_name}' is not in the standard registry. It may be a custom field.",
                severity="warning",
            ))
            continue
        
        field_meta = field_lookup[field_name]
        
        # Validate Jinja2 template syntax if value looks like a template
        if isinstance(value, str) and "{{" in value and "}}" in value:
            if not _validate_jinja2_syntax(value):
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Invalid Jinja2 template syntax: {value}",
                    severity="error",
                ))
            
            # Check if using contextual field without proper setup
            if field_meta.available_after:
                warnings.append(ValidationError(
                    field=field_name,
                    message=f"Field requires '{field_meta.available_after}' step to run before update_quote",
                    severity="warning",
                ))
        
        # Type validation
        type_valid = _validate_field_type(value, field_meta.type)
        if not type_valid:
            errors.append(ValidationError(
                field=field_name,
                message=f"Value type mismatch. Expected {field_meta.type}, got {type(value).__name__}",
                severity="error",
            ))
        
        # Enum validation
        if field_meta.options and isinstance(value, str) and "{{" not in value:
            if value not in field_meta.options:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Invalid option '{value}'. Must be one of: {', '.join(field_meta.options)}",
                    severity="error",
                ))
    
    is_valid = len(errors) == 0
    
    logger.info(f"Validation complete. Valid: {is_valid}, Errors: {len(errors)}, Warnings: {len(warnings)}")
    
    return UpdateQuoteValidationResponse(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
    )


def _validate_jinja2_syntax(template: str) -> bool:
    """Validate Jinja2 template syntax."""
    try:
        from jinja2 import Environment
        env = Environment()
        env.parse(template)
        return True
    except Exception as e:
        logger.warning(f"Invalid Jinja2 template '{template}': {e}")
        return False


def _validate_field_type(value: Any, expected_type: str) -> bool:
    """Validate that a value matches the expected type."""
    # Allow Jinja2 templates for any type
    if isinstance(value, str) and "{{" in value:
        return True
    
    type_map = {
        "string": str,
        "number": (int, float),
        "object": dict,
        "array": list,
        "boolean": bool,
    }
    
    expected_python_type = type_map.get(expected_type)
    if expected_python_type is None:
        logger.warning(f"Unknown type: {expected_type}")
        return True  # Allow unknown types
    
    return isinstance(value, expected_python_type)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP CONFIGURATION SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@workflow_metadata_router.get(
    "/step-config-schemas",
    summary="Get all step configuration schemas",
    description="Returns configuration schemas for all workflow step types. "
                "UI uses this to dynamically render configuration panels.",
)
async def get_all_step_config_schemas():
    """
    Get configuration schemas for all step types.
    
    The UI should use these schemas to:
    - Dynamically render configuration forms
    - Validate user input
    - Show/hide fields based on conditions
    - Provide examples and documentation
    
    Returns a dict mapping step_type → schema.
    """
    schemas = list_step_config_schemas()
    return {
        "schemas": {k: v.model_dump() for k, v in schemas.items()},
        "count": len(schemas)
    }


@workflow_metadata_router.get(
    "/step-config-schemas/{step_type}",
    summary="Get configuration schema for a specific step type",
    description="Returns the configuration schema for a specific workflow step type",
)
async def get_step_config_schema_endpoint(step_type: str):
    """
    Get configuration schema for a specific step type.
    
    Args:
        step_type: The workflow step type (e.g., "update_quote", "calculate_premium")
    
    Returns:
        Configuration schema with sections, fields, validation rules, and examples
    
    Raises:
        404: Step type not found
    """
    schema = get_step_config_schema(step_type)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"No configuration schema found for step type: {step_type}"
        )
    
    return schema.model_dump()
