"""Docker image building service."""

import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Callable

import docker
from docker.errors import APIError, BuildError

from orchestrator.services.github_service import GitHubService

logger = logging.getLogger(__name__)


class ImageBuildService:
    """Service for building Docker images from GitHub repositories."""
    
    def __init__(self, github_token: str | None = None):
        """
        Initialize Docker client and GitHub service.
        
        Args:
            github_token: Optional GitHub token for private repo access
        """
        self.docker_client = docker.from_env()
        self.github_service = GitHubService(token=github_token)
    
    def build_from_github(
        self,
        repo: str,
        tag: str,
        commit_sha: str,
        image_name: str,
        dockerfile_path: str = "Dockerfile",
        log_callback: Callable[[str], None] | None = None,
    ) -> tuple[bool, str, str | None]:
        """
        Build a Docker image from a GitHub repository.
        
        Args:
            repo: GitHub repository (owner/repo)
            tag: Git tag to build from
            commit_sha: Commit SHA for verification
            image_name: Full image name with tag (e.g., "bre-payments:v1.2.3")
            dockerfile_path: Path to Dockerfile relative to repo root (e.g., "Dockerfile" or "cortex-orchestrator/Dockerfile")
            log_callback: Optional callback function to receive build logs
            
        Returns:
            Tuple of (success: bool, logs: str, error: str | None)
        """
        temp_dir = None
        build_logs = []
        
        def log(message: str):
            """Helper to collect logs and optionally call callback."""
            build_logs.append(message)
            if log_callback:
                log_callback(message)
            logger.info(message)
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="docker-build-")
            temp_path = Path(temp_dir)
            tarball_path = temp_path / "repo.tar.gz"
            
            log(f"Downloading {repo}@{tag} from GitHub...")
            
            # Download repository tarball
            self.github_service.download_tarball(repo, tag, str(tarball_path))
            
            log("Extracting repository...")
            
            # Extract tarball
            with tarfile.open(tarball_path, 'r:gz') as tar:
                tar.extractall(temp_path)
            
            # GitHub tarballs extract to a directory like "owner-repo-sha"
            # Find the extracted directory
            extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise Exception("No directory found in extracted tarball")
            
            repo_root = extracted_dirs[0]
            
            # Parse dockerfile_path to determine build context and dockerfile name
            dockerfile_parts = Path(dockerfile_path).parts
            if len(dockerfile_parts) > 1:
                # Dockerfile is in subdirectory (e.g., "cortex-orchestrator/Dockerfile")
                build_context = repo_root / Path(*dockerfile_parts[:-1])
                dockerfile_name = dockerfile_parts[-1]
            else:
                # Dockerfile is in root
                build_context = repo_root
                dockerfile_name = dockerfile_path
            
            # Verify Dockerfile exists
            full_dockerfile_path = build_context / dockerfile_name
            if not full_dockerfile_path.exists():
                # List available paths for debugging
                available_paths = list(repo_root.rglob("Dockerfile"))
                error_msg = f"Dockerfile not found at {full_dockerfile_path}."
                if available_paths:
                    relative_paths = [str(p.relative_to(repo_root)) for p in available_paths]
                    error_msg += f" Found Dockerfiles at: {', '.join(relative_paths)}"
                else:
                    error_msg += " No Dockerfiles found in repository."
                raise Exception(error_msg)
            
            log(f"Building Docker image: {image_name}")
            log(f"Build context: {build_context}")
            log(f"Dockerfile: {dockerfile_name}")
            
            # Build the image
            image, build_log = self.docker_client.images.build(
                path=str(build_context),
                dockerfile=dockerfile_name,
                tag=image_name,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Always remove intermediate containers
                pull=True,  # Pull base images
                nocache=False,
            )
            
            # Collect build logs
            for chunk in build_log:
                if 'stream' in chunk:
                    log(chunk['stream'].strip())
                elif 'error' in chunk:
                    log(f"ERROR: {chunk['error']}")
                elif 'status' in chunk:
                    log(f"STATUS: {chunk['status']}")
            
            log(f"✅ Successfully built image: {image_name}")
            log(f"Image ID: {image.id}")
            
            return True, '\n'.join(build_logs), None
            
        except BuildError as e:
            error_msg = f"Docker build failed: {str(e)}"
            log(f"❌ {error_msg}")
            for line in e.build_log:
                if 'stream' in line:
                    log(line['stream'].strip())
            return False, '\n'.join(build_logs), error_msg
            
        except APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            log(f"❌ {error_msg}")
            return False, '\n'.join(build_logs), error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            log(f"❌ {error_msg}")
            return False, '\n'.join(build_logs), error_msg
            
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    log("Cleaned up temporary files")
                except Exception as e:
                    logger.warning(f"Failed to clean up {temp_dir}: {e}")
    
    def list_local_images(self, name_filter: str | None = None) -> list[dict]:
        """
        List Docker images on the local system.
        
        Args:
            name_filter: Optional filter for image name
            
        Returns:
            List of image dictionaries
        """
        try:
            images = self.docker_client.images.list(name=name_filter)
            
            return [
                {
                    "id": img.id,
                    "tags": img.tags,
                    "created": img.attrs.get("Created"),
                    "size": img.attrs.get("Size"),
                }
                for img in images
            ]
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []
    
    def remove_image(self, image_name: str, force: bool = False) -> bool:
        """
        Remove a Docker image.
        
        Args:
            image_name: Image name or ID
            force: Force removal even if image is in use
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.docker_client.images.remove(image_name, force=force)
            logger.info(f"Removed image: {image_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove image {image_name}: {e}")
            return False
