"""SQLAlchemy database models for orchestrator."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class OrchestratorSettings(Base):
    """
    Orchestrator-level configuration settings.
    
    Stores global settings like GitHub token, default repos, etc.
    Key-value store with single row (id=1).
    """
    
    __tablename__ = "orchestrator_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    
    # GitHub Integration
    github_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_default_repo: Mapped[str] = mapped_column(
        String(255), 
        default="habitio/bre-cortex", 
        nullable=False
    )
    
    # Audit
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        token_masked = f"{self.github_token[:10]}..." if self.github_token else None
        return f"<OrchestratorSettings(github_token='{token_masked}', default_repo='{self.github_default_repo}')>"


class DockerImage(Base):
    """
    Docker image built from GitHub repository.
    """
    
    __tablename__ = "docker_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    github_repo: Mapped[str] = mapped_column(String(255), nullable=False)
    github_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    
    build_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )  # pending, building, success, failed
    
    build_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    build_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    built_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DockerImage(id={self.id}, name='{self.name}', tag='{self.tag}', status='{self.build_status}')>"


class Product(Base):
    """
    Product instance definition.
    
    Each product instance has its own environment variables for deployment.
    """
    
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    replicas: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="stopped",
        nullable=False,
    )  # stopped, starting, running, stopping, failed
    
    # Environment variables (stored as JSON key-value pairs)
    env_vars: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Docker image reference (which image to deploy)
    image_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('docker_images.id'), nullable=True)
    image_name: Mapped[str] = mapped_column(String(255), default='bre-payments:latest', nullable=False)
    
    # Docker service info (populated when deployed)
    service_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', slug='{self.slug}', status='{self.status}')>"


class ActivityLog(Base):
    """
    Activity log for user-facing operational events.
    
    Tracks high-level events like product starts/stops, health check failures,
    scaling operations, etc. Used for dashboard "Recent Activity" display.
    """
    
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('products.id'), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Event types: product_created, product_started, product_stopped, product_scaled,
    # product_deleted, health_check_failed, service_restarted, image_build_completed, etc.
    
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20),
        default="info",
        nullable=False,
    )  # info, warning, error
    
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Additional context: old_replicas, new_replicas, error_details, etc.
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationship
    product: Mapped[Optional["Product"]] = relationship("Product")

    def __repr__(self) -> str:
        return f"<ActivityLog(id={self.id}, event='{self.event_type}', product_id={self.product_id})>"


class AuditLog(Base):
    """
    Comprehensive audit trail for compliance and security.
    
    Tracks all changes to products, settings, and configurations with
    before/after values, user information, and request metadata.
    """
    
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Actions: create_product, update_product, delete_product, start_product, stop_product,
    # scale_product, update_settings, delete_github_token, build_image, etc.
    
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Resource types: product, orchestrator_settings, docker_image
    
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    resource_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Change tracking
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Format: {"field": {"old": "value1", "new": "value2"}, ...}
    
    # User/request information
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # TODO: Implement authentication and populate with actual user ID
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    # IPv4 (15 chars) or IPv6 (45 chars)
    
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Result
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}:{self.resource_id}')>"
