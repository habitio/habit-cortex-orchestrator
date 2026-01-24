"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.config import settings
from orchestrator.database import Base, engine
from orchestrator.routers import health_router, products_router
from orchestrator.routers.activity import router as activity_router
from orchestrator.routers.admin import router as admin_router
from orchestrator.routers.audit import router as audit_router
from orchestrator.routers.auth import router as auth_router
from orchestrator.routers.images import router as images_router
from orchestrator.routers.instance_api import router as instance_api_router
from orchestrator.routers.schema import router as schema_router
from orchestrator.routers.subscriptions import router as subscriptions_router
from orchestrator.routers.templates import router as templates_router

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Habit BRE Cortex Orchestrator",
    description="Multi-product orchestration and management service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins is ["*"]
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to client
)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(instance_api_router)  # Public API for instances (shared key auth)
app.include_router(products_router)
app.include_router(subscriptions_router)
app.include_router(templates_router)
app.include_router(schema_router)  # Schema/metadata for UI
app.include_router(images_router)
app.include_router(admin_router)
app.include_router(activity_router)
app.include_router(audit_router)


@app.on_event("startup")
async def startup_event():
    """Application startup: create database tables."""
    logger.info("Starting Cortex Orchestrator...")
    logger.info(f"Database URL: {settings.database_url}")
    logger.info(f"Docker Host: {settings.docker_host}")
    logger.info(f"API Port: {settings.api_port}")
    
    # Create tables (in production, use Alembic migrations)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    logger.info("Cortex Orchestrator started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown cleanup."""
    logger.info("Shutting down Cortex Orchestrator...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "cortex-orchestrator",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


def run():
    """Run the application with uvicorn."""
    import uvicorn
    
    uvicorn_config = {
        "host": settings.api_host,
        "port": settings.api_port,
        "reload": settings.api_reload,
        "log_level": settings.log_level.lower(),
    }
    
    # Add SSL configuration if certificates are provided
    if settings.ssl_cert_file and settings.ssl_key_file:
        logger.info(f"HTTPS enabled with cert: {settings.ssl_cert_file}")
        uvicorn_config["ssl_certfile"] = settings.ssl_cert_file
        uvicorn_config["ssl_keyfile"] = settings.ssl_key_file
    else:
        logger.warning("Running in HTTP mode (no SSL certificates configured)")
    
    uvicorn.run(
        "orchestrator.main:app",
        **uvicorn_config,
    )


if __name__ == "__main__":
    run()
