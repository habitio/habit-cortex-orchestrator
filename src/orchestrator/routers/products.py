"""Product management endpoints."""

import logging
from datetime import datetime
from typing import List

from docker.errors import APIError, NotFound
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from orchestrator.database import Product, UserSession, get_db
from orchestrator.routers.auth import get_current_user, get_current_user_from_query
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
def create_product(
    product_data: ProductCreate,
    request: Request,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
def list_products(
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all products."""
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    current_user: UserSession = Depends(get_current_user),
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
def delete_product(
    product_id: int,
    request: Request,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a product and all related data.
    
    Note: Product must be stopped before deletion.
    
    Deletes in order:
    1. Activity logs  
    2. Event subscriptions
    3. Product record
    
    Note: Subscriptions cascade delete automatically via relationship.
    """
    from orchestrator.database import ActivityLog
    
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
    
    # Delete related data in correct order
    
    # 1. Delete activity logs
    db.query(ActivityLog).filter(ActivityLog.product_id == product_id).delete()
    
    # 2. Delete product (subscriptions cascade automatically)
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
def start_product(
    product_id: int,
    request: Request,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
def stop_product(
    product_id: int,
    request: Request,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    current_user: UserSession = Depends(get_current_user),
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


@router.post("/{product_id}/generate-shared-key")
def generate_product_shared_key(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Generate a new cryptographically secure shared key for the product.
    
    This key is used for instance-to-orchestrator authentication.
    The key is automatically unique and cannot be duplicated across products.
    """
    from orchestrator.security import generate_shared_key, is_shared_key_unique
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    
    # Generate unique key
    max_attempts = 10
    for _ in range(max_attempts):
        new_key = generate_shared_key(length=64)  # 512-bit key
        if is_shared_key_unique(db, new_key):
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique shared key after multiple attempts",
        )
    
    old_key_masked = f"{product.shared_key[:16]}..." if product.shared_key else None
    
    # Update product
    product.shared_key = new_key
    db.commit()
    db.refresh(product)
    
    logger.info(f"Generated new shared key for product '{product.name}'")
    
    # Log activity
    log_activity(
        db,
        event_type="shared_key_generated",
        message=f"New shared key generated for {product.name}",
        product_id=product.id,
        severity="info",
        event_metadata={"action": "generate_shared_key"},
    )
    
    # Log audit
    log_audit(
        db,
        action="generate_shared_key",
        resource_type="product",
        resource_id=product.id,
        resource_name=product.name,
        changes={"shared_key": {"old": old_key_masked, "new": "generated"}},
        request=request,
        success=True,
    )
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "shared_key": new_key,
        "message": "Shared key generated successfully. Store this securely - it cannot be retrieved again.",
    }


@router.get("/{product_id}/status")
def get_product_status(
    product_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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


@router.get("/{product_id}/logs/stream")
def stream_product_logs(
    product_id: int,
    tail: int = 100,
    current_user: UserSession = Depends(get_current_user_from_query),
    db: Session = Depends(get_db)
):
    """
    Stream logs from a running product service using Server-Sent Events (SSE).
    
    Auth: Token must be provided as query parameter (?token=...) since SSE/EventSource
          cannot set custom headers.
    
    Args:
        tail: Number of initial log lines to return (default 100, max 1000)
        token: Authentication token (query parameter)
    
    Returns:
        StreamingResponse with text/event-stream content type
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
    
    def event_generator():
        """Generate SSE events from Docker log stream."""
        try:
            for log_line in docker_manager.stream_service_logs(product.service_id, tail=tail):
                # Send each log line as an SSE event
                yield f"data: {log_line}\n\n"
        except NotFound:
            yield f"event: error\ndata: Service not found\n\n"
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/{product_id}/logs/mqtt/stream")
def stream_mqtt_logs(
    product_id: int,
    tail: int = 100,
    current_user: UserSession = Depends(get_current_user_from_query),
    db: Session = Depends(get_db)
):
    """
    Stream MQTT-related logs using Server-Sent Events (SSE).
    
    Auth: Token must be provided as query parameter (?token=...) since SSE/EventSource
          cannot set custom headers.
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
    
    tail = min(tail, 1000)
    docker_manager = DockerManager()
    filter_pattern = r"(MQTT|mqtt|Connected|Subscribed|Received.*event|Starting MQTT listener)"
    
    def event_generator():
        """Generate SSE events from Docker log stream with MQTT filter."""
        try:
            for log_line in docker_manager.stream_service_logs(product.service_id, tail=tail):
                # Only send MQTT-related lines
                if re.search(filter_pattern, log_line, re.IGNORECASE):
                    yield f"data: {log_line}\n\n"
        except NotFound:
            yield f"event: error\ndata: Service not found\n\n"
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/{product_id}/logs/events/stream")
def stream_event_logs(
    product_id: int,
    tail: int = 100,
    current_user: UserSession = Depends(get_current_user_from_query),
    db: Session = Depends(get_db)
):
    """
    Stream event processing logs using Server-Sent Events (SSE).
    
    Auth: Token must be provided as query parameter (?token=...) since SSE/EventSource
          cannot set custom headers.
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
    
    tail = min(tail, 1000)
    docker_manager = DockerManager()
    filter_pattern = r"(event.*received|Executing action|action.*executed|Error executing action|Processing.*event)"
    
    def event_generator():
        """Generate SSE events from Docker log stream with event filter."""
        try:
            for log_line in docker_manager.stream_service_logs(product.service_id, tail=tail):
                # Only send event-related lines
                if re.search(filter_pattern, log_line, re.IGNORECASE):
                    yield f"data: {log_line}\n\n"
        except NotFound:
            yield f"event: error\ndata: Service not found\n\n"
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/{product_id}/logs/console/stream")
def stream_console_logs(
    product_id: int,
    tail: int = 100,
    current_user: UserSession = Depends(get_current_user_from_query),
    db: Session = Depends(get_db)
):
    """
    Stream application console logs using Server-Sent Events (SSE).
    Excludes health checks and debug noise.
    
    Auth: Token must be provided as query parameter (?token=...) since SSE/EventSource
          cannot set custom headers.
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
    
    tail = min(tail, 1000)
    docker_manager = DockerManager()
    exclude_pattern = r"(GET /health|GET /metrics|GET /readiness|GET /liveness|Starting gunicorn|Booting worker)"
    
    def event_generator():
        """Generate SSE events from Docker log stream excluding health checks."""
        try:
            for log_line in docker_manager.stream_service_logs(product.service_id, tail=tail):
                # Exclude health check and startup noise
                if not re.search(exclude_pattern, log_line, re.IGNORECASE):
                    yield f"data: {log_line}\n\n"
        except NotFound:
            yield f"event: error\ndata: Service not found\n\n"
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{product_id}/duplicate")
def duplicate_product(
    product_id: int,
    new_name: str,
    new_slug: str,
    new_port: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Duplicate an existing product with all its configuration.
    
    Creates a new product copying:
    - Environment variables
    - MQTT configuration (broker, subscriptions with actions)
    - Replicas setting
    - Docker image reference
    
    Does NOT copy:
    - Shared key (generates new one if needed)
    - Running state (new product starts as 'stopped')
    - Service ID
    """
    # Get source product
    source_product = db.query(Product).filter(Product.id == product_id).first()
    if not source_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source product {product_id} not found",
        )
    
    # Validate new slug is unique
    existing = db.query(Product).filter(Product.slug == new_slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with slug '{new_slug}' already exists",
        )
    
    # Validate new port is unique
    existing_port = db.query(Product).filter(Product.port == new_port).first()
    if existing_port:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Port {new_port} is already in use by product '{existing_port.name}'",
        )
    
    # Create new product with copied data
    new_product = Product(
        name=new_name,
        slug=new_slug,
        port=new_port,
        replicas=source_product.replicas,
        env_vars=source_product.env_vars.copy() if source_product.env_vars else {},
        image_id=source_product.image_id,
        image_name=source_product.image_name,
        status="stopped",
    )
    
    try:
        db.add(new_product)
        db.flush()  # Get the new product ID
        
        # Copy event subscriptions if they exist
        from orchestrator.database import EventSubscription
        
        source_subscriptions = db.query(EventSubscription).filter(
            EventSubscription.product_id == source_product.id
        ).all()
        
        subscriptions_copied = 0
        for source_sub in source_subscriptions:
            new_sub = EventSubscription(
                product_id=new_product.id,
                event_type=source_sub.event_type,
                description=source_sub.description,
                enabled=source_sub.enabled,
                actions=source_sub.actions.copy() if source_sub.actions else [],
            )
            db.add(new_sub)
            subscriptions_copied += 1
        
        db.commit()
        db.refresh(new_product)
        
        logger.info(
            f"Duplicated product '{source_product.name}' (ID: {source_product.id}) "
            f"to '{new_product.name}' (ID: {new_product.id})"
        )
        
        # Log activity
        log_activity(
            db,
            event_type="product_duplicated",
            message=f"{new_product.name} duplicated from {source_product.name}",
            product_id=new_product.id,
            severity="info",
        )
        
        # Log audit
        log_audit(
            db,
            action="duplicate_product",
            resource_type="product",
            resource_id=new_product.id,
            resource_name=new_product.name,
            changes={
                "source_product_id": {"old": None, "new": source_product.id},
                "source_product_name": {"old": None, "new": source_product.name},
                "name": {"old": None, "new": new_product.name},
                "slug": {"old": None, "new": new_product.slug},
                "port": {"old": None, "new": new_product.port},
            },
            request=request,
            success=True,
        )
        
        # Return summary
        return {
            "id": new_product.id,
            "name": new_product.name,
            "slug": new_product.slug,
            "port": new_product.port,
            "replicas": new_product.replicas,
            "status": new_product.status,
            "image_name": new_product.image_name,
            "env_vars": new_product.env_vars,
            "created_at": new_product.created_at,
            "source_product_id": source_product.id,
            "source_product_name": source_product.name,
            "subscriptions_copied": subscriptions_copied,
        }
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to duplicate product: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database constraint violation: {str(e)}",
        )


@router.get("/{product_id}/logs")
def get_product_logs(
    product_id: int,
    tail: int = 100,
    current_user: UserSession = Depends(get_current_user),
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


@router.get("/{product_id}/logs/mqtt")
def get_mqtt_logs(
    product_id: int,
    tail: int = 500,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get MQTT-related logs (connections, subscriptions, events).
    
    Args:
        tail: Number of log lines to fetch before filtering (default 500, max 2000)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")
    
    if not product.service_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{product.name}' is not deployed")
    
    tail = min(tail, 2000)
    docker_manager = DockerManager()
    
    try:
        # Filter for MQTT-related log lines
        filter_pattern = r"(MQTT|mqtt|Connected|Subscribed|Received.*event|Starting MQTT listener)"
        logs = docker_manager.get_filtered_logs(product.service_id, filter_pattern, tail=tail)
        return {
            "product_id": product.id,
            "product_name": product.name,
            "log_type": "mqtt",
            "logs": logs,
        }
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service not found")


@router.get("/{product_id}/logs/events")
def get_event_logs(
    product_id: int,
    tail: int = 500,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get event processing logs (MQTT events, actions executed).
    
    Args:
        tail: Number of log lines to fetch before filtering (default 500, max 2000)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")
    
    if not product.service_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{product.name}' is not deployed")
    
    tail = min(tail, 2000)
    docker_manager = DockerManager()
    
    try:
        # Filter for event processing log lines
        filter_pattern = r"(event.*received|Executing action|action.*executed|Error executing action|Processing.*event)"
        logs = docker_manager.get_filtered_logs(product.service_id, filter_pattern, tail=tail)
        return {
            "product_id": product.id,
            "product_name": product.name,
            "log_type": "events",
            "logs": logs,
        }
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service not found")


@router.get("/{product_id}/logs/console")
def get_console_logs(
    product_id: int,
    tail: int = 200,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get console/application logs (startup, errors, warnings - excludes health checks and debug).
    
    Args:
        tail: Number of log lines to fetch before filtering (default 200, max 1000)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")
    
    if not product.service_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{product.name}' is not deployed")
    
    tail = min(tail, 1000)
    docker_manager = DockerManager()
    
    try:
        # Get all logs then filter out health checks and debug noise
        all_logs = docker_manager.get_service_logs(product.service_id, tail=tail)
        lines = all_logs.split('\n')
        
        # Exclude health checks, quote simulations, and other noise
        filtered_lines = [
            line for line in lines
            if not any(pattern in line for pattern in [
                'GET /health',
                '[AGE_DEBUG]',
                '[ENTITY_FILTER]',
                '[PAYMENT_BREAKDOWN]',
                '[DOC_SERVICE]',
            ])
        ]
        
        return {
            "product_id": product.id,
            "product_name": product.name,
            "log_type": "console",
            "logs": '\n'.join(filtered_lines),
        }
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service not found")
