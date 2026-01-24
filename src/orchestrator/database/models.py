"""SQLAlchemy database models for orchestrator."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, JSON, DateTime, ForeignKey, Integer, String, Text, func
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
    
    # Shared key for instance-to-orchestrator authentication (must be unique)
    shared_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    
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
    
    # Relationships
    subscriptions: Mapped[list["EventSubscription"]] = relationship(
        "EventSubscription",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    email_templates: Mapped[list["EmailTemplate"]] = relationship(
        "EmailTemplate",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    listmonk_templates: Mapped[list["ListMonkTemplate"]] = relationship(
        "ListMonkTemplate",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    sms_templates: Mapped[list["SMSTemplate"]] = relationship(
        "SMSTemplate",
        back_populates="product",
        cascade="all, delete-orphan"
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


class EventSubscription(Base):
    """Event subscription configuration for business events."""
    
    __tablename__ = "event_subscriptions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Event type (e.g., 'order.created', 'payment.completed')
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Actions configuration (JSON array of action objects)
    # Example: [{"type": "webhook", "url": "...", "method": "POST"}]
    actions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    
    # Execution statistics
    messages_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actions_executed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actions_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="subscriptions")
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "event_type": self.event_type,
            "enabled": bool(self.enabled),
            "description": self.description,
            "actions": self.actions or [],
            "stats": {
                "messages_received": self.messages_received,
                "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
                "actions_executed": self.actions_executed,
                "actions_failed": self.actions_failed,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailTemplate(Base):
    """
    Custom email template with subject and body content.
    
    Stores complete email content (subject, HTML body, plain text) with variable placeholders.
    Templates are product-specific and referenced in event subscription actions.
    """
    
    __tablename__ = "email_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Human-friendly name for UI
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Email content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)  # HTML content
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Plain text fallback
    
    # Optional description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Template type for categorization
    template_type: Mapped[str] = mapped_column(
        String(50),
        default="transactional",
        nullable=False
    )  # transactional, marketing, notification, system
    
    # Available variables (JSON array of variable names)
    available_variables: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    
    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="email_templates")
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.name,
            "subject": self.subject,
            "body_html": self.body_html,
            "body_text": self.body_text,
            "description": self.description,
            "template_type": self.template_type,
            "available_variables": self.available_variables or [],
            "stats": {
                "times_used": self.times_used,
                "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ListMonkTemplate(Base):
    """
    ListMonk template reference.
    
    Stores human-friendly template names that map to ListMonk template IDs.
    Templates are product-specific and referenced in event subscription actions.
    """
    
    __tablename__ = "listmonk_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Human-friendly name for UI
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # ListMonk template ID
    listmonk_template_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Optional description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Template type for categorization
    template_type: Mapped[str] = mapped_column(
        String(50),
        default="transactional",
        nullable=False
    )  # transactional, marketing, notification, system
    
    # Available variables (JSON array of variable names)
    available_variables: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    
    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="listmonk_templates")
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.name,
            "listmonk_template_id": self.listmonk_template_id,
            "description": self.description,
            "template_type": self.template_type,
            "available_variables": self.available_variables or [],
            "stats": {
                "times_used": self.times_used,
                "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SMSTemplate(Base):
    """
    SMS template configuration.
    
    Stores SMS message templates with variable placeholders.
    Templates are product-specific and referenced in event subscription actions.
    """
    
    __tablename__ = "sms_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Human-friendly name for UI
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # SMS message content (with {{variable}} placeholders)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Optional description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Template type for categorization
    template_type: Mapped[str] = mapped_column(
        String(50),
        default="transactional",
        nullable=False
    )  # transactional, marketing, notification, system
    
    # Available variables (JSON array of variable names)
    available_variables: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    
    # Character count (for SMS planning)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="sms_templates")
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.name,
            "message": self.message,
            "description": self.description,
            "template_type": self.template_type,
            "available_variables": self.available_variables or [],
            "char_count": self.char_count,
            "stats": {
                "times_used": self.times_used,
                "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSession(Base):
    """
    User authentication sessions for orchestrator UI.
    
    Stores access tokens from Habit Platform authentication.
    """
    
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    access_token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Store complete user data from Habit Platform
    user_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Session tracking
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<UserSession(email='{self.email}', last_login={self.last_login})>"


# Export all models
__all__ = [
    "Base",
    "OrchestratorSettings",
    "DockerImage",
    "Product",
    "ActivityLog",
    "AuditLog",
    "EventSubscription",
    "EmailTemplate",
    "ListMonkTemplate",
    "SMSTemplate",
    "UserSession",
]
