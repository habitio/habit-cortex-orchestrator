"""Security utilities for Cortex Orchestrator."""

import secrets
from typing import Optional

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from orchestrator.database.models import Product


def generate_shared_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure shared key.
    
    Args:
        length: Length of the key in bytes (default 64 = 512 bits)
        
    Returns:
        Hexadecimal string representation of the key
    """
    return secrets.token_hex(length)


async def verify_shared_key(
    x_cortex_shared_key: Optional[str] = Header(None),
    db: Session = None,
    product_id: int = None
) -> Product:
    """
    Verify shared key from request header matches product's shared key.
    
    Args:
        x_cortex_shared_key: Shared key from request header
        db: Database session
        product_id: Expected product ID
        
    Returns:
        Product object if authentication successful
        
    Raises:
        HTTPException: If authentication fails
    """
    if not x_cortex_shared_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Cortex-Shared-Key header",
            headers={"WWW-Authenticate": "SharedKey"},
        )
    
    if not db or product_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid authentication setup",
        )
    
    # Find product by shared key
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.shared_key == x_cortex_shared_key
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid shared key or product ID",
        )
    
    return product


def is_shared_key_unique(db: Session, shared_key: str, exclude_product_id: Optional[int] = None) -> bool:
    """
    Check if a shared key is unique across all products.
    
    Args:
        db: Database session
        shared_key: Shared key to check
        exclude_product_id: Optional product ID to exclude from check (for updates)
        
    Returns:
        True if key is unique, False otherwise
    """
    query = db.query(Product).filter(Product.shared_key == shared_key)
    
    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)
    
    return query.first() is None
