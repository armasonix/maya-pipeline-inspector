from __future__ import annotations

from typing import Any, Optional

from shader_health.core.fix_plan import FixAction
from shader_health.maya.fix_applier import apply_fix_actions


class FakeCmds:
    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        self.attrs = attrs or {}
        self.undo_calls: list[dict[str, Any]] = []
        self.set_calls: list[tuple[str, Any, dict[str, Any]]] = []

    def undoInfo(self, **kwargs: Any) -> None:
        self.undo_calls.append(dict(kwargs))

    def objExists(self, node_name: str) -> bool:
        prefix = f"{node_name}."
        return any(plug.startswith(prefix) for plug in self.attrs)

    def getAttr(self, plug: str) -> Any:
        return self.attrs[plug]

    def setAttr(self, plug: str, value: Any, **kwargs: Any) -> None:
        self.set_calls.append((plug, value, dict(kwargs)))
        self.attrs[plug] = value


def test_apply_fix_actions_uses_undo_chunk_and_records_before_after_values():
    cmds = FakeCmds({"file1.colorSpace": "ACEScg"})
    action = _action()

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.undo_calls == [
        {"openChunk": True, "chunkName": "Shader Health Apply Fixes"},
        {"closeChunk": True},
    ]
    assert cmds.set_calls == [("file1.colorSpace", "Raw", {"type": "string"})]
    assert report.total == 1
    assert report.applied_count == 1
    assert report.blocked_count == 0
    record = report.records[0]
    assert record.before_value == "ACEScg"
    assert record.after_value == "Raw"
    assert record.applied is True
    assert record.blocked is False
    assert record.message == "Fix applied."


def test_apply_fix_actions_blocks_referenced_and_locked_targets_by_default():
    cmds = FakeCmds({"file1.colorSpace": "ACEScg"})
    action = _action(referenced=True, locked=True)

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == []
    assert report.applied_count == 0
    assert report.blocked_count == 1
    record = report.records[0]
    assert record.blocked is True
    assert record.block_reasons == ["target_referenced", "target_locked"]
    assert record.before_value == "ACEScg"
    assert record.after_value == "Raw"


def test_apply_fix_actions_allows_referenced_locked_targets_when_explicitly_enabled():
    cmds = FakeCmds({"file1.colorSpace": "ACEScg"})
    action = _action(referenced=True, locked=True)

    report = apply_fix_actions(
        [action],
        cmds=cmds,
        allow_referenced=True,
        allow_locked=True,
    )

    assert report.applied_count == 1
    assert report.blocked_count == 0
    assert cmds.attrs["file1.colorSpace"] == "Raw"


def test_apply_fix_actions_blocks_unsupported_fix_types():
    cmds = FakeCmds({"file1.colorSpace": "ACEScg"})
    action = _action(fix_type="cleanup_orphan")

    report = apply_fix_actions([action], cmds=cmds)

    assert report.applied_count == 0
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["unsupported_fix_type"]
    assert cmds.set_calls == []


def test_apply_fix_actions_returns_empty_report_without_undo_chunk_for_empty_input():
    cmds = FakeCmds()

    report = apply_fix_actions([], cmds=cmds)

    assert report.to_dict() == {
        "total": 0,
        "applied_count": 0,
        "blocked_count": 0,
        "failed_count": 0,
        "records": [],
    }
    assert cmds.undo_calls == []


def test_apply_relink_path_updates_file_texture_path_inside_undo_chunk():
    cmds = FakeCmds(
        {
            "file1.fileTextureName": "D:/show/tex/albedo_v001.<UDIM>.exr",
        }
    )
    action = _relink_action(
        before_value="D:/show/tex/albedo_v001.<UDIM>.exr",
        after_value="D:/show/tex/albedo_v003.<UDIM>.exr",
    )

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.undo_calls == [
        {"openChunk": True, "chunkName": "Shader Health Apply Fixes"},
        {"closeChunk": True},
    ]
    assert cmds.set_calls == [
        (
            "file1.fileTextureName",
            "D:/show/tex/albedo_v003.<UDIM>.exr",
            {"type": "string"},
        )
    ]
    assert report.applied_count == 1
    record = report.records[0]
    assert record.fix_type == "relink_path"
    assert record.target_attr == "fileTextureName"
    assert record.before_value == "D:/show/tex/albedo_v001.<UDIM>.exr"
    assert record.after_value == "D:/show/tex/albedo_v003.<UDIM>.exr"


def test_apply_relink_path_blocks_referenced_targets_by_default():
    cmds = FakeCmds({"file1.fileTextureName": "D:/old/path.exr"})
    action = _relink_action(referenced=True)

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == []
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["target_referenced"]


def test_apply_relink_path_blocks_missing_target_node():
    cmds = FakeCmds()
    action = _relink_action()

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == []
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["target_node_missing"]


def test_apply_relink_path_uses_attribute_from_fix_params_when_plug_is_metadata():
    cmds = FakeCmds({"file1.fileTextureName": "D:/show/tex/albedo_v001.exr"})
    action = _relink_action(target_attr="version")

    report = apply_fix_actions([action], cmds=cmds)

    assert report.applied_count == 1
    assert cmds.set_calls[0][0] == "file1.fileTextureName"


def test_apply_relink_path_blocks_invalid_empty_path():
    cmds = FakeCmds({"file1.fileTextureName": "D:/show/tex/albedo_v001.exr"})
    action = _relink_action(after_value="   ")

    report = apply_fix_actions([action], cmds=cmds)

    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["invalid_relink_path"]


def test_apply_normalize_path_rewrites_local_prefix_to_project_variable():
    cmds = FakeCmds({"file1.fileTextureName": "D:/show/assets/tex/albedo.exr"})
    action = _normalize_action()

    report = apply_fix_actions([action], cmds=cmds)

    assert report.applied_count == 1
    assert cmds.set_calls == [
        ("file1.fileTextureName", "$ASSET_ROOT/tex/albedo.exr", {"type": "string"}),
    ]
    record = report.records[0]
    assert record.fix_type == "normalize_path"
    assert record.before_value == "D:/show/assets/tex/albedo.exr"
    assert record.after_value == "$ASSET_ROOT/tex/albedo.exr"


def test_apply_normalize_path_blocks_referenced_targets_by_default():
    cmds = FakeCmds({"file1.fileTextureName": "D:/show/assets/tex/albedo.exr"})
    action = _normalize_action(referenced=True)

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == []
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["target_referenced"]


def test_apply_normalize_path_blocks_when_prefix_does_not_match():
    cmds = FakeCmds({"file1.fileTextureName": "//legacy_server/random/albedo.exr"})
    action = _normalize_action()

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == []
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["invalid_normalize_path"]


def _action(
    *,
    fix_type: str = "set_attr",
    referenced: bool = False,
    locked: bool = False,
) -> FixAction:
    block_reasons: list[str] = []
    if referenced:
        block_reasons.append("target_referenced")
    if locked:
        block_reasons.append("target_locked")
    return FixAction(
        fix_id="common.texture.colorspace.data_raw:node:file1:set_attr",
        rule_id="common.texture.colorspace.data_raw",
        title="Data textures must use Raw color space: set_attr",
        fix_type=fix_type,
        risk="low",
        target_kind="node",
        target_id="node:file1",
        target_node="file1",
        target_attr="colorSpace",
        before_value="ACEScg",
        after_value="Raw",
        explanation="Data textures must not be color transformed.",
        referenced=referenced,
        locked=locked,
        requires_reference_edit=referenced,
        blocked=bool(block_reasons),
        block_reasons=block_reasons,
        params={"type": fix_type, "attribute": "colorSpace", "value": "Raw"},
    )


def _relink_action(
    *,
    referenced: bool = False,
    locked: bool = False,
    target_attr: str = "fileTextureName",
    before_value: str = "D:/show/tex/albedo_v001.<UDIM>.exr",
    after_value: str = "D:/show/tex/albedo_v003.<UDIM>.exr",
) -> FixAction:
    block_reasons: list[str] = []
    if referenced:
        block_reasons.append("target_referenced")
    if locked:
        block_reasons.append("target_locked")
    return FixAction(
        fix_id="common.texture.version.latest:node:file1:relink_path",
        rule_id="common.texture.version.latest",
        title="Texture version should be latest available: relink_path",
        fix_type="relink_path",
        risk="medium",
        target_kind="file_dependency",
        target_id="node:file1",
        target_node="file1",
        target_attr=target_attr,
        before_value=before_value,
        after_value=after_value,
        explanation="Relink texture to latest approved version.",
        referenced=referenced,
        locked=locked,
        requires_reference_edit=referenced,
        blocked=bool(block_reasons),
        block_reasons=block_reasons,
        params={
            "type": "relink_path",
            "attribute": "fileTextureName",
            "path": after_value,
        },
    )


def _normalize_action(
    *,
    referenced: bool = False,
    locked: bool = False,
    before_value: str = "D:/show/assets/tex/albedo.exr",
    after_value: str = "$ASSET_ROOT/tex/albedo.exr",
) -> FixAction:
    block_reasons: list[str] = []
    if referenced:
        block_reasons.append("target_referenced")
    if locked:
        block_reasons.append("target_locked")
    return FixAction(
        fix_id="common.texture.path.local_drive:node:file1:normalize_path",
        rule_id="common.texture.path.local_drive",
        title="Texture path must not use a local drive root: normalize_path",
        fix_type="normalize_path",
        risk="medium",
        target_kind="file_dependency",
        target_id="node:file1",
        target_node="file1",
        target_attr="fileTextureName",
        before_value=before_value,
        after_value=after_value,
        explanation="Convert local path to approved project variable.",
        referenced=referenced,
        locked=locked,
        requires_reference_edit=referenced,
        blocked=bool(block_reasons),
        block_reasons=block_reasons,
        params={
            "type": "normalize_path",
            "attribute": "fileTextureName",
            "replace_from": "D:/show/assets",
            "replace_to": "$ASSET_ROOT",
        },
    )
