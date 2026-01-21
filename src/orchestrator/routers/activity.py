"""Activity log endpoints for operational events."""

import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from orchestrator.database import ActivityLog, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


# Pydantic schemas
class ActivityResponse(BaseModel):
    """Schema for activity log response."""
    id: int
    product_id: int | None
    product_name: str | None
    event_type: str
    message: str
    severity: str
    event_metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[ActivityResponse])
def list_activity(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of events to return"),
    product_id: int | None = Query(default=None, description="Filter by product ID"),
    severity: str | None = Query(default=None, description="Filter by severity (info, warning, error)"),
    event_type: str | None = Query(default=None, description="Filter by event type"),
    hours: int | None = Query(default=None, ge=1, le=168, description="Only show events from last N hours"),
    db: Session = Depends(get_db),
):
    """
    Retrieve recent activity logs.
    
    Returns operational events in reverse chronological order (newest first).
    Used for dashboard "Recent Activity" widget.
    
    **Query Parameters:**
    - `limit`: Max number of events (1-100, default 20)
    - `product_id`: Filter by specific product
    - `severity`: Filter by severity (info, warning, error)
    - `event_type`: Filter by event type (product_started, health_check_failed, etc.)
    - `hours`: Only show events from last N hours
    
    **Example:**
    ```
    GET /api/v1/activity?limit=10&severity=error
    GET /api/v1/activity?product_id=5&hours=24
    ```
    """
    query = db.query(ActivityLog)
    
    # Apply filters
    if product_id is not None:
        query = query.filter(ActivityLog.product_id == product_id)
    
    if severity:
        query = query.filter(ActivityLog.severity == severity.lower())
    
    if event_type:
        query = query.filter(ActivityLog.event_type == event_type)
    
    if hours:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(ActivityLog.created_at >= cutoff_time)
    
    # Order by newest first and apply limit
    activities = query.order_by(desc(ActivityLog.created_at)).limit(limit).all()
    
    # Enrich with product names
    result = []
    for activity in activities:
        activity_dict = {
            "id": activity.id,
            "product_id": activity.product_id,
            "product_name": activity.product.name if activity.product else None,
            "event_type": activity.event_type,
            "message": activity.message,
            "severity": activity.severity,
            "event_metadata": activity.event_metadata,
            "created_at": activity.created_at,
        }
        result.append(ActivityResponse(**activity_dict))
    
    logger.info(f"Retrieved {len(result)} activity log entries")
    return result
