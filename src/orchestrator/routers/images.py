"""API router for Docker image management."""

import logging
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from orchestrator.config import settings
from orchestrator.database import get_db
from orchestrator.database.models import DockerImage, OrchestratorSettings
from orchestrator.services.github_service import GitHubService
from orchestrator.services.image_build_service import ImageBuildService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["images"])


# Helper functions
def _parse_env_metadata_from_labels(labels: dict[str, str]) -> list[dict]:
    """
    Parse environment variable metadata from Docker image labels.
    
    Looks for labels with pattern: io.habit.cortex.env.<VAR_NAME>.<attribute>
    
    Example label:
        io.habit.cortex.env.APPLICATION_ID.required="true"
        io.habit.cortex.env.APPLICATION_ID.description="App identifier"
    
    Returns:
        List of environment variable metadata dictionaries
    """
    env_metadata = {}
    prefix = "io.habit.cortex.env."
    
    for label_key, label_value in labels.items():
        if not label_key.startswith(prefix):
            continue
        
        # Parse: io.habit.cortex.env.<VAR_NAME>.<attribute>
        parts = label_key[len(prefix):].split(".", 1)
        if len(parts) != 2:
            continue
        
        var_name, attribute = parts
        
        if var_name not in env_metadata:
            env_metadata[var_name] = {"name": var_name}
        
        # Convert string booleans
        if label_value.lower() == "true":
            label_value = True
        elif label_value.lower() == "false":
            label_value = False
        
        env_metadata[var_name][attribute] = label_value
    
    # Return as sorted list
    return sorted(env_metadata.values(), key=lambda x: (not x.get("required", False), x["name"]))


# Pydantic schemas
class ImageBuildRequest(BaseModel):
    """Schema for triggering an image build."""
    repo: str = Field(..., description="GitHub repository (owner/repo)")
    tag: str = Field(..., description="Git tag to build")
    commit_sha: str = Field(..., description="Commit SHA for verification")
    image_name: str = Field(default="bre-payments", description="Base image name")
    dockerfile_path: str = Field(default="Dockerfile", description="Path to Dockerfile relative to repo root (e.g., 'Dockerfile' or 'cortex-orchestrator/Dockerfile')")


class ImageResponse(BaseModel):
    """Schema for image response."""
    id: int
    name: str
    tag: str
    github_repo: str
    github_ref: str
    commit_sha: str
    build_status: str
    build_log: str | None
    build_error: str | None
    built_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImageInspectResponse(BaseModel):
    """Schema for Docker image inspection."""
    image_name: str
    env_vars: list[str]  # List of ENV variables from the image (e.g., ["PATH=/usr/local/bin", "PORT=8000"])
    env_metadata: list[dict] | None  # Parsed metadata for environment variables from labels
    labels: dict[str, str] | None
    created: str | None


class GitHubTagResponse(BaseModel):
    """Schema for GitHub tag response."""
    name: str
    commit: dict
    zipball_url: str
    tarball_url: str


# Endpoints
@router.get("/github-tags")
def list_github_tags(repo: str = "habitio/bre-cortex", db: Session = Depends(get_db)):
    """
    List available tags from GitHub repository.
    
    Args:
        repo: GitHub repository (default: habitio/bre-cortex)
        db: Database session
    """
    # Get GitHub token from database settings
    orch_settings = db.query(OrchestratorSettings).filter(OrchestratorSettings.id == 1).first()
    github_token = orch_settings.github_token if orch_settings else None
    
    try:
        github_service = GitHubService(token=github_token)
        tags = github_service.list_tags(repo)
        
        # Enrich with commit details for recent tags (first 20)
        enriched_tags = []
        for tag in tags[:20]:
            try:
                commit_details = github_service.get_commit_details(repo, tag["commit"]["sha"])
                tag["commit"].update({
                    "date": commit_details["date"],
                    "author": commit_details["author"],
                    "message": commit_details["message"][:100],  # First 100 chars
                })
            except Exception as e:
                logger.warning(f"Failed to get commit details for {tag['name']}: {e}")
            
            enriched_tags.append(tag)
        
        return {"tags": enriched_tags}
        
    except Exception as e:
        logger.error(f"Failed to list GitHub tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch GitHub tags: {str(e)}",
        )


@router.post("", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
def create_image_build(build_request: ImageBuildRequest, db: Session = Depends(get_db)):
    """
    Create a new Docker image build from GitHub repository.
    
    The build runs in a background thread. Poll GET /images/{id} for status updates.
    """
    # Create database record
    full_image_name = f"{build_request.image_name}:{build_request.tag}"
    
    # Check if image already exists
    existing = db.query(DockerImage).filter(
        DockerImage.name == build_request.image_name,
        DockerImage.tag == build_request.tag
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Image {full_image_name} already exists with ID {existing.id}",
        )
    
    image = DockerImage(
        name=build_request.image_name,
        tag=build_request.tag,
        github_repo=build_request.repo,
        github_ref=f"refs/tags/{build_request.tag}",
        commit_sha=build_request.commit_sha,
        build_status="pending",
    )
    
    db.add(image)
    db.commit()
    db.refresh(image)
    
    logger.info(f"Created image build record: {full_image_name} (ID: {image.id})")
    
    # Start background build
    def build_worker():
        """Background worker to build the Docker image."""
        from orchestrator.database import SessionLocal
        worker_db = SessionLocal()
        
        try:
            # Get GitHub token from database
            orch_settings = worker_db.query(OrchestratorSettings).filter(OrchestratorSettings.id == 1).first()
            github_token = orch_settings.github_token if orch_settings else None
            
            # Update status to building
            worker_image = worker_db.query(DockerImage).filter(DockerImage.id == image.id).first()
            worker_image.build_status = "building"
            worker_db.commit()
            
            logger.info(f"Starting build for {full_image_name}")
            
            # Build the image (GitHub token from database)
            build_service = ImageBuildService(github_token=github_token)
            
            def log_callback(message: str):
                """Append to build log in real-time."""
                worker_img = worker_db.query(DockerImage).filter(DockerImage.id == image.id).first()
                if worker_img.build_log:
                    worker_img.build_log += f"\n{message}"
                else:
                    worker_img.build_log = message
                worker_db.commit()
            
            success, logs, error = build_service.build_from_github(
                repo=build_request.repo,
                tag=build_request.tag,
                commit_sha=build_request.commit_sha,
                image_name=full_image_name,
                dockerfile_path=build_request.dockerfile_path,
                log_callback=log_callback,
            )
            
            # Update final status
            worker_image = worker_db.query(DockerImage).filter(DockerImage.id == image.id).first()
            worker_image.build_status = "success" if success else "failed"
            worker_image.build_log = logs
            worker_image.build_error = error
            worker_image.built_at = datetime.utcnow() if success else None
            worker_db.commit()
            
            logger.info(f"Build completed for {full_image_name}: {worker_image.build_status}")
            
        except Exception as e:
            logger.error(f"Build worker failed for {full_image_name}: {e}")
            worker_image = worker_db.query(DockerImage).filter(DockerImage.id == image.id).first()
            worker_image.build_status = "failed"
            worker_image.build_error = str(e)
            worker_db.commit()
            
        finally:
            worker_db.close()
    
    # Start background thread
    thread = threading.Thread(target=build_worker, daemon=True)
    thread.start()
    
    return image


@router.get("", response_model=list[ImageResponse])
def list_images(
    status_filter: str | None = None,
    db: Session = Depends(get_db)
):
    """
    List all Docker images.
    
    Args:
        status_filter: Optional filter by build_status (pending, building, success, failed)
    """
    query = db.query(DockerImage).order_by(DockerImage.created_at.desc())
    
    if status_filter:
        query = query.filter(DockerImage.build_status == status_filter)
    
    images = query.all()
    return images


@router.get("/{image_id}", response_model=ImageResponse)
def get_image(image_id: int, db: Session = Depends(get_db)):
    """Get a specific Docker image by ID."""
    image = db.query(DockerImage).filter(DockerImage.id == image_id).first()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not found",
        )
    
    return image


@router.get("/{image_id}/inspect", response_model=ImageInspectResponse)
def inspect_image(image_id: int, db: Session = Depends(get_db)):
    """
    Inspect a Docker image and return its environment variables and metadata.
    
    This endpoint inspects the built Docker image to extract:
    - Environment variables defined in the Dockerfile
    - Labels
    - Creation date
    
    Use this to populate environment variable fields when creating a product instance.
    """
    import docker
    
    # Get image record from database
    image = db.query(DockerImage).filter(DockerImage.id == image_id).first()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not found",
        )
    
    # Check if image was built successfully
    if image.build_status != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image build status is '{image.build_status}', must be 'success' to inspect",
        )
    
    # Inspect the Docker image
    try:
        docker_client = docker.from_env()
        full_image_name = f"{image.name}:{image.tag}"
        
        # Get image details from Docker
        docker_image = docker_client.images.get(full_image_name)
        image_config = docker_image.attrs.get("Config", {})
        
        # Extract environment variables
        env_vars = image_config.get("Env", [])
        
        # Extract labels
        labels = image_config.get("Labels") or {}
        
        # Extract creation date
        created = docker_image.attrs.get("Created")
        
        # Parse environment variable metadata from labels
        env_metadata = _parse_env_metadata_from_labels(labels)
        
        return ImageInspectResponse(
            image_name=full_image_name,
            env_vars=env_vars,
            env_metadata=env_metadata,
            labels=labels,
            created=created,
        )
    except docker.errors.ImageNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Docker image '{full_image_name}' not found on host. The image may have been removed.",
        )
    except Exception as e:
        logger.error(f"Error inspecting image {full_image_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to inspect image: {str(e)}",
        )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: int, db: Session = Depends(get_db)):
    """
    Delete a Docker image record and optionally the Docker image itself.
    
    Note: This only deletes the database record. The actual Docker image remains.
    Use Docker CLI to remove the image: docker rmi <image>
    """
    image = db.query(DockerImage).filter(DockerImage.id == image_id).first()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not found",
        )
    
    # TODO: Check if any products are using this image
    # For now, just delete the record
    
    db.delete(image)
    db.commit()
    
    logger.info(f"Deleted image record: {image.name}:{image.tag} (ID: {image_id})")
