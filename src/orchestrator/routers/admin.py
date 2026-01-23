"""Admin API router for orchestrator configuration."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.database import get_db
from orchestrator.database.models import OrchestratorSettings, UserSession
from orchestrator.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# Pydantic schemas
class SettingsResponse(BaseModel):
    """Schema for settings response."""
    github_token: str | None
    github_default_repo: str
    updated_at: str

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    """Schema for updating settings."""
    github_token: str | None = Field(None, description="GitHub personal access token")
    github_default_repo: str | None = Field(None, description="Default GitHub repository")


# Helper function
def get_or_create_settings(db: Session) -> OrchestratorSettings:
    """Get or create the orchestrator settings record."""
    settings = db.query(OrchestratorSettings).filter(OrchestratorSettings.id == 1).first()
    
    if not settings:
        settings = OrchestratorSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


# Endpoints
@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get orchestrator configuration settings.
    
    Returns global settings like GitHub token, default repository, etc.
    """
    settings = get_or_create_settings(db)
    
    return SettingsResponse(
        github_token=settings.github_token,
        github_default_repo=settings.github_default_repo,
        updated_at=settings.updated_at.isoformat(),
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings(
    settings_update: SettingsUpdate,
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update orchestrator configuration settings.
    
    Updates global settings like GitHub token, default repository.
    Only provided fields will be updated.
    """
    settings = get_or_create_settings(db)
    
    # Update only provided fields
    if settings_update.github_token is not None:
        settings.github_token = settings_update.github_token
        logger.info("GitHub token updated")
    
    if settings_update.github_default_repo is not None:
        settings.github_default_repo = settings_update.github_default_repo
        logger.info(f"Default GitHub repo updated to: {settings_update.github_default_repo}")
    
    db.commit()
    db.refresh(settings)
    
    return SettingsResponse(
        github_token=settings.github_token,
        github_default_repo=settings.github_default_repo,
        updated_at=settings.updated_at.isoformat(),
    )


@router.delete("/settings/github-token", status_code=status.HTTP_204_NO_CONTENT)
def clear_github_token(
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear the GitHub token from settings.
    
    Useful for security purposes or when rotating tokens.
    """
    settings = get_or_create_settings(db)
    settings.github_token = None
    db.commit()
    
    logger.info("GitHub token cleared")
