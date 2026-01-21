"""Audit log endpoints for compliance and security tracking."""

import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from orchestrator.database import AuditLog, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# Pydantic schemas
class AuditResponse(BaseModel):
    """Schema for audit log response."""
    id: int
    action: str
    resource_type: str
    resource_id: int | None
    resource_name: str | None
    changes: dict | None
    user_id: str | None
    ip_address: str | None
    user_agent: str | None
    success: bool
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[AuditResponse])
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of audit entries to return"),
    resource_type: str | None = Query(default=None, description="Filter by resource type (product, orchestrator_settings, docker_image)"),
    resource_id: int | None = Query(default=None, description="Filter by specific resource ID"),
    action: str | None = Query(default=None, description="Filter by action (create_product, update_product, etc.)"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    success: bool | None = Query(default=None, description="Filter by success/failure"),
    start_date: datetime | None = Query(default=None, description="Start date for filtering (ISO 8601)"),
    end_date: datetime | None = Query(default=None, description="End date for filtering (ISO 8601)"),
    days: int | None = Query(default=None, ge=1, le=365, description="Only show audit logs from last N days"),
    db: Session = Depends(get_db),
):
    """
    Retrieve audit logs for compliance and security tracking.
    
    Returns comprehensive audit trail with before/after values, user information,
    and request metadata. Used for compliance reports, security investigations,
    and debugging configuration changes.
    
    **Query Parameters:**
    - `limit`: Max number of entries (1-500, default 50)
    - `resource_type`: Filter by resource (product, orchestrator_settings, docker_image)
    - `resource_id`: Filter by specific resource ID
    - `action`: Filter by action (create_product, update_product, delete_product, etc.)
    - `user_id`: Filter by user ID
    - `success`: Filter by success (true) or failure (false)
    - `start_date`: Start date (ISO 8601 format)
    - `end_date`: End date (ISO 8601 format)
    - `days`: Only show logs from last N days
    
    **Examples:**
    ```
    GET /api/v1/audit?resource_type=product&resource_id=5
    GET /api/v1/audit?action=update_product&days=7
    GET /api/v1/audit?success=false&limit=100
    GET /api/v1/audit?start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T23:59:59Z
    ```
    """
    query = db.query(AuditLog)
    
    # Apply filters
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    if resource_id is not None:
        query = query.filter(AuditLog.resource_id == resource_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if success is not None:
        query = query.filter(AuditLog.success == success)
    
    # Date filtering
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.created_at >= cutoff_date)
    
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    # Order by newest first and apply limit
    audit_logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    logger.info(f"Retrieved {len(audit_logs)} audit log entries")
    return audit_logs
