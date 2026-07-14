from __future__ import annotations

import pytest

from pipeline_inspector.core.naming_fix import propose_naming_fix, propose_texture_file_path_fix

MESH_PATTERN = r"^geo_[A-Za-z0-9_]+$"
MATERIAL_PATTERN = r"^mat_[A-Za-z0-9_]+$"


def test_propose_texture_file_path_fix_renames_basename():
    assert (
        propose_texture_file_path_fix(r"D:/show/tex/albedo_wrong.exr", r"^tex_[A-Za-z0-9_]+$")
        == "D:/show/tex/tex_albedo_wrong.exr"
    )
    assert (
        propose_texture_file_path_fix(
            r"D:/show/tex/albedo_wrong.<UDIM>.exr",
            r"^tex_[A-Za-z0-9_]+$",
        )
        == "D:/show/tex/tex_albedo_wrong.<UDIM>.exr"
    )


@pytest.mark.parametrize(
    ("current", "pattern", "expected"),
    [
        ("body_bad", MESH_PATTERN, "geo_body_bad"),
        ("shader_body", MATERIAL_PATTERN, "mat_shader_body"),
        ("geo_body_01", MESH_PATTERN, None),
        ("geo_body-bad", MESH_PATTERN, "geo_body_bad"),
        ("|world|grp_rig|body_bad", MESH_PATTERN, "geo_body_bad"),
        ("", MESH_PATTERN, None),
        ("body_bad", "", None),
        ("body_bad", "[invalid", None),
    ],
)
def test_propose_naming_fix_returns_expected_short_name(
    current: str,
    pattern: str,
    expected: str | None,
) -> None:
    assert propose_naming_fix(current, pattern) == expected
