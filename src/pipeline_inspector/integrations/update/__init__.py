"""GitHub Releases integration for Pipeline Inspector update checks."""

from pipeline_inspector.integrations.update.config import (
    DEFAULT_API_BASE_URL,
    DEFAULT_GITHUB_OWNER,
    DEFAULT_GITHUB_REPO,
    DEFAULT_TIMEOUT_SECONDS,
    GitHubReleasesConfig,
)
from pipeline_inspector.integrations.update.github_releases import (
    GitHubRelease,
    GitHubReleasesClient,
    GitHubReleasesClientError,
    GitHubReleasesResponse,
    HttpRequest,
    HttpTransport,
    ReleaseAsset,
    UpdateCheckResult,
    compare_semver,
    default_http_transport,
    is_newer_version,
    normalize_release_tag,
    parse_release_payload,
    parse_semver,
)
from pipeline_inspector.integrations.update.install import (
    UpdateInstallResult,
    install_staged_update,
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
    "UpdateCheckResult",
    "UpdateInstallResult",
    "compare_semver",
    "default_http_transport",
    "install_staged_update",
    "is_newer_version",
    "normalize_release_tag",
    "parse_release_payload",
    "parse_semver",
]
