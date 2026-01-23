"""
Instance API Endpoints.

Public endpoints for product instances to fetch their configuration using shared key.
These endpoints do NOT require user authentication - they use X-Cortex-Shared-Key header.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import Depends

from orchestrator.database import get_db, Product, EventSubscription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/instance", tags=["instance"])


def verify_shared_key(
    product_id: int,
    x_cortex_shared_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Product:
    """
    Verify shared key and return product.
    
    Args:
        product_id: Product ID from path
        x_cortex_shared_key: Shared key from header
        db: Database session
        
    Returns:
        Product: Verified product instance
        
    Raises:
        HTTPException: If key is missing or invalid
    """
    if not x_cortex_shared_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Cortex-Shared-Key header"
        )
    
    # Get product and verify shared key
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    # Get shared key from product env_vars
    expected_key = product.env_vars.get("CORTEX_API_SHARED_KEY") if product.env_vars else None
    
    if not expected_key:
        logger.error(f"Product {product_id} has no CORTEX_API_SHARED_KEY configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Product shared key not configured"
        )
    
    if x_cortex_shared_key != expected_key:
        logger.warning(f"Invalid shared key attempt for product {product_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid shared key"
        )
    
    return product


@router.get("/products/{product_id}/subscriptions")
async def get_instance_subscriptions(
    product: Product = Depends(verify_shared_key),
    db: Session = Depends(get_db)
):
    """
    Get event subscriptions for a product instance.
    
    This endpoint is called by product instances using their shared key.
    Returns enabled subscriptions with their actions.
    
    **Authentication:** X-Cortex-Shared-Key header (not user session)
    
    Args:
        product: Verified product from shared key
        db: Database session
        
    Returns:
        dict: Event subscriptions configuration
    """
    # Get all subscriptions for this product
    subscriptions = db.query(EventSubscription)\
        .filter(EventSubscription.product_id == product.id)\
        .order_by(EventSubscription.event_type)\
        .all()
    
    # Convert to dict format
    subscriptions_list = []
    for sub in subscriptions:
        sub_dict = sub.to_dict()
        subscriptions_list.append(sub_dict)
    
    # Get MQTT settings from product env_vars
    env_vars = product.env_vars or {}
    mqtt_config = {
        "host": env_vars.get("MQTT_HOST"),
        "port": int(env_vars.get("MQTT_PORT", 1883)),
        "use_tls": env_vars.get("MQTT_USE_TLS", "false").lower() == "true",
        "username": env_vars.get("MQTT_USERNAME"),
        "password": env_vars.get("MQTT_PASSWORD"),
        "topic_prefix": env_vars.get("MQTT_TOPIC_PREFIX", "/v3/applications"),
        "shared_group": env_vars.get("MQTT_SHARED_GROUP", "bre"),
    }
    
    # Get application_id for topic construction
    application_id = env_vars.get("APPLICATION_ID")
    
    logger.info(f"Instance API: Product {product.id} fetched {len(subscriptions_list)} subscriptions")
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "mqtt_config": mqtt_config,
        "application_id": application_id,
        "subscriptions": subscriptions_list,
        "total_subscriptions": len(subscriptions_list),
        "enabled_subscriptions": len([s for s in subscriptions_list if s.get("enabled")])
    }


@router.get("/products/{product_id}/mqtt-config")
async def get_instance_mqtt_config_legacy(
    product: Product = Depends(verify_shared_key),
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint for backward compatibility.
    
    Returns MQTT configuration in the old format expected by existing instances.
    Redirects to new subscriptions format internally.
    
    **Deprecated:** Use /instance/products/{id}/subscriptions instead
    
    **Authentication:** X-Cortex-Shared-Key header
    """
    # Get subscriptions using new endpoint
    subscriptions_data = await get_instance_subscriptions(product=product, db=db)
    
    # Convert to legacy format
    mqtt_config_data = subscriptions_data["mqtt_config"]
    subscriptions_list = subscriptions_data["subscriptions"]
    
    # Legacy format structure
    legacy_format = {
        "mqtt_config": {
            "id": product.id,
            "product_id": product.id,
            "broker": {
                "host": mqtt_config_data["host"],
                "port": mqtt_config_data["port"],
                "use_tls": mqtt_config_data["use_tls"],
                "username": mqtt_config_data["username"],
                "password": mqtt_config_data["password"],
            },
            "topics": {
                "prefix": mqtt_config_data["topic_prefix"],
                "pattern": f"{{{subscriptions_data['application_id']}}}/business-events" if subscriptions_data['application_id'] else "{application_id}/business-events",
                "use_shared": True,
                "shared_group": mqtt_config_data["shared_group"],
                "qos": 1
            }
        },
        "subscriptions": [
            {
                "id": sub["id"],
                "name": sub["event_type"],  # Map event_type to name for legacy
                "topic": f"{mqtt_config_data['topic_prefix']}/{subscriptions_data['application_id']}/business-events/{sub['event_type']}",
                "enabled": sub["enabled"],
                "description": sub["description"],
                "actions": sub["actions"]
            }
            for sub in subscriptions_list
        ]
    }
    
    logger.info(f"Instance API (legacy): Product {product.id} fetched MQTT config")
    
    return legacy_format
