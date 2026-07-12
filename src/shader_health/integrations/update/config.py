"""GitHub Releases configuration for Shader Health update checks."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_GITHUB_OWNER = "armasonix"
DEFAULT_GITHUB_REPO = "maya-shader-health-inspector"
DEFAULT_API_BASE_URL = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class GitHubReleasesConfig:
    """Connection defaults for GitHub Releases API lookups."""

    owner: str = DEFAULT_GITHUB_OWNER
    repo: str = DEFAULT_GITHUB_REPO
    api_base_url: str = DEFAULT_API_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    user_agent: str = "maya-shader-health-inspector"
    github_token: str = ""

    def with_overrides(self, **kwargs: Any) -> GitHubReleasesConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)

    @property
    def latest_release_url(self) -> str:
        base = self.api_base_url.rstrip("/")
        return f"{base}/repos/{self.owner}/{self.repo}/releases/latest"

    @property
    def releases_url(self) -> str:
        base = self.api_base_url.rstrip("/")
        return f"{base}/repos/{self.owner}/{self.repo}/releases?per_page=10"
