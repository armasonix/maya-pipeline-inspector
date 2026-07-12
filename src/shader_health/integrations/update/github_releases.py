"""GitHub Releases client for Shader Health update checks."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from shader_health.integrations.update.config import GitHubReleasesConfig

HttpTransport = Callable[["HttpRequest", float], "GitHubReleasesResponse"]

_SEMVER_CORE_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


@dataclass(frozen=True)
class HttpRequest:
    """Low-level HTTP request passed to a transport implementation."""

    method: str
    url: str
    body: bytes | None
    headers: Mapping[str, str]


@dataclass(frozen=True)
class GitHubReleasesResponse:
    """Normalized GitHub REST API response."""

    status_code: int
    body: str
    json_data: dict[str, Any] | list[Any] | None = None


@dataclass(frozen=True)
class SemverVersion:
    """Parsed semver core used for update comparisons."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseAsset:
    """One downloadable asset attached to a GitHub release."""

    name: str
    download_url: str
    size: int
    content_type: str
    asset_id: int


@dataclass(frozen=True)
class GitHubRelease:
    """Latest release metadata returned by GitHub."""

    tag_name: str
    name: str
    html_url: str
    published_at: str
    body: str
    assets: tuple[ReleaseAsset, ...]

    @property
    def version(self) -> str:
        return normalize_release_tag(self.tag_name)


@dataclass(frozen=True)
class UpdateCheckResult:
    """Outcome from comparing an installed version with GitHub Releases."""

    installed_version: str
    latest_version: str
    tag_name: str
    update_available: bool
    release: GitHubRelease | None = None
    error_message: str = ""
    status_code: int = 0


class GitHubReleasesClientError(RuntimeError):
    """Raised when the GitHub Releases API returns an unexpected response."""


class GitHubReleasesClient:
    """REST wrapper for GitHub Releases latest lookup and semver compare."""

    def __init__(
        self,
        config: GitHubReleasesConfig | None = None,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config or GitHubReleasesConfig()
        self._transport = transport or default_http_transport

    @property
    def config(self) -> GitHubReleasesConfig:
        return self._config

    def request(self, method: str, url: str) -> GitHubReleasesResponse:
        """Send a raw HTTP request to the GitHub REST API."""

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self._config.user_agent,
        }
        token = str(self._config.github_token or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = HttpRequest(method=method.upper(), url=url, body=None, headers=headers)
        return self._transport(request, self._config.timeout_seconds)

    def _private_repo_error_message(self) -> str:
        return (
            "GitHub repository is private or not accessible without a token. "
            "Add updates.github_token to shader_health_studio.json "
            f"(repo: {self._config.owner}/{self._config.repo})."
        )

    def _fetch_latest_release_from_list(self) -> GitHubRelease | None:
        response = self.request("GET", self._config.releases_url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            return None
        if not isinstance(response.json_data, list):
            return None
        for item in response.json_data:
            if not isinstance(item, Mapping):
                continue
            if bool(item.get("draft")):
                continue
            return parse_release_payload(item)
        return None

    def fetch_latest_release(self) -> GitHubRelease:
        """Fetch metadata and assets for the latest GitHub release."""

        response = self.request("GET", self._config.latest_release_url)
        if response.status_code == 404:
            fallback = self._fetch_latest_release_from_list()
            if fallback is not None:
                return fallback
            raise GitHubReleasesClientError(self._private_repo_error_message())
        if response.status_code != 200:
            raise GitHubReleasesClientError(
                f"GitHub Releases API returned HTTP {response.status_code} for latest release."
            )
        if not isinstance(response.json_data, dict):
            raise GitHubReleasesClientError("GitHub Releases API returned non-object JSON.")
        return parse_release_payload(response.json_data)

    def check_for_update(self, installed_version: str) -> UpdateCheckResult:
        """Compare the installed version against the latest GitHub release tag."""

        response = self.request("GET", self._config.latest_release_url)
        release_payload: Mapping[str, Any] | None = None
        if response.status_code == 200 and isinstance(response.json_data, dict):
            release_payload = response.json_data
        elif response.status_code == 404:
            fallback_release = self._fetch_latest_release_from_list()
            if fallback_release is None:
                return UpdateCheckResult(
                    installed_version=installed_version,
                    latest_version="",
                    tag_name="",
                    update_available=False,
                    error_message=self._private_repo_error_message(),
                    status_code=response.status_code,
                )
            release = fallback_release
            update_available = is_newer_version(release.version, installed_version)
            return UpdateCheckResult(
                installed_version=installed_version,
                latest_version=release.version,
                tag_name=release.tag_name,
                update_available=update_available,
                release=release,
                status_code=response.status_code,
            )
        elif response.status_code != 200:
            return UpdateCheckResult(
                installed_version=installed_version,
                latest_version="",
                tag_name="",
                update_available=False,
                error_message=(
                    f"GitHub Releases API returned HTTP {response.status_code} "
                    "for latest release."
                ),
                status_code=response.status_code,
            )
        else:
            return UpdateCheckResult(
                installed_version=installed_version,
                latest_version="",
                tag_name="",
                update_available=False,
                error_message="GitHub Releases API returned non-object JSON.",
                status_code=response.status_code,
            )

        release = parse_release_payload(release_payload)
        update_available = is_newer_version(release.version, installed_version)
        return UpdateCheckResult(
            installed_version=installed_version,
            latest_version=release.version,
            tag_name=release.tag_name,
            update_available=update_available,
            release=release,
            status_code=response.status_code,
        )


def normalize_release_tag(tag_name: str) -> str:
    """Strip a leading ``v`` from GitHub release tags for semver compare."""

    text = tag_name.strip()
    if text.lower().startswith("v") and len(text) > 1 and text[1].isdigit():
        return text[1:]
    return text


def parse_semver(version: str) -> SemverVersion:
    """Parse a semver string used by release tags and ``version.py``."""

    normalized = normalize_release_tag(version)
    match = _SEMVER_CORE_RE.match(normalized)
    if match is None:
        raise ValueError(f"Unsupported semver string: {version!r}")

    prerelease_raw = match.group("prerelease")
    prerelease = tuple(prerelease_raw.split(".")) if prerelease_raw else ()
    return SemverVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=prerelease,
    )


def compare_semver(left: str, right: str) -> int:
    """Return ``-1``, ``0``, or ``1`` when ``left`` is older, equal, or newer than ``right``."""

    left_version = parse_semver(left)
    right_version = parse_semver(right)
    for left_value, right_value in (
        (left_version.major, right_version.major),
        (left_version.minor, right_version.minor),
        (left_version.patch, right_version.patch),
    ):
        if left_value < right_value:
            return -1
        if left_value > right_value:
            return 1

    if not left_version.prerelease and not right_version.prerelease:
        return 0
    if not left_version.prerelease and right_version.prerelease:
        return 1
    if left_version.prerelease and not right_version.prerelease:
        return -1
    return _compare_prerelease_identifiers(left_version.prerelease, right_version.prerelease)


def is_newer_version(candidate: str, installed: str) -> bool:
    """Return ``True`` when ``candidate`` is semver-newer than ``installed``."""

    return compare_semver(candidate, installed) > 0


def parse_release_payload(payload: Mapping[str, Any]) -> GitHubRelease:
    """Convert a GitHub ``/releases/latest`` JSON object into ``GitHubRelease``."""

    assets_raw = payload.get("assets")
    assets: tuple[ReleaseAsset, ...] = ()
    if isinstance(assets_raw, Sequence) and not isinstance(assets_raw, (str, bytes)):
        parsed_assets: list[ReleaseAsset] = []
        for item in assets_raw:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("name", "") or "")
            download_url = str(item.get("browser_download_url", "") or "")
            if not name or not download_url:
                continue
            parsed_assets.append(
                ReleaseAsset(
                    name=name,
                    download_url=download_url,
                    size=int(item.get("size", 0) or 0),
                    content_type=str(item.get("content_type", "") or ""),
                    asset_id=int(item.get("id", 0) or 0),
                )
            )
        assets = tuple(parsed_assets)

    return GitHubRelease(
        tag_name=str(payload.get("tag_name", "") or ""),
        name=str(payload.get("name", "") or ""),
        html_url=str(payload.get("html_url", "") or ""),
        published_at=str(payload.get("published_at", "") or ""),
        body=str(payload.get("body", "") or ""),
        assets=assets,
    )


def default_http_transport(request: HttpRequest, timeout: float) -> GitHubReleasesResponse:
    """Send an HTTP request using the Python standard library."""

    urllib_request = urllib.request.Request(
        request.url,
        data=request.body,
        headers=dict(request.headers),
        method=request.method,
    )
    try:
        with urllib.request.urlopen(urllib_request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return GitHubReleasesResponse(
                status_code=response.status,
                body=body,
                json_data=_parse_json_body(body),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return GitHubReleasesResponse(
            status_code=exc.code,
            body=body,
            json_data=_parse_json_body(body),
        )


def _compare_prerelease_identifiers(
    left: tuple[str, ...],
    right: tuple[str, ...],
) -> int:
    for left_part, right_part in zip(left, right):
        left_is_numeric = left_part.isdigit()
        right_is_numeric = right_part.isdigit()
        if left_is_numeric and right_is_numeric:
            left_number = int(left_part)
            right_number = int(right_part)
            if left_number < right_number:
                return -1
            if left_number > right_number:
                return 1
            continue
        if left_is_numeric != right_is_numeric:
            return -1 if left_is_numeric else 1
        if left_part < right_part:
            return -1
        if left_part > right_part:
            return 1
    if len(left) < len(right):
        return -1
    if len(left) > len(right):
        return 1
    return 0


def _parse_json_body(body: str) -> dict[str, Any] | list[Any] | None:
    text = body.strip()
    if not text or text[0] not in "{[":
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return None
