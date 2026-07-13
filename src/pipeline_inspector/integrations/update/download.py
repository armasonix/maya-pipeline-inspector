"""Download helpers for GitHub Releases update assets."""
from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from pipeline_inspector.integrations.update.github_releases import ReleaseAsset

DownloadTransport = Callable[[str, float], bytes]

DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 120.0
UPDATE_STAGING_DIRNAME = "updates"
UPDATE_STAGING_SUBDIR = "staging"


def default_download_transport(url: str, timeout: float) -> bytes:
    """Download release asset bytes using the Python standard library."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "maya-pipeline-inspector"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub asset download returned HTTP {exc.code}: {body or exc.reason}"
        ) from exc


def select_update_asset(assets: tuple[ReleaseAsset, ...]) -> ReleaseAsset | None:
    """Pick the preferred install package from a GitHub release asset list."""

    if not assets:
        return None

    zip_assets = [asset for asset in assets if asset.name.lower().endswith(".zip")]
    if not zip_assets:
        return None

    def preference_key(asset: ReleaseAsset) -> tuple[int, str]:
        lowered = asset.name.lower()
        if _is_legacy_shader_health_asset(lowered):
            return (-1, lowered)
        if lowered.startswith("maya-pipeline-inspector") and lowered.endswith(".zip"):
            return (3, lowered)
        if "maya-pipeline-inspector" in lowered:
            return (2, lowered)
        if "pipeline-inspector" in lowered or "pipeline_inspector" in lowered:
            return (1, lowered)
        return (0, lowered)

    candidates = [asset for asset in zip_assets if preference_key(asset)[0] >= 0]
    if not candidates:
        return None

    return max(candidates, key=preference_key)


def _is_legacy_shader_health_asset(name: str) -> bool:
    legacy_markers = (
        "shader-health",
        "shader_health",
        "maya-shader-health",
    )
    return any(marker in name for marker in legacy_markers)


def default_update_staging_root() -> Path:
    """Return the default local staging directory for downloaded update packages."""

    from pipeline_inspector.user_config import USER_CONFIG_DIRNAME

    return Path.home() / USER_CONFIG_DIRNAME / UPDATE_STAGING_DIRNAME / UPDATE_STAGING_SUBDIR


def download_release_asset(
    asset: ReleaseAsset,
    *,
    tag_name: str,
    staging_root: Path | None = None,
    transport: DownloadTransport | None = None,
    timeout_seconds: float = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
) -> Path:
    """Download one release asset into a versioned staging directory."""

    root = staging_root or default_update_staging_root()
    destination_dir = root / _sanitize_tag_name(tag_name)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / asset.name
    downloader = transport or default_download_transport
    payload = downloader(asset.download_url, timeout_seconds)
    destination.write_bytes(payload)
    return destination


def _sanitize_tag_name(tag_name: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {".", "-", "_"} else "_"
        for char in tag_name.strip()
    )
    return cleaned or "release"
