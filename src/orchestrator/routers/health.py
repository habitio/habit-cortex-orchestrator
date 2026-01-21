"""Health check endpoints."""

from fastapi import APIRouter

from orchestrator.services.docker_manager import DockerManager

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Health check endpoint.
    
    Returns service health status and Docker Swarm connectivity.
    """
    try:
        docker_manager = DockerManager()
        docker_healthy = docker_manager.health_check()
    except Exception:
        docker_healthy = False
    
    return {
        "status": "healthy" if docker_healthy else "degraded",
        "service": "cortex-orchestrator",
        "version": "0.1.0",
        "docker_swarm": "connected" if docker_healthy else "disconnected",
    }
