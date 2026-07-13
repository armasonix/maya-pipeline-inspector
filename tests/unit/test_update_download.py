from __future__ import annotations

import pytest

from pipeline_inspector.integrations.update.download import (
    make_authenticated_download_transport,
    resolve_release_asset_download,
)
from pipeline_inspector.integrations.update.github_releases import ReleaseAsset


def _sample_asset() -> ReleaseAsset:
    return ReleaseAsset(
        name="maya-pipeline-inspector-0.5.0.zip",
        download_url=(
            "https://github.com/armasonix/maya-pipeline-inspector/"
            "releases/download/v0.5.0/maya-pipeline-inspector-0.5.0.zip"
        ),
        size=123,
        content_type="application/zip",
        asset_id=475385077,
    )


def test_resolve_release_asset_download_uses_api_endpoint_with_token():
    asset = _sample_asset()

    url, headers = resolve_release_asset_download(
        asset,
        owner="armasonix",
        repo="maya-pipeline-inspector",
        github_token="studio-token",
    )

    assert url.endswith("/releases/assets/475385077")
    assert headers["Accept"] == "application/octet-stream"
    assert headers["Authorization"] == "Bearer studio-token"


def test_resolve_release_asset_download_uses_browser_url_without_token():
    asset = _sample_asset()

    url, headers = resolve_release_asset_download(
        asset,
        owner="armasonix",
        repo="maya-pipeline-inspector",
        github_token="",
    )

    assert url == asset.download_url
    assert "Authorization" not in headers
    assert "Accept" not in headers


def test_make_authenticated_download_transport_uses_resolved_api_url(monkeypatch):
    asset = _sample_asset()
    captured: dict[str, object] = {}

    def _fake_download(
        url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> bytes:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return b"zip-bytes"

    monkeypatch.setattr(
        "pipeline_inspector.integrations.update.download._download_bytes_with_headers",
        _fake_download,
    )
    transport = make_authenticated_download_transport(
        asset,
        owner="armasonix",
        repo="maya-pipeline-inspector",
        github_token="studio-token",
    )
    payload = transport(asset.download_url, 30.0)

    assert payload == b"zip-bytes"
    assert "/releases/assets/475385077" in str(captured["url"])
    assert captured["headers"]["Authorization"] == "Bearer studio-token"
