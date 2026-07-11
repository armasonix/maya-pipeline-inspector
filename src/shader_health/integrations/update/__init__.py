"""GitHub Releases integration for Shader Health update checks."""

from shader_health.integrations.update.config import (
    DEFAULT_API_BASE_URL,
    DEFAULT_GITHUB_OWNER,
    DEFAULT_GITHUB_REPO,
    DEFAULT_TIMEOUT_SECONDS,
    GitHubReleasesConfig,
)
from shader_health.integrations.update.github_releases import (
    GitHubRelease,
    GitHubReleasesClient,
    GitHubReleasesClientError,
    GitHubReleasesResponse,
    HttpRequest,
    HttpTransport,
    ReleaseAsset,
    SemverVersion,
    UpdateCheckResult,
    compare_semver,
    default_http_transport,
    is_newer_version,
    normalize_release_tag,
    parse_release_payload,
    parse_semver,
)

__all__ = [
    "DEFAULT_API_BASE_URL",
    "DEFAULT_GITHUB_OWNER",
    "DEFAULT_GITHUB_REPO",
    "DEFAULT_TIMEOUT_SECONDS",
    "GitHubRelease",
    "GitHubReleasesClient",
    "GitHubReleasesClientError",
    "GitHubReleasesConfig",
    "GitHubReleasesResponse",
    "HttpRequest",
    "HttpTransport",
    "ReleaseAsset",
    "SemverVersion",
    "UpdateCheckResult",
    "compare_semver",
    "default_http_transport",
    "is_newer_version",
    "normalize_release_tag",
    "parse_release_payload",
    "parse_semver",
]
