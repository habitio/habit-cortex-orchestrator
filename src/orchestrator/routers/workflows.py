"""Product workflow management endpoints."""

import logging
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.database import Product, ProductWorkflow, UserSession, get_db
from orchestrator.routers.auth import get_current_user
from orchestrator.utils.logging_helpers import log_activity, log_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["workflows"])


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
    
    # Proxy to instance
    instance_url = f"http://localhost:{product.port}/internal/habit-specs/workflow-steps"
    
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
        metadata={
            "endpoint": workflow.endpoint,
            "workflow_id": workflow.id,
            "version": workflow.version
        }
    )
    
    # Log audit
    log_audit(
        db=db,
        user_email=current_user.email,
        action="update",
        resource_type="workflow",
        resource_id=workflow.id,
        changes=changes,
        metadata={"product_id": product_id, "endpoint": workflow.endpoint}
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
