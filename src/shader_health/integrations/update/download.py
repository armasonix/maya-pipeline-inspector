"""Download helpers for GitHub Releases update assets."""
from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from shader_health.integrations.update.github_releases import ReleaseAsset

DownloadTransport = Callable[[str, float], bytes]

DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 120.0
UPDATE_STAGING_DIRNAME = "updates"
UPDATE_STAGING_SUBDIR = "staging"


def default_download_transport(url: str, timeout: float) -> bytes:
    """Download release asset bytes using the Python standard library."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "maya-shader-health-inspector"},
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
    for asset in zip_assets:
        lowered = asset.name.lower()
        if "maya-shader-health-inspector" in lowered:
            return asset
    if zip_assets:
        return zip_assets[0]
    return assets[0]


def default_update_staging_root() -> Path:
    """Return the default local staging directory for downloaded update packages."""

    from shader_health.user_config import USER_CONFIG_DIRNAME

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
