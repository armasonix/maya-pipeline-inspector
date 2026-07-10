from __future__ import annotations

from pathlib import Path
from typing import Optional

from shader_health.core.fix_plan import (
    FixAction,
    build_fix_plan,
    fix_plan_from_export,
    project_root_from_scene,
    replace_path_prefix,
    resolve_normalize_path_value,
)
from shader_health.core.models import GraphSnapshot, MaterialSnapshot, NodeSnapshot
from shader_health.core.rule_schema import (
    RuleCheck,
    RuleDefinition,
    RuleFix,
    RuleMatch,
    RulePolicy,
    RuleResult,
)
from shader_health.studio_config import StudioEnvironmentSettings


def test_fix_planner_builds_action_for_failed_result_with_rule_fix():
    rule = _rule_with_fix()
    result = _failed_result()
    snapshot = _snapshot(
        NodeSnapshot(
            id="node:file1",
            name="file1",
            full_name="asset:file1",
            type_name="file",
            attrs={"colorSpace": "ACEScg"},
        )
    )

    plan = build_fix_plan([result], [rule], snapshot)

    assert plan.total == 1
    assert plan.safe_count == 1
    assert plan.blocked_count == 0
    action = plan.actions[0]
    assert action.rule_id == "common.texture.colorspace.data_raw"
    assert action.fix_type == "set_attr"
    assert action.risk == "low"
    assert action.target_node == "asset:file1"
    assert action.target_attr == "colorSpace"
    assert action.before_value == "ACEScg"
    assert action.after_value == "Raw"
    assert action.referenced is False
    assert action.locked is False
    assert action.blocked is False


def test_fix_planner_skips_non_failed_results_and_rules_without_fix():
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))
    passed = _failed_result(status="passed")
    no_fix_rule = _rule_without_fix()

    plan = build_fix_plan([passed, _failed_result()], [no_fix_rule], snapshot)

    assert plan.total == 0
    assert plan.to_dict() == {
        "total": 0,
        "safe_count": 0,
        "blocked_count": 0,
        "actions": [],
    }


def test_fix_plan_from_export_preserves_blocked_actions():
    action = FixAction(
        fix_id="rule:node:set_attr",
        rule_id="rule",
        title="title",
        fix_type="set_attr",
        risk="high",
        target_kind="node",
        target_id="node:file1",
        target_node="file1",
        blocked=True,
        block_reasons=["high_risk_requires_explicit_confirmation"],
    )
    plan = fix_plan_from_export({"actions": [action.to_dict()]})
    assert plan.blocked_count == 1
    assert plan.actions[0].blocked is True


def test_fix_planner_includes_referenced_and_locked_status():
    rule = _rule_with_fix()
    result = _failed_result()
    snapshot = _snapshot(
        NodeSnapshot(
            id="node:file1",
            name="file1",
            type_name="file",
            referenced=True,
            reference_path="D:/show/assets/char/hero.ma",
            locked=True,
        )
    )

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.referenced is True
    assert action.locked is True
    assert action.reference_path == "D:/show/assets/char/hero.ma"
    assert action.requires_reference_edit is True
    assert action.blocked is True
    assert action.block_reasons == ["target_locked"]
    assert plan.blocked_count == 1


def test_fix_planner_allows_referenced_fixes_when_not_locked():
    rule = _rule_with_fix()
    result = _failed_result()
    snapshot = _snapshot(
        NodeSnapshot(
            id="node:file1",
            name="file1",
            type_name="file",
            referenced=True,
            reference_path="D:/show/assets/char/hero.ma",
        )
    )

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.referenced is True
    assert action.requires_reference_edit is True
    assert action.blocked is False
    assert action.block_reasons == []


def test_fix_planner_marks_high_risk_actions_as_supervisor_required_and_blocked():
    rule = _rule_with_fix(
        fix=RuleFix(
            type="cleanup_orphan",
            risk="high",
            params={"value": "delete_unused_network"},
        )
    )
    result = _failed_result()
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.risk == "high"
    assert action.requires_supervisor is True
    assert action.undo_supported is False
    assert action.blocked is False
    assert action.block_reasons == ["high_risk_requires_explicit_confirmation"]


def test_fix_planner_resolves_material_target_to_underlying_node():
    rule = _rule_with_fix()
    result = _failed_result(
        target_kind="material",
        target_id="node:mat1",
        node="mat1",
    )
    snapshot = GraphSnapshot(
        nodes=(
            NodeSnapshot(
                id="node:mat1",
                name="mat1",
                full_name="asset:mat1",
                type_name="VRayMtl",
                referenced=True,
            ),
        ),
        materials=(
            MaterialSnapshot(
                node_id="node:mat1",
                name="mat1",
                type_name="VRayMtl",
            ),
        ),
    )

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.target_node == "asset:mat1"
    assert action.referenced is True
    assert action.block_reasons == []
    assert action.blocked is False


def test_replace_path_prefix_rewrites_matching_root():
    assert replace_path_prefix(
        "D:/show/assets/tex/albedo.exr",
        "D:/show/assets",
        "$ASSET_ROOT",
    ) == "$ASSET_ROOT/tex/albedo.exr"


def test_resolve_normalize_path_value_uses_replace_from_and_replace_to():
    assert resolve_normalize_path_value(
        "D:/show/assets/tex/albedo.exr",
        {
            "replace_from": "D:/show/assets",
            "replace_to": "$ASSET_ROOT",
        },
    ) == "$ASSET_ROOT/tex/albedo.exr"


def test_resolve_normalize_path_value_uses_scene_project_root_fallback(tmp_path: Path):
    repo_root = tmp_path / "repo"
    (repo_root / "src" / "shader_health").mkdir(parents=True)
    scene_path = repo_root / "examples" / "broken_scene" / "demo.ma"
    scene_path.parent.mkdir(parents=True)
    texture_path = repo_root / "examples" / "broken_scene" / "textures" / "demo.exr"
    texture_path.parent.mkdir(parents=True)

    assert resolve_normalize_path_value(
        str(texture_path).replace("\\", "/"),
        {"replace_to": "${ASSET_ROOT}"},
        scene_path=str(scene_path).replace("\\", "/"),
    ) == "${ASSET_ROOT}/examples/broken_scene/textures/demo.exr"


def test_resolve_normalize_path_value_maps_user_home_path_to_asset_root_textures():
    assert resolve_normalize_path_value(
        "C:/Users/ledorub3d/Documents/local_only_texture.exr",
        {"replace_to": "${ASSET_ROOT}"},
        scene_path="D:/Workspace/portfolio/maya-shader-health-inspector/examples/broken_scene/demo.ma",
    ) == "${ASSET_ROOT}/textures/local_only_texture.exr"


def test_resolve_normalize_path_value_maps_studio_texture_root_to_token():
    environment = StudioEnvironmentSettings(texture_root="\\\\farm\\textures")

    assert resolve_normalize_path_value(
        "\\\\farm\\textures/hero/albedo.exr",
        {"replace_to": "${ASSET_ROOT}"},
        studio_environment=environment,
    ) == "${STUDIO_TEXTURE_ROOT}/hero/albedo.exr"


def test_resolve_normalize_path_value_uses_studio_asset_root_for_local_paths():
    environment = StudioEnvironmentSettings(asset_root="\\\\farm\\assets")

    assert resolve_normalize_path_value(
        "C:/Users/ledorub3d/Documents/local_only_texture.exr",
        {"replace_to": "${ASSET_ROOT}"},
        scene_path="D:/Workspace/portfolio/maya-shader-health-inspector/examples/broken_scene/demo.ma",
        studio_environment=environment,
    ) == "${STUDIO_ASSET_ROOT}/textures/local_only_texture.exr"


def test_build_fix_plan_embeds_studio_environment_in_normalize_path_params():
    environment = StudioEnvironmentSettings(texture_root="\\\\farm\\textures")
    rule = _rule(
        fix=RuleFix(
            type="normalize_path",
            risk="medium",
            params={"attribute": "fileTextureName", "replace_to": "${ASSET_ROOT}"},
        ),
    )
    from shader_health.core.models import FileDependencySnapshot

    snapshot = GraphSnapshot(
        scene_path="D:/show/scenes/demo.ma",
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file1",
                attr="fileTextureName",
                raw_path="D:/local/albedo.exr",
                resolved_path="D:/local/albedo.exr",
            )
        ],
    )
    result = _failed_result(
        target_kind="file_dependency",
        target_id="node:file1",
        current_value="D:/local/albedo.exr",
    )

    plan = build_fix_plan(
        [result],
        [rule],
        snapshot,
        studio_environment=environment,
    )

    assert plan.actions[0].params["studio_environment"]["texture_root"] == "\\\\farm\\textures"


def test_project_root_from_scene_detects_shader_health_repo(tmp_path: Path):
    repo_root = tmp_path / "repo"
    (repo_root / "src" / "shader_health").mkdir(parents=True)
    scene_path = repo_root / "examples" / "broken_scene" / "demo.ma"

    root = project_root_from_scene(str(scene_path).replace("\\", "/"))
    assert root == str(repo_root).replace("\\", "/")


def test_fix_planner_builds_relink_path_action_from_texture_version_failure():
    rule = _rule(
        fix=RuleFix(
            type="relink_path",
            risk="medium",
            params={"attribute": "fileTextureName"},
        ),
    )
    result = _failed_result(
        plug="version",
        current_value="001",
        target_kind="file_dependency",
        target_id="node:file1",
    )
    result = RuleResult(
        rule_id=result.rule_id,
        severity=result.severity,
        status="failed",
        title=result.title,
        message=result.message,
        why=result.why,
        owner=result.owner,
        target_kind="file_dependency",
        target_id="node:file1",
        node="file1",
        plug="version",
        current_value="001",
        expected_value="003",
        auto_fix_available=True,
        fix_id="relink_path",
    )
    from shader_health.core.models import FileDependencySnapshot

    snapshot = GraphSnapshot(
        file_dependencies=[
            FileDependencySnapshot(
                node_id="node:file1",
                attr="fileTextureName",
                raw_path="D:/show/tex/albedo_v001.<UDIM>.exr",
                resolved_path="D:/show/tex/albedo_v001.<UDIM>.exr",
                exists=True,
                version="001",
                latest_version="003",
            )
        ],
    )

    plan = build_fix_plan([result], [rule], snapshot)
    action = plan.actions[0]

    assert action.fix_type == "relink_path"
    assert action.before_value == "D:/show/tex/albedo_v001.<UDIM>.exr"
    assert action.after_value == "D:/show/tex/albedo_v003.<UDIM>.exr"


def test_fix_planner_blocks_normalize_path_when_target_cannot_be_resolved():
    rule = RuleDefinition(
        id="common.texture.path.local_drive",
        name="local drive",
        enabled=True,
        renderer=["common"],
        scope="file_dependency",
        severity="critical",
        owner="pipeline_td",
        message="local",
        why="local",
        match=RuleMatch(criteria={"dependency_kind": "texture"}),
        check=RuleCheck(type="path_policy", params={"disallow": ["local_drive"]}),
        policy=RulePolicy(auto_fix_allowed=True),
        fix=RuleFix(
            type="normalize_path",
            risk="medium",
            params={"attribute": "fileTextureName", "replace_to": "${ASSET_ROOT}"},
        ),
    )
    result = RuleResult(
        rule_id=rule.id,
        severity="critical",
        status="failed",
        title=rule.name,
        message=rule.message,
        why=rule.why,
        owner=rule.owner,
        target_kind="file_dependency",
        target_id="node:file1",
        node="file1",
        plug="fileTextureName",
        current_value="Z:/no/scene/root/file.exr",
        expected_value="path policy compliant",
        auto_fix_available=True,
        fix_id="normalize_path",
    )
    snapshot = GraphSnapshot(scene_path="")

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.blocked is False
    assert action.after_value == "${ASSET_ROOT}/textures/file.exr"


def test_fix_planner_blocks_normalize_path_when_after_value_cannot_be_resolved():
    rule = RuleDefinition(
        id="common.texture.path.local_drive",
        name="local drive",
        enabled=True,
        renderer=["common"],
        scope="file_dependency",
        severity="critical",
        owner="pipeline_td",
        message="local",
        why="local",
        match=RuleMatch(criteria={"dependency_kind": "texture"}),
        check=RuleCheck(type="path_policy", params={"disallow": ["local_drive"]}),
        policy=RulePolicy(auto_fix_allowed=True),
        fix=RuleFix(
            type="normalize_path",
            risk="medium",
            params={"attribute": "fileTextureName", "replace_to": "${ASSET_ROOT}"},
        ),
    )
    result = RuleResult(
        rule_id=rule.id,
        severity="critical",
        status="failed",
        title=rule.name,
        message=rule.message,
        why=rule.why,
        owner=rule.owner,
        target_kind="file_dependency",
        target_id="node:file1",
        node="file1",
        plug="fileTextureName",
        current_value="",
        expected_value="path policy compliant",
        auto_fix_available=True,
        fix_id="normalize_path",
    )
    snapshot = GraphSnapshot(scene_path="")

    plan = build_fix_plan([result], [rule], snapshot)

    assert plan.actions[0].blocked is True
    assert "invalid_normalize_path" in plan.actions[0].block_reasons


def test_fix_planner_builds_normalize_path_action_from_rule_fix():
    rule = _rule(
        fix=RuleFix(
            type="normalize_path",
            risk="medium",
            params={
                "attribute": "fileTextureName",
                "replace_from": "D:/show/assets",
                "replace_to": "$ASSET_ROOT",
            },
        )
    )
    result = _failed_result(
        plug="fileTextureName",
        current_value="D:/show/assets/tex/albedo.exr",
    )
    snapshot = _snapshot(NodeSnapshot(id="node:file1", name="file1", type_name="file"))

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.fix_type == "normalize_path"
    assert action.risk == "medium"
    assert action.target_attr == "fileTextureName"
    assert action.after_value == "$ASSET_ROOT/tex/albedo.exr"


def test_fix_planner_builds_disable_feature_action_with_default_false_value():
    rule = _rule(
        fix=RuleFix(
            type="disable_feature",
            risk="high",
            params={"attribute": "aiDispersion"},
        ),
    )
    result = _failed_result(
        plug="aiDispersion",
        current_value=True,
    )
    snapshot = _snapshot(
        NodeSnapshot(id="node:disp1", name="disp1", type_name="displacementShader")
    )

    plan = build_fix_plan([result], [rule], snapshot)

    action = plan.actions[0]
    assert action.fix_type == "disable_feature"
    assert action.target_attr == "aiDispersion"
    assert action.after_value is False
    assert action.blocked is False
    assert action.block_reasons == ["high_risk_requires_explicit_confirmation"]


def _rule_with_fix(fix: Optional[RuleFix] = None) -> RuleDefinition:
    return _rule(fix=_default_fix() if fix is None else fix)


def _rule_without_fix() -> RuleDefinition:
    return _rule(fix=None, auto_fix_allowed=False)


def _rule(
    *,
    fix: Optional[RuleFix],
    auto_fix_allowed: bool = True,
) -> RuleDefinition:
    return RuleDefinition(
        id="common.texture.colorspace.data_raw",
        name="Data textures must use Raw color space",
        enabled=True,
        renderer=["common"],
        scope="texture_node",
        severity="critical",
        owner="shader_td",
        message="Data texture uses a color-managed color space.",
        why="Data textures must not be color transformed.",
        match=RuleMatch(criteria={"node_type": ["file"]}),
        check=RuleCheck(type="attribute_equals", params={"attribute": "colorSpace"}),
        policy=RulePolicy(auto_fix_allowed=auto_fix_allowed),
        fix=fix,
    )


def _default_fix() -> RuleFix:
    return RuleFix(
        type="set_attr",
        risk="low",
        params={"attribute": "colorSpace", "value": "Raw"},
    )


def _failed_result(
    *,
    status: str = "failed",
    target_kind: str = "node",
    target_id: str = "node:file1",
    node: str = "file1",
    plug: str = "colorSpace",
    current_value: str = "ACEScg",
) -> RuleResult:
    return RuleResult(
        rule_id="common.texture.colorspace.data_raw",
        severity="critical",
        status=status,
        title="Data textures must use Raw color space",
        message="Data texture uses a color-managed color space.",
        why="Data textures must not be color transformed.",
        owner="shader_td",
        target_kind=target_kind,
        target_id=target_id,
        node=node,
        plug=plug,
        current_value=current_value,
        expected_value="Raw",
        auto_fix_available=True,
        fix_id="set_attr",
    )


def _snapshot(node: NodeSnapshot) -> GraphSnapshot:
    return GraphSnapshot(nodes=(node,))
