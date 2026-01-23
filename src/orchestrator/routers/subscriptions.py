"""
Event Subscriptions API endpoints.

Manages business event subscriptions and actions for product instances.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.database import get_db, EventSubscription, Product
from orchestrator.database.models import UserSession
from orchestrator.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products/{product_id}/subscriptions", tags=["subscriptions"])


# Pydantic schemas
class ActionConfig(BaseModel):
    """Action configuration for a subscription."""
    type: str = Field(..., description="Action type (e.g., 'webhook', 'email', 'log')")
    config: dict = Field(default={}, description="Action-specific configuration")


class SubscriptionCreate(BaseModel):
    """Request model for creating a subscription."""
    event_type: str = Field(..., min_length=1, max_length=255, description="Business event type (e.g., 'order.created')")
    description: Optional[str] = Field(None, description="Human-readable description")
    enabled: bool = Field(default=True, description="Whether subscription is active")
    actions: list[dict] = Field(default=[], description="List of actions to execute")


class SubscriptionUpdate(BaseModel):
    """Request model for updating a subscription."""
    event_type: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    actions: Optional[list[dict]] = None


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


# Endpoints
@router.get("")
async def list_subscriptions(
    product_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of event subscriptions for a product.
    """
    product = get_product_or_404(db, product_id)
    
    subscriptions = db.query(EventSubscription).filter(
        EventSubscription.product_id == product_id
    ).all()
    
    return {
        "product_id": product_id,
        "product_name": product.name,
        "subscriptions": [sub.to_dict() for sub in subscriptions]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    product_id: int,
    subscription_data: SubscriptionCreate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new event subscription.
    """
    product = get_product_or_404(db, product_id)
    
    # Check for duplicate event_type
    existing = db.query(EventSubscription).filter(
        EventSubscription.product_id == product_id,
        EventSubscription.event_type == subscription_data.event_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subscription for event '{subscription_data.event_type}' already exists"
        )
    
    subscription = EventSubscription(
        product_id=product_id,
        event_type=subscription_data.event_type,
        description=subscription_data.description,
        enabled=subscription_data.enabled,
        actions=subscription_data.actions,
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"Created subscription {subscription.id} for product {product_id}")
    
    return subscription.to_dict()


@router.get("/{subscription_id}")
async def get_subscription(
    product_id: int,
    subscription_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific event subscription by ID.
    """
    product = get_product_or_404(db, product_id)
    
    subscription = db.query(EventSubscription).filter(
        EventSubscription.id == subscription_id,
        EventSubscription.product_id == product_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found"
        )
    
    return subscription.to_dict()


@router.put("/{subscription_id}")
async def update_subscription(
    product_id: int,
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a specific event subscription.
    """
    product = get_product_or_404(db, product_id)
    
    subscription = db.query(EventSubscription).filter(
        EventSubscription.id == subscription_id,
        EventSubscription.product_id == product_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found"
        )
    
    # Update fields if provided
    if subscription_data.event_type is not None:
        # Check for conflicts if changing event_type
        if subscription_data.event_type != subscription.event_type:
            existing = db.query(EventSubscription).filter(
                EventSubscription.product_id == product_id,
                EventSubscription.event_type == subscription_data.event_type
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Subscription for event '{subscription_data.event_type}' already exists"
                )
        subscription.event_type = subscription_data.event_type
    
    if subscription_data.description is not None:
        subscription.description = subscription_data.description
    
    if subscription_data.enabled is not None:
        subscription.enabled = subscription_data.enabled
    
    if subscription_data.actions is not None:
        subscription.actions = subscription_data.actions
    
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"Updated subscription {subscription_id} for product {product_id}")
    
    return subscription.to_dict()


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    product_id: int,
    subscription_id: int,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an event subscription.
    """
    product = get_product_or_404(db, product_id)
    
    subscription = db.query(EventSubscription).filter(
        EventSubscription.id == subscription_id,
        EventSubscription.product_id == product_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found"
        )
    
    db.delete(subscription)
    db.commit()
    
    logger.info(f"Deleted subscription {subscription_id} for product {product_id}")
