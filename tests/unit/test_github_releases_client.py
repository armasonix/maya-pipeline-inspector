from __future__ import annotations

import json

import pytest

from shader_health.integrations.update import (
    GitHubReleasesClient,
    GitHubReleasesConfig,
    compare_semver,
    is_newer_version,
    normalize_release_tag,
    parse_release_payload,
    parse_semver,
)
from shader_health.integrations.update.github_releases import (
    GitHubReleasesResponse,
    HttpRequest,
)


def _latest_release_payload() -> dict[str, object]:
    return {
        "tag_name": "v0.5.0",
        "name": "v0.5.0 — Settings Core v2",
        "html_url": "https://github.com/armasonix/maya-shader-health-inspector/releases/tag/v0.5.0",
        "published_at": "2026-07-11T07:00:00Z",
        "body": "Release notes",
        "assets": [
            {
                "id": 42,
                "name": "maya-shader-health-inspector-v0.5.0.zip",
                "browser_download_url": (
                    "https://github.com/armasonix/maya-shader-health-inspector/"
                    "releases/download/v0.5.0/maya-shader-health-inspector-v0.5.0.zip"
                ),
                "size": 123456,
                "content_type": "application/zip",
            },
            {
                "id": 43,
                "name": "shader_health_inspector.mll",
                "browser_download_url": (
                    "https://github.com/armasonix/maya-shader-health-inspector/"
                    "releases/download/v0.5.0/shader_health_inspector.mll"
                ),
                "size": 11776,
                "content_type": "application/octet-stream",
            },
        ],
    }


def test_normalize_release_tag_strips_leading_v():
    assert normalize_release_tag("v0.4.0") == "0.4.0"
    assert normalize_release_tag("0.4.0") == "0.4.0"


def test_compare_semver_orders_core_and_prerelease_versions():
    assert compare_semver("0.4.0", "0.5.0") == -1
    assert compare_semver("0.5.0", "0.4.0") == 1
    assert compare_semver("v0.4.0", "0.4.0") == 0
    assert compare_semver("1.0.0-alpha", "1.0.0") == -1
    assert compare_semver("1.0.0-alpha.1", "1.0.0-alpha.2") == -1


def test_parse_semver_reads_prerelease_identifiers():
    parsed = parse_semver("2.1.0-rc.3")

    assert parsed.major == 2
    assert parsed.minor == 1
    assert parsed.patch == 0
    assert parsed.prerelease == ("rc", "3")


def test_parse_semver_rejects_invalid_strings():
    with pytest.raises(ValueError, match="Unsupported semver"):
        parse_semver("not-a-version")


def test_is_newer_version_compares_installed_version():
    assert is_newer_version("0.5.0", "0.4.0") is True
    assert is_newer_version("0.4.0", "0.4.0") is False
    assert is_newer_version("0.3.0", "0.4.0") is False


def test_parse_release_payload_extracts_assets():
    release = parse_release_payload(_latest_release_payload())

    assert release.tag_name == "v0.5.0"
    assert release.version == "0.5.0"
    assert release.html_url.endswith("/releases/tag/v0.5.0")
    assert len(release.assets) == 2
    assert release.assets[0].name == "maya-shader-health-inspector-v0.5.0.zip"
    assert release.assets[0].asset_id == 42
    assert release.assets[1].download_url.endswith("shader_health_inspector.mll")


def test_github_releases_client_fetches_latest_release_metadata_and_assets():
    captured: list[HttpRequest] = []

    def transport(request: HttpRequest, timeout: float) -> GitHubReleasesResponse:
        captured.append(request)
        _ = timeout
        return GitHubReleasesResponse(
            status_code=200,
            body=json.dumps(_latest_release_payload()),
            json_data=_latest_release_payload(),
        )

    client = GitHubReleasesClient(transport=transport)
    release = client.fetch_latest_release()

    assert len(captured) == 1
    assert captured[0].method == "GET"
    assert captured[0].url.endswith("/repos/armasonix/maya-shader-health-inspector/releases/latest")
    assert captured[0].headers["Accept"] == "application/vnd.github+json"
    assert release.version == "0.5.0"
    assert release.assets[0].content_type == "application/zip"


def test_github_releases_client_check_for_update_reports_available_release():
    def transport(_request: HttpRequest, _timeout: float) -> GitHubReleasesResponse:
        return GitHubReleasesResponse(
            status_code=200,
            body=json.dumps(_latest_release_payload()),
            json_data=_latest_release_payload(),
        )

    client = GitHubReleasesClient(transport=transport)

    result = client.check_for_update("0.4.0")

    assert result.update_available is True
    assert result.latest_version == "0.5.0"
    assert result.tag_name == "v0.5.0"
    assert result.status_code == 200
    assert result.release is not None
    assert len(result.release.assets) == 2


def test_github_releases_client_check_for_update_reports_up_to_date_install():
    def transport(_request: HttpRequest, _timeout: float) -> GitHubReleasesResponse:
        return GitHubReleasesResponse(
            status_code=200,
            body=json.dumps(_latest_release_payload()),
            json_data=_latest_release_payload(),
        )

    client = GitHubReleasesClient(transport=transport)

    result = client.check_for_update("0.5.0")

    assert result.update_available is False
    assert result.error_message == ""


def test_github_releases_client_check_for_update_surfaces_http_errors():
    def transport(_request: HttpRequest, _timeout: float) -> GitHubReleasesResponse:
        return GitHubReleasesResponse(
            status_code=404,
            body='{"message":"Not Found"}',
            json_data=None,
        )

    client = GitHubReleasesClient(
        GitHubReleasesConfig(owner="armasonix", repo="missing-repo"),
        transport=transport,
    )

    result = client.check_for_update("0.4.0")

    assert result.update_available is False
    assert result.status_code == 404
    assert "HTTP 404" in result.error_message
