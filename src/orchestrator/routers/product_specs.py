"""
Product specification endpoints (read-only).

These endpoints proxy requests to the instance, which fetches specs from Habit Platform.
This is a read-only implementation - no create/update/delete operations.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from orchestrator.database import Product, UserSession, get_db
from orchestrator.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products/{product_id}/specs", tags=["product-specs"])


async def _get_instance_url(product_id: int, db: Session) -> str:
    """
    Get the instance URL for a product.
    
    Args:
        product_id: Product ID
        db: Database session
        
    Returns:
        Instance URL (e.g., http://localhost:8001)
        
    Raises:
        HTTPException: If product not found or not deployed
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if not product.service_id or product.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is not running. Deploy it first."
        )
    
    # Instance URL uses the product's port
    return f"http://localhost:{product.port}"


async def _proxy_to_instance(
    instance_url: str,
    endpoint: str,
    method: str = "GET",
    **kwargs
) -> dict[str, Any]:
    """
    Proxy request to instance.
    
    Args:
        instance_url: Instance base URL
        endpoint: Endpoint path (e.g., /internal/habit-specs/list)
        method: HTTP method
        **kwargs: Additional httpx request parameters
        
    Returns:
        Response JSON from instance
        
    Raises:
        HTTPException: If instance request fails
    """
    url = f"{instance_url}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Proxying {method} request to instance: {url}")
            
            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "DELETE":
                response = await client.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Instance returned error {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Instance error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.exception(f"Failed to connect to instance: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to product instance: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error proxying to instance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to proxy request: {str(e)}"
        )


@router.get("/list")
async def list_product_specs(
    product_id: int,
    db: Session = Depends(get_db),
    _current_user: UserSession = Depends(get_current_user)
) -> dict[str, Any]:
    """
    List all product specifications from Habit Platform.
    
    This endpoint proxies the request to the product instance, which fetches
    specs from Habit Platform.
    
    Args:
        product_id: Product ID
        
    Returns:
        Dictionary containing:
        - product_id: Product ID
        - product_name: Product name
        - specs: List of spec summaries with metadata
        - total_specs: Total number of specs
        
    Example response:
        {
            "product_id": 2,
            "product_name": "Tyres Protection PT",
            "specs": [
                {
                    "spec_id": 1,
                    "name": "Standard Coverage",
                    "version": "1.2",
                    "is_active": true,
                    "status": "valid",
                    "completeness_score": 95,
                    "summary": {
                        "simulate_configured": true,
                        "checkout_configured": true,
                        "pricing_formulas": 3
                    }
                }
            ],
            "total_specs": 1
        }
    """
    # Get product info for context
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if not product.service_id or product.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is not running. Deploy it first."
        )
    
    # Proxy to instance
    instance_url = f"http://localhost:{product.port}"
    services_data = await _proxy_to_instance(instance_url, "/internal/habit-specs/list")
    
    # Add product context to Habit Platform response
    return {
        "product_id": product.id,
        "product_name": product.name,
        **services_data  # Spread complete Habit Platform services response (elements, size, etc.)
    }


@router.get("/{spec_id}")
async def get_product_spec(
    product_id: int,
    spec_id: str,
    db: Session = Depends(get_db),
    _current_user: UserSession = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Get detailed product specification from Habit Platform.
    
    This endpoint proxies the request to the product instance, which fetches
    the specific spec from Habit Platform.
    
    Args:
        product_id: Product ID
        spec_id: Specification ID
        
    Returns:
        Dictionary containing:
        - spec_id: Spec ID
        - name: Spec name
        - description: Spec description
        - version: Spec version
        - is_active: Whether spec is currently active
        - configuration: Full spec configuration (simulate, checkout, etc.)
        - validation: Validation results (errors, warnings, completeness)
        - history: Version history
        
    Example response:
        {
            "spec_id": 1,
            "name": "Standard Coverage",
            "version": "1.2",
            "is_active": true,
            "configuration": {
                "version": "1.0",
                "product": "bre-tyres",
                "simulate": {
                    "required_fields": [...],
                    "pricing_formula": {...}
                },
                "checkout": {
                    "required_fields": [...],
                    "quote_properties": {...}
                }
            },
            "validation": {
                "is_valid": true,
                "errors": [],
                "warnings": [],
                "completeness_score": 95
            },
            "history": [...]
        }
    """
    instance_url = await _get_instance_url(product_id, db)
    return await _proxy_to_instance(instance_url, f"/internal/habit-specs/{spec_id}")


@router.get("/{service_id}/quote-specs")
async def get_service_quote_specs(
    product_id: int,
    service_id: str,
    db: Session = Depends(get_db),
    _current_user: UserSession = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Get quote-specs for a specific service from Habit Platform.
    
    This endpoint returns the raw quote-specs structure from Habit Platform,
    including all property specifications for quotes, insurees, and protected assets.
    
    Args:
        product_id: Product ID
        service_id: Service/spec UUID
        
    Returns:
        Dictionary containing:
        - quotepropertyspecs: Array of quote property specifications
        - insureepropertyspecs: Array of insuree property specifications
        - protectedassetpropertyspecs: Array of protected asset property specifications
        
    Each property spec includes:
        - namespace: Property identifier (e.g., "num_tyres", "coverage_level")
        - classes: Array of class identifiers (e.g., "io.habit.operations.required.quotes.simulate")
        - options: Array of allowed values (if applicable)
        - label: Human-readable label
        
    Example response:
        {
            "quotepropertyspecs": [
                {
                    "namespace": "num_tyres",
                    "label": "Number of Tyres",
                    "classes": ["io.habit.operations.required.quotes.simulate"],
                    "options": [
                        {"data": 2, "label": "2 tyres"},
                        {"data": 4, "label": "4 tyres"}
                    ]
                }
            ],
            "insureepropertyspecs": [...],
            "protectedassetpropertyspecs": [...]
        }
    """
    instance_url = await _get_instance_url(product_id, db)
    
    # Add product context to response
    product = db.query(Product).filter(Product.id == product_id).first()
    
    specs_data = await _proxy_to_instance(
        instance_url, 
        f"/internal/habit-specs/{service_id}/quote-specs"
    )
    
    return {
        "product_id": product_id,
        "product_name": product.name,
        "service_id": service_id,
        **specs_data
    }
