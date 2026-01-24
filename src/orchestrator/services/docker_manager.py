"""Docker Swarm orchestration service using Docker SDK."""

import logging
from typing import Any, Dict, List, Optional

import docker
from docker.errors import APIError, NotFound
from docker.models.services import Service
from docker.types import EndpointSpec, RestartPolicy, ServiceMode

from orchestrator.config import settings
from orchestrator.database.models import Product

logger = logging.getLogger(__name__)


class DockerManager:
    """
    Manages Docker Swarm services for product instances.
    
    Phase 1: All instances use same image and configuration.
    Only difference is PORT environment variable.
    """

    def __init__(self):
        """Initialize Docker client."""
        self.client = docker.DockerClient(base_url=settings.docker_host)
        self._ensure_network_exists()

    def _ensure_network_exists(self) -> None:
        """Ensure the Docker network for services exists."""
        try:
            self.client.networks.get(settings.docker_network)
            logger.info(f"Network '{settings.docker_network}' already exists")
        except NotFound:
            logger.info(f"Creating network '{settings.docker_network}'")
            self.client.networks.create(
                settings.docker_network,
                driver="overlay",
                attachable=True,
            )

    def create_service(self, product: Product) -> str:
        """
        Create and start a Docker Swarm service for a product.
        
        Args:
            product: Product instance to deploy
            
        Returns:
            Docker service ID
            
        Raises:
            APIError: If Docker API call fails
        """
        service_name = f"product-{product.slug}"
        
        # Use product-specific Docker image or fallback to default
        image = product.image_name if product.image_name else settings.instance_image
        
        # Use product-specific environment variables
        # Start with PORT (required for all products)
        env_vars = [f"PORT={product.port}"]
        
        # Add product-specific environment variables
        if product.env_vars:
            for key, value in product.env_vars.items():
                env_vars.append(f"{key}={value}")

        try:
            service = self.client.services.create(
                image=image,  # Use product's image instead of hardcoded
                name=service_name,
                env=env_vars,
                mode=ServiceMode("replicated", replicas=product.replicas),
                networks=[settings.docker_network],
                endpoint_spec=EndpointSpec(ports={product.port: 8000}),
                restart_policy=RestartPolicy(condition="on-failure", max_attempts=3),
                labels={
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "product_slug": product.slug,
                    "managed_by": "cortex-orchestrator",
                },
            )
            
            logger.info(
                f"Created service '{service_name}' (ID: {service.id}) "
                f"for product '{product.name}' (ID: {product.id}) "
                f"using image '{image}'"
            )
            
            return service.id

        except APIError as e:
            logger.error(f"Failed to create service for product '{product.name}': {e}")
            raise

    def remove_service(self, service_id: str) -> None:
        """
        Remove a Docker Swarm service.
        
        Args:
            service_id: Docker service ID to remove
            
        Raises:
            NotFound: If service doesn't exist
            APIError: If Docker API call fails
        """
        try:
            service = self.client.services.get(service_id)
            service_name = service.name
            service.remove()
            logger.info(f"Removed service '{service_name}' (ID: {service_id})")
        except NotFound:
            logger.warning(f"Service {service_id} not found (already removed?)")
            raise
        except APIError as e:
            logger.error(f"Failed to remove service {service_id}: {e}")
            raise

    def scale_service(self, service_id: str, replicas: int) -> None:
        """
        Scale a Docker Swarm service to specified number of replicas.
        
        Args:
            service_id: Docker service ID to scale
            replicas: Target number of replicas
            
        Raises:
            NotFound: If service doesn't exist
            APIError: If Docker API call fails
        """
        try:
            service = self.client.services.get(service_id)
            service.scale(replicas)
            logger.info(f"Scaled service '{service.name}' to {replicas} replicas")
        except NotFound:
            logger.error(f"Service {service_id} not found")
            raise
        except APIError as e:
            logger.error(f"Failed to scale service {service_id}: {e}")
            raise

    def get_service_status(self, service_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a Docker Swarm service.
        
        Args:
            service_id: Docker service ID
            
        Returns:
            Dictionary with service status information
            
        Raises:
            NotFound: If service doesn't exist
        """
        try:
            service = self.client.services.get(service_id)
            tasks = service.tasks()
            
            running_tasks = [t for t in tasks if t.get("Status", {}).get("State") == "running"]
            
            return {
                "service_id": service.id,
                "service_name": service.name,
                "replicas_desired": len(tasks),
                "replicas_running": len(running_tasks),
                "image": service.attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"],
                "created_at": service.attrs["CreatedAt"],
                "updated_at": service.attrs["UpdatedAt"],
                "tasks": [
                    {
                        "id": task["ID"],
                        "state": task.get("Status", {}).get("State"),
                        "desired_state": task.get("DesiredState"),
                        "node_id": task.get("NodeID"),
                    }
                    for task in tasks
                ],
            }
        except NotFound:
            logger.error(f"Service {service_id} not found")
            raise

    def list_services(self) -> List[Dict[str, Any]]:
        """
        List all services managed by orchestrator.
        
        Returns:
            List of service information dictionaries
        """
        services = self.client.services.list(
            filters={"label": "managed_by=cortex-orchestrator"}
        )
        
        return [
            {
                "service_id": service.id,
                "service_name": service.name,
                "product_id": service.attrs["Spec"]["Labels"].get("product_id"),
                "product_name": service.attrs["Spec"]["Labels"].get("product_name"),
                "replicas": len(service.tasks()),
            }
            for service in services
        ]

    def health_check(self) -> bool:
        """
        Check if Docker daemon is reachable and Swarm is active.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            info = self.client.info()
            return info.get("Swarm", {}).get("LocalNodeState") == "active"
        except Exception as e:
            logger.error(f"Docker health check failed: {e}")
            return False

    def get_service_logs(self, service_id: str, tail: int = 100) -> str:
        """
        Get logs from a Docker service.
        
        Args:
            service_id: Docker service ID
            tail: Number of lines to return from the end
            
        Returns:
            Service logs as string
            
        Raises:
            NotFound: If service doesn't exist
            APIError: If Docker API call fails
        """
        try:
            service = self.client.services.get(service_id)
            logs = service.logs(
                stdout=True,
                stderr=True,
                tail=tail,
                timestamps=True,
            )
            # Decode bytes to string
            if isinstance(logs, bytes):
                return logs.decode('utf-8', errors='replace')
            return ''.join([chunk.decode('utf-8', errors='replace') for chunk in logs])
        except NotFound:
            logger.warning(f"Service {service_id} not found")
            raise
        except APIError as e:
            logger.error(f"Failed to get logs for service {service_id}: {e}")
            raise
    
    def stream_service_logs(self, service_id: str, tail: int = 100):
        """
        Stream logs from a Docker service (generator for SSE).
        
        Args:
            service_id: Docker service ID
            tail: Number of lines to return from the end initially
            
        Yields:
            Log lines as they arrive
            
        Raises:
            NotFound: If service doesn't exist
            APIError: If Docker API call fails
        """
        try:
            service = self.client.services.get(service_id)
            # follow=True automatically returns a generator/stream
            logs = service.logs(
                stdout=True,
                stderr=True,
                tail=tail,
                follow=True,  # Stream new logs (returns generator)
                timestamps=True,
            )
            
            for chunk in logs:
                if isinstance(chunk, bytes):
                    yield chunk.decode('utf-8', errors='replace')
                else:
                    yield chunk
                    
        except NotFound:
            logger.warning(f"Service {service_id} not found")
            raise
        except APIError as e:
            logger.error(f"Failed to stream logs for service {service_id}: {e}")
            raise

    def get_filtered_logs(self, service_id: str, filter_pattern: str, tail: int = 100) -> str:
        """
        Get logs from a Docker service with grep-like filtering.
        
        Args:
            service_id: Docker service ID
            filter_pattern: Regex pattern to filter log lines
            tail: Number of lines to return from the end (before filtering)
            
        Returns:
            Filtered service logs as string
        """
        import re
        
        try:
            all_logs = self.get_service_logs(service_id, tail=tail)
            lines = all_logs.split('\n')
            
            # Filter lines matching pattern (case-insensitive)
            filtered_lines = [
                line for line in lines 
                if re.search(filter_pattern, line, re.IGNORECASE)
            ]
            
            return '\n'.join(filtered_lines)
        except Exception as e:
            logger.error(f"Failed to filter logs for service {service_id}: {e}")
            raise
