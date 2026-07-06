from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.unit.test_manifest_diff_command import new_manifest, old_manifest

from shader_health.reports.html_manifest_diff import (
    build_html_manifest_diff,
    write_html_manifest_diff,
)
from shader_health.reports.manifest_diff import build_manifest_diff

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "reports" / "manifest_diff_sample.json"
)


@pytest.fixture(name="sample_diff")
def fixture_sample_diff() -> dict[str, object]:
    return build_manifest_diff(old_manifest(), new_manifest())


def test_html_manifest_diff_is_self_contained(sample_diff: dict[str, object]):
    html = build_html_manifest_diff(sample_diff)

    assert html.startswith("<!doctype html>")
    assert "<style>" in html
    assert "table-wrap" in html
    assert "score-ring" in html
    assert "href=" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html.casefold()


def test_html_manifest_diff_renders_summary_and_issue_groups(sample_diff: dict[str, object]):
    html = build_html_manifest_diff(sample_diff)

    assert "Maya Shader Health Manifest Diff" in html
    assert "Before/after comparison of shader manifest materials and textures." in html
    assert "Summary" in html
    assert "Issue Groups" in html
    assert "Expand or collapse each group" in html
    assert "New (1)" in html
    assert "Resolved (1)" in html
    assert "Changed (2)" in html
    assert '<details class="severity category-new" open>' in html
    assert '<details class="severity category-resolved" open>' in html
    assert '<details class="severity category-changed" open>' in html


def test_html_manifest_diff_lists_new_resolved_and_changed_entries(sample_diff: dict[str, object]):
    html = build_html_manifest_diff(sample_diff)

    assert "file_roughness" in html
    assert "file_mask" in html
    assert "hero_mtl" in html
    assert "graph_fingerprint" in html
    assert "sha256:old_graph" in html
    assert "sha256:new_graph" in html
    assert "old_scene.ma" in html
    assert "new_scene.ma" in html
    assert "kind-texture" in html
    assert "kind-material" in html


def test_html_manifest_diff_escapes_user_controlled_text():
    diff = build_manifest_diff(
        {
            "manifest_schema_version": "1.0",
            "scene_path": "old <unsafe>.ma",
            "materials": [],
        },
        {
            "manifest_schema_version": "1.0",
            "scene_path": 'new & "unsafe".ma',
            "materials": [
                {
                    "node_id": "node:hero_mtl",
                    "name": 'hero <mtl> & "unsafe"',
                    "type_name": "VRayMtl",
                    "textures": [],
                }
            ],
        },
    )

    html = build_html_manifest_diff(diff)

    assert "old &lt;unsafe&gt;.ma" in html
    assert 'new &amp; "unsafe".ma' in html
    assert "hero &lt;mtl&gt; &amp;" in html
    assert "<unsafe>" not in html


def test_html_manifest_diff_fixture_matches_locked_sections(sample_diff: dict[str, object]):
    html = build_html_manifest_diff(sample_diff)
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for section in fixture["required_sections"]:
        assert section in html


def test_write_html_manifest_diff_writes_file(sample_diff: dict[str, object], tmp_path: Path):
    output_path = tmp_path / "reports" / "manifest_diff.html"
    written = write_html_manifest_diff(output_path, sample_diff)

    assert written == output_path
    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8") == build_html_manifest_diff(sample_diff)
