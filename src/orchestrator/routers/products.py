"""Product management endpoints."""

import logging
from datetime import datetime
from typing import List

from docker.errors import APIError, NotFound
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from orchestrator.database import Product, get_db
from orchestrator.services.docker_manager import DockerManager
from orchestrator.utils.logging_helpers import log_activity, log_audit, calculate_changes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


# Pydantic schemas
class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    name: str = Field(..., min_length=1, max_length=255, description="Product display name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern="^[a-z0-9-]+$",
        description="URL-safe slug (lowercase, numbers, hyphens only)",
    )
    port: int = Field(..., ge=1024, le=65535, description="API port (1024-65535)")
    replicas: int = Field(default=1, ge=1, le=10, description="Number of instances (1-10)")
    env_vars: dict[str, str] | None = Field(
        default=None,
        description="Environment variables for the product instance (e.g., API keys, database URLs)",
    )
    image_id: int | None = Field(
        default=None,
        description="Docker image ID to use (from /api/v1/images). If not specified, uses default image.",
    )


class ProductUpdate(BaseModel):
    """Schema for updating product metadata."""
    name: str | None = Field(None, min_length=1, max_length=255)
    replicas: int | None = Field(None, ge=1, le=10)
    env_vars: dict[str, str] | None = Field(None, description="Update environment variables")
    image_id: int | None = Field(None, description="Change Docker image")


class ScaleRequest(BaseModel):
    """Schema for scaling product."""
    replicas: int = Field(..., ge=1, le=10, description="Number of replicas (1-10)")


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int
    name: str
    slug: str
    port: int
    replicas: int
    status: str
    env_vars: dict[str, str] | None
    image_id: int | None
    image_name: str
    service_id: str | None
    deployed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Endpoints
@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_data: ProductCreate, request: Request, db: Session = Depends(get_db)):
    """
    Create a new product instance definition.
    
    Note: This only creates the database record. Use POST /products/{id}/start to deploy.
    """
    # If image_id is provided, fetch the image name
    image_name = "bre-payments:latest"  # Default
    if product_data.image_id:
        from orchestrator.database.models import DockerImage
        docker_image = db.query(DockerImage).filter(DockerImage.id == product_data.image_id).first()
        if not docker_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker image {product_data.image_id} not found",
            )
        if docker_image.build_status != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Docker image {docker_image.name}:{docker_image.tag} build status is '{docker_image.build_status}', not 'success'",
            )
        image_name = f"{docker_image.name}:{docker_image.tag}"
    
    product = Product(
        name=product_data.name,
        slug=product_data.slug,
        port=product_data.port,
        replicas=product_data.replicas,
        env_vars=product_data.env_vars or {},
        image_id=product_data.image_id,
        image_name=image_name,
        status="stopped",
    )
    
    try:
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info(f"Created product '{product.name}' (ID: {product.id})")
        
        # Log activity
        log_activity(
            db,
            event_type="product_created",
            message=f"{product.name} created",
            product_id=product.id,
            severity="info",
        )
        
        # Log audit
        log_audit(
            db,
            action="create_product",
            resource_type="product",
            resource_id=product.id,
            resource_name=product.name,
            changes={
                "name": {"old": None, "new": product.name},
                "slug": {"old": None, "new": product.slug},
                "port": {"old": None, "new": product.port},
                "replicas": {"old": None, "new": product.replicas},
            },
            request=request,
            success=True,
        )
        
        return product
    except IntegrityError as e:
        db.rollback()
        if "slug" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with slug '{product_data.slug}' already exists",
            )
        elif "port" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Port {product_data.port} is already in use",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create product",
        )


@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """List all products."""
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Update product metadata.
    
    Note: Changing replicas here only updates the database.
    Use POST /products/{id}/scale to actually scale the service.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    # Calculate changes for audit log
    changes = calculate_changes(product, product_data.model_dump(exclude_unset=True))
    
    if product_data.name is not None:
        product.name = product_data.name
    if product_data.replicas is not None:
        product.replicas = product_data.replicas
    if product_data.env_vars is not None:
        product.env_vars = product_data.env_vars
    if product_data.image_id is not None:
        from orchestrator.database.models import DockerImage
        docker_image = db.query(DockerImage).filter(DockerImage.id == product_data.image_id).first()
        if not docker_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker image {product_data.image_id} not found",
            )
        if docker_image.build_status != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Docker image build status is '{docker_image.build_status}', not 'success'",
            )
        product.image_id = product_data.image_id
        product.image_name = f"{docker_image.name}:{docker_image.tag}"
    
    db.commit()
    db.refresh(product)
    logger.info(f"Updated product '{product.name}' (ID: {product.id})")
    
    # Log audit
    if changes:
        log_audit(
            db,
            action="update_product",
            resource_type="product",
            resource_id=product.id,
            resource_name=product.name,
            changes=changes,
            request=request,
            success=True,
        )
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Delete a product.
    
    Note: Product must be stopped before deletion.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    if product.status != "stopped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete product in '{product.status}' state. Stop it first.",
        )
    
    product_name = product.name
    db.delete(product)
    db.commit()
    logger.info(f"Deleted product '{product_name}' (ID: {product_id})")
    
    # Log activity
    log_activity(
        db,
        event_type="product_deleted",
        message=f"{product_name} deleted",
        severity="info",
    )
    
    # Log audit
    log_audit(
        db,
        action="delete_product",
        resource_type="product",
        resource_id=product_id,
        resource_name=product_name,
        request=request,
        success=True,
    )


# Orchestration endpoints
@router.post("/{product_id}/start", response_model=ProductResponse)
def start_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    """Deploy product to Docker Swarm."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    if product.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is already running",
        )
    
    docker_manager = DockerManager()
    
    try:
        product.status = "starting"
        db.commit()
        
        service_id = docker_manager.create_service(product)
        
        product.service_id = service_id
        product.status = "running"
        product.deployed_at = datetime.utcnow()
        db.commit()
        db.refresh(product)
        
        logger.info(f"Started product '{product.name}' (ID: {product.id})")
        
        # Log activity
        log_activity(
            db,
            event_type="product_started",
            message=f"{product.name} started",
            product_id=product.id,
            severity="info",
            event_metadata={"service_id": service_id, "replicas": product.replicas},
        )
        
        # Log audit
        log_audit(
            db,
            action="start_product",
            resource_type="product",
            resource_id=product.id,
            resource_name=product.name,
            changes={"status": {"old": "stopped", "new": "running"}},
            request=request,
            success=True,
        )
        
        return product
        
    except APIError as e:
        product.status = "failed"
        db.commit()
        logger.error(f"Failed to start product '{product.name}': {e}")
        
        # Log activity
        log_activity(
            db,
            event_type="product_start_failed",
            message=f"{product.name} failed to start: {str(e)[:100]}",
            product_id=product.id,
            severity="error",
        )
        
        # Log audit
        log_audit(
            db,
            action="start_product",
            resource_type="product",
            resource_id=product.id,
            resource_name=product.name,
            request=request,
            success=False,
            error_message=str(e),
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy service: {str(e)}",
        )


@router.post("/{product_id}/stop", response_model=ProductResponse)
def stop_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    """Stop and remove product from Docker Swarm."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    if product.status == "stopped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is already stopped",
        )
    
    if not product.service_id:
        product.status = "stopped"
        db.commit()
        db.refresh(product)
        return product
    
    docker_manager = DockerManager()
    
    try:
        product.status = "stopping"
        db.commit()
        
        docker_manager.remove_service(product.service_id)
        
        product.service_id = None
        product.status = "stopped"
        product.deployed_at = None
        db.commit()
        db.refresh(product)
        
        logger.info(f"Stopped product '{product.name}' (ID: {product.id})")
        
        # Log activity
        log_activity(
            db,
            event_type="product_stopped",
            message=f"{product.name} stopped",
            product_id=product.id,
            severity="info",
        )
        
        # Log audit
        log_audit(
            db,
            action="stop_product",
            resource_type="product",
            resource_id=product.id,
            resource_name=product.name,
            changes={"status": {"old": "running", "new": "stopped"}},
            request=request,
            success=True,
        )
        
        return product
        
    except NotFound:
        # Service already removed
        product.service_id = None
        product.status = "stopped"
        product.deployed_at = None
        db.commit()
        db.refresh(product)
        return product
        
    except APIError as e:
        logger.error(f"Failed to stop product '{product.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove service: {str(e)}",
        )


@router.post("/{product_id}/scale")
def scale_product(
    product_id: int,
    scale_data: ScaleRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Scale product to specified number of replicas."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    if product.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot scale product in '{product.status}' state. Must be running.",
        )
    
    docker_manager = DockerManager()
    
    try:
        old_replicas = product.replicas
        docker_manager.scale_service(product.service_id, scale_data.replicas)
        
        product.replicas = scale_data.replicas
        db.commit()
        db.refresh(product)
        
        logger.info(f"Scaled product '{product.name}' to {scale_data.replicas} replicas")
        
        # Log activity
        log_activity(
            db,
            event_type="product_scaled",
            message=f"{product.name} scaled to {scale_data.replicas} replicas",
            product_id=product.id,
            severity="info",
            event_metadata={"old_replicas": old_replicas, "new_replicas": scale_data.replicas},
        )
        
        # Log audit
        log_audit(
            db,
            action="scale_product",
            resource_type="product",
            resource_id=product.id,
            resource_name=product.name,
            changes={"replicas": {"old": old_replicas, "new": scale_data.replicas}},
            request=request,
            success=True,
        )
        
        return {
            "product_id": product.id,
            "product_name": product.name,
            "replicas": scale_data.replicas,
            "status": "scaling",
        }
        
    except APIError as e:
        logger.error(f"Failed to scale product '{product.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scale service: {str(e)}",
        )


@router.get("/{product_id}/status")
def get_product_status(product_id: int, db: Session = Depends(get_db)):
    """Get detailed runtime status of product from Docker Swarm."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    if not product.service_id:
        return {
            "product_id": product.id,
            "product_name": product.name,
            "status": product.status,
            "service_id": None,
            "docker_status": None,
        }
    
    docker_manager = DockerManager()
    
    try:
        docker_status = docker_manager.get_service_status(product.service_id)
        return {
            "product_id": product.id,
            "product_name": product.name,
            "status": product.status,
            "service_id": product.service_id,
            "docker_status": docker_status,
        }
    except NotFound:
        # Service was removed outside orchestrator
        product.service_id = None
        product.status = "stopped"
        db.commit()
        return {
            "product_id": product.id,
            "product_name": product.name,
            "status": "stopped",
            "service_id": None,
            "docker_status": None,
        }


@router.get("/{product_id}/logs")
def get_product_logs(
    product_id: int,
    tail: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get logs from a running product service.
    
    Args:
        tail: Number of log lines to return (default 100, max 1000)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    if not product.service_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is not deployed",
        )
    
    # Limit tail to prevent abuse
    tail = min(tail, 1000)
    
    docker_manager = DockerManager()
    
    try:
        logs = docker_manager.get_service_logs(product.service_id, tail=tail)
        return {
            "product_id": product.id,
            "product_name": product.name,
            "service_id": product.service_id,
            "logs": logs,
            "lines": tail,
        }
    except NotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found (may have been removed)",
        )
