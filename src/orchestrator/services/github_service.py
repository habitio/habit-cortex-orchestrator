"""GitHub API integration service."""

import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str | None = None):
        """
        Initialize GitHub service.
        
        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})
    
    def list_tags(self, repo: str) -> List[Dict[str, Any]]:
        """
        List all tags for a GitHub repository.
        
        Args:
            repo: Repository in format "owner/repo"
            
        Returns:
            List of tag dictionaries with name, commit info
            
        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.BASE_URL}/repos/{repo}/tags"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            tags = response.json()
            
            # Transform to simpler format
            return [
                {
                    "name": tag["name"],
                    "commit": {
                        "sha": tag["commit"]["sha"],
                        "url": tag["commit"]["url"],
                    },
                    "zipball_url": tag["zipball_url"],
                    "tarball_url": tag["tarball_url"],
                }
                for tag in tags
            ]
            
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch tags for {repo}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching tags: {e}")
            raise
    
    def get_commit_details(self, repo: str, sha: str) -> Dict[str, Any]:
        """
        Get detailed commit information.
        
        Args:
            repo: Repository in format "owner/repo"
            sha: Commit SHA
            
        Returns:
            Commit details including date, author, message
        """
        url = f"{self.BASE_URL}/repos/{repo}/commits/{sha}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            commit_data = response.json()
            
            return {
                "sha": commit_data["sha"],
                "message": commit_data["commit"]["message"],
                "author": commit_data["commit"]["author"]["name"],
                "date": commit_data["commit"]["author"]["date"],
                "html_url": commit_data["html_url"],
            }
            
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch commit {sha} for {repo}: {e}")
            raise
    
    def download_tarball(self, repo: str, ref: str, output_path: str) -> None:
        """
        Download repository tarball for a specific ref (tag/branch/commit).
        
        Args:
            repo: Repository in format "owner/repo"
            ref: Git reference (tag, branch, or commit SHA)
            output_path: Where to save the tarball
        """
        url = f"{self.BASE_URL}/repos/{repo}/tarball/{ref}"
        
        try:
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded {repo}@{ref} to {output_path}")
            
        except requests.HTTPError as e:
            logger.error(f"Failed to download {repo}@{ref}: {e}")
            raise
