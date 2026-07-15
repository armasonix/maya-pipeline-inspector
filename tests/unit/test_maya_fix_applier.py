from __future__ import annotations

from typing import Any, Optional

from pipeline_inspector.core.fix_plan import FixAction
from pipeline_inspector.maya.fix_applier import apply_fix_actions


class FakeCmds:
    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        self.attrs = attrs or {}
        self.nodes: dict[str, str] = {}
        self.read_only_nodes: set[str] = set()
        self.referenced_nodes: set[str] = set()
        self.locked_nodes: set[str] = set()
        self.undo_calls: list[dict[str, Any]] = []
        self.set_calls: list[tuple[str, Any, dict[str, Any]]] = []
        self.rename_calls: list[tuple[str, str]] = []

    def undoInfo(self, **kwargs: Any) -> None:
        self.undo_calls.append(dict(kwargs))

    def objExists(self, node_name: str) -> bool:
        if node_name in self.nodes:
            return True
        prefix = f"{node_name}."
        return any(plug.startswith(prefix) for plug in self.attrs)

    def ls(self, node_name: str, shortNames: bool = False) -> list[str]:
        if node_name in self.nodes:
            return [self.nodes[node_name]]
        if self.objExists(node_name):
            return [node_name]
        return []

    def rename(self, node_name: str, new_name: str) -> str:
        if node_name in self.read_only_nodes:
            raise RuntimeError("Cannot rename a read only node.")
        self.rename_calls.append((node_name, new_name))
        current = self.nodes.get(node_name, node_name)
        parent = "|".join(current.split("|")[:-1])
        renamed = f"{parent}|{new_name}" if parent else new_name
        self.nodes[node_name] = renamed
        self.nodes[renamed] = renamed
        return renamed

    def lockNode(self, node_name: str, **kwargs: Any) -> bool:
        if kwargs.get("q") and kwargs.get("lock"):
            return node_name in self.locked_nodes
        return False

    def referenceQuery(self, node_name: str, **kwargs: Any) -> bool:
        if kwargs.get("isNodeReferenced"):
            return node_name in self.referenced_nodes
        if kwargs.get("isReadOnly"):
            return node_name in self.read_only_nodes
        return False

    def getAttr(self, plug: str) -> Any:
        return self.attrs[plug]

    def setAttr(self, plug: str, value: Any, **kwargs: Any) -> None:
        self.set_calls.append((plug, value, dict(kwargs)))
        self.attrs[plug] = value


def test_apply_rename_texture_file_renames_disk_file_and_updates_path(tmp_path):
    texture_file = tmp_path / "albedo_wrong.exr"
    texture_file.write_bytes(b"fixture")
    cmds = FakeCmds({"file1.fileTextureName": str(texture_file)})
    cmds.nodes["file1"] = "file1"
    action = FixAction(
        fix_id="studio.naming.texture.pattern:node:file1:rename_texture_file",
        rule_id="studio.naming.texture.pattern",
        title="Texture file name must match studio naming template: rename texture file",
        fix_type="rename_texture_file",
        risk="medium",
        target_kind="node",
        target_id="node:file1",
        target_node="file1",
        target_attr="fileTextureName",
        before_value=str(texture_file),
        after_value=str(tmp_path / "tex_albedo_wrong.exr"),
        params={
            "resolved_before": str(texture_file),
            "is_udim": False,
            "node_name_after": "tex_albedo_wrong",
        },
    )

    report = apply_fix_actions([action], cmds=cmds)

    assert report.applied_count == 1
    assert not texture_file.exists()
    assert (tmp_path / "tex_albedo_wrong.exr").is_file()
    assert cmds.attrs["file1.fileTextureName"] == str(tmp_path / "tex_albedo_wrong.exr")
    assert cmds.rename_calls == [("file1", "tex_albedo_wrong")]


def test_apply_rename_node_updates_short_name_inside_undo_chunk():
    cmds = FakeCmds()
    cmds.nodes["|world|body_bad"] = "|world|body_bad"
    action = FixAction(
        fix_id="studio.naming.mesh.pattern:mesh:body_bad:rename_node",
        rule_id="studio.naming.mesh.pattern",
        title="Mesh name must match studio naming template: rename",
        fix_type="rename_node",
        risk="low",
        target_kind="shape",
        target_id="mesh:body_bad",
        target_node="|world|body_bad",
        before_value="body_bad",
        after_value="geo_body_bad",
    )

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.rename_calls == [("|world|body_bad", "geo_body_bad")]
    assert report.applied_count == 1
    record = report.records[0]
    assert record.before_value == "body_bad"
    assert record.after_value == "geo_body_bad"


def test_apply_rename_node_blocks_read_only_target_without_crashing():
    cmds = FakeCmds()
    cmds.nodes["|world|body_bad"] = "|world|body_bad"
    cmds.read_only_nodes.add("|world|body_bad")
    cmds.referenced_nodes.add("|world|body_bad")
    action = FixAction(
        fix_id="studio.naming.mesh.pattern:mesh:body_bad:rename_node",
        rule_id="studio.naming.mesh.pattern",
        title="Mesh name must match studio naming template: rename",
        fix_type="rename_node",
        risk="low",
        target_kind="shape",
        target_id="mesh:body_bad",
        target_node="|world|body_bad",
        before_value="body_bad",
        after_value="geo_body_bad",
    )

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.rename_calls == []
    assert report.applied_count == 0
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["target_read_only"]


def test_apply_fix_actions_uses_undo_chunk_and_records_before_after_values():
    cmds = FakeCmds({"file1.colorSpace": "ACEScg"})
    action = _action()

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.undo_calls == [
        {"openChunk": True, "chunkName": "Pipeline Inspector Apply Fixes"},
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
        "undo_chunk_name": "Pipeline Inspector Apply Fixes",
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
        {"openChunk": True, "chunkName": "Pipeline Inspector Apply Fixes"},
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


def test_apply_normalize_path_uses_asset_root_basename_when_prefix_does_not_match():
    cmds = FakeCmds({"file1.fileTextureName": "//legacy_server/random/albedo.exr"})
    action = _normalize_action()

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == [
        ("file1.fileTextureName", "$ASSET_ROOT/textures/albedo.exr", {"type": "string"}),
    ]
    assert report.applied_count == 1


def test_apply_disable_feature_sets_bool_attribute_with_confirmation():
    cmds = FakeCmds({"displacementShader1.aiDispersion": True})
    action = _disable_feature_action()

    report = apply_fix_actions([action], cmds=cmds, allow_high_risk=True)

    assert report.applied_count == 1
    assert cmds.set_calls == [("displacementShader1.aiDispersion", False, {})]
    record = report.records[0]
    assert record.fix_type == "disable_feature"
    assert record.before_value is True
    assert record.after_value is False


def test_apply_disable_feature_blocks_without_high_risk_confirmation():
    cmds = FakeCmds({"displacementShader1.aiDispersion": True})
    action = _disable_feature_action()

    report = apply_fix_actions([action], cmds=cmds)

    assert cmds.set_calls == []
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["high_risk_requires_explicit_confirmation"]


def test_apply_disable_feature_blocks_referenced_targets_by_default():
    cmds = FakeCmds({"displacementShader1.aiDispersion": True})
    action = _disable_feature_action(referenced=True)

    report = apply_fix_actions([action], cmds=cmds, allow_high_risk=True)

    assert cmds.set_calls == []
    assert report.blocked_count == 1
    assert report.records[0].block_reasons == ["target_referenced"]


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


def _disable_feature_action(
    *,
    referenced: bool = False,
    locked: bool = False,
    target_attr: str = "aiDispersion",
    before_value: bool = True,
    after_value: bool = False,
) -> FixAction:
    block_reasons: list[str] = ["high_risk_requires_explicit_confirmation"]
    if referenced:
        block_reasons.insert(0, "target_referenced")
    if locked:
        block_reasons.insert(0, "target_locked")
    return FixAction(
        fix_id="common.displacement.amount.max:node:displacementShader1:disable_feature",
        rule_id="common.displacement.amount.max",
        title="Displacement amount must stay within the risk budget: disable_feature",
        fix_type="disable_feature",
        risk="high",
        target_kind="node",
        target_id="node:displacementShader1",
        target_node="displacementShader1",
        target_attr=target_attr,
        before_value=before_value,
        after_value=after_value,
        explanation="Disable risky displacement feature.",
        referenced=referenced,
        locked=locked,
        requires_reference_edit=referenced,
        requires_supervisor=True,
        blocked=referenced or locked,
        block_reasons=block_reasons,
        params={
            "type": "disable_feature",
            "attribute": target_attr,
            "value": after_value,
        },
    )
