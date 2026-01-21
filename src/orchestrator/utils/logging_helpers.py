"""Helper utilities for activity and audit logging."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from orchestrator.database import ActivityLog, AuditLog

logger = logging.getLogger(__name__)


def log_activity(
    db: Session,
    event_type: str,
    message: str,
    product_id: Optional[int] = None,
    severity: str = "info",
    event_metadata: Optional[Dict[str, Any]] = None,
) -> ActivityLog:
    """
    Create an activity log entry for operational events.
    
    Args:
        db: Database session
        event_type: Type of event (product_started, health_check_failed, etc.)
        message: Human-readable message for UI display
        product_id: Optional product ID this event relates to
        severity: Event severity (info, warning, error)
        event_metadata: Optional additional context (dict)
    
    Returns:
        Created ActivityLog instance
    
    Example:
        log_activity(
            db,
            event_type="product_scaled",
            message="Pet Insurance scaled to 3 replicas",
            product_id=5,
            severity="info",
            event_metadata={"old_replicas": 1, "new_replicas": 3}
        )
    """
    activity = ActivityLog(
        product_id=product_id,
        event_type=event_type,
        message=message,
        severity=severity.lower(),
        event_metadata=event_metadata or {},
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    logger.info(f"Activity logged: {event_type} - {message}")
    return activity


def log_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    resource_name: Optional[str] = None,
    changes: Optional[Dict[str, Dict[str, Any]]] = None,
    user_id: Optional[str] = None,
    request: Optional[Request] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> AuditLog:
    """
    Create an audit log entry for compliance and security tracking.
    
    Args:
        db: Database session
        action: Action performed (create_product, update_product, etc.)
        resource_type: Type of resource (product, orchestrator_settings, docker_image)
        resource_id: ID of the affected resource
        resource_name: Name of the affected resource
        changes: Dict of changes in format {"field": {"old": value1, "new": value2}}
        user_id: User who performed the action (future: from auth token)
        request: FastAPI Request object to extract IP and user agent
        success: Whether the action succeeded
        error_message: Error message if action failed
    
    Returns:
        Created AuditLog instance
    
    Example:
        log_audit(
            db,
            action="update_product",
            resource_type="product",
            resource_id=5,
            resource_name="Pet Insurance",
            changes={
                "replicas": {"old": 1, "new": 3},
                "status": {"old": "running", "new": "running"}
            },
            request=request,
            success=True
        )
    """
    # Extract request metadata if provided
    ip_address = None
    user_agent = None
    if request:
        # Get real IP (considering proxies)
        ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip_address:
            ip_address = request.headers.get("X-Real-IP")
        if not ip_address and request.client:
            ip_address = request.client.host
        
        user_agent = request.headers.get("User-Agent")
    
    audit = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        changes=changes or {},
        user_id=user_id or "system",  # Default to "system" until auth is implemented
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    
    logger.info(f"Audit logged: {action} on {resource_type}:{resource_id} by {user_id or 'system'}")
    return audit


def calculate_changes(old_obj: Any, new_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate changes between old object and new data.
    
    Args:
        old_obj: SQLAlchemy model instance (before changes)
        new_data: Dict of new values
    
    Returns:
        Dict in format {"field": {"old": value1, "new": value2}}
    
    Example:
        old_product = db.query(Product).get(1)
        new_data = {"replicas": 3, "name": "Updated Name"}
        changes = calculate_changes(old_product, new_data)
        # Returns: {"replicas": {"old": 1, "new": 3}, "name": {"old": "Old Name", "new": "Updated Name"}}
    """
    changes = {}
    
    for field, new_value in new_data.items():
        if hasattr(old_obj, field):
            old_value = getattr(old_obj, field)
            
            # Skip if values are identical
            if old_value == new_value:
                continue
            
            # Handle special cases
            if field in ["env_vars", "metadata", "changes"]:
                # For JSON fields, do deep comparison
                if old_value != new_value:
                    changes[field] = {
                        "old": old_value,
                        "new": new_value,
                    }
            elif field in ["password", "token", "secret", "github_token"]:
                # Mask sensitive fields
                changes[field] = {
                    "old": "***REDACTED***" if old_value else None,
                    "new": "***REDACTED***" if new_value else None,
                }
            else:
                changes[field] = {
                    "old": old_value,
                    "new": new_value,
                }
    
    return changes
