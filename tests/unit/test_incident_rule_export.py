from __future__ import annotations

import json
from pathlib import Path

from shader_health.core.rule_wizard import (
    RULE_TEMPLATE_PATH_EXISTS,
    IncidentRuleExportContext,
    NewRuleDraftInput,
    build_incident_rule_sidecar_payload,
    build_rule_draft,
    export_incident_rule_draft_to_studio_extra_rules,
    incident_rule_sidecar_path,
    studio_extra_rules_folder,
)
from shader_health.studio_config import PipelineSettings, StudioConfig


def test_build_incident_rule_sidecar_payload_includes_metadata():
    draft = {"id": "studio.custom.test", "name": "Test"}

    payload = build_incident_rule_sidecar_payload(
        draft,
        source_rule_id="common.texture.missing",
        scene_path="/show/scenes/demo.ma",
        exported_at_utc="2026-07-11T08:00:00+00:00",
    )

    assert payload["exported_from"] == "incident"
    assert payload["source_rule_id"] == "common.texture.missing"
    assert payload["scene_path"] == "/show/scenes/demo.ma"
    assert payload["rules"][0]["id"] == "studio.custom.test"


def test_export_incident_rule_draft_writes_valid_sidecar(tmp_path: Path):
    draft = build_rule_draft(
        RULE_TEMPLATE_PATH_EXISTS,
        NewRuleDraftInput(
            rule_id="studio.incident.texture.missing.draft",
            name="Missing texture incident rule",
            message="Texture file is missing.",
            why="Missing textures fail on farm.",
            severity="critical",
            dependency_kind="texture",
        ),
    )
    export_dir = tmp_path / "extra_rules"

    result = export_incident_rule_draft_to_studio_extra_rules(
        draft,
        export_dir,
        export_context=IncidentRuleExportContext(
            source_rule_id="common.texture.missing",
            scene_path=str(tmp_path / "demo.ma"),
        ),
        known_rule_ids=frozenset(),
    )

    assert result.success is True
    assert result.path == incident_rule_sidecar_path(export_dir, draft["id"]).resolve()
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert payload["source_rule_id"] == "common.texture.missing"
    assert payload["rules"][0]["id"] == "studio.incident.texture.missing.draft"


def test_studio_extra_rules_folder_reads_pipeline_setting():
    config = StudioConfig(
        pipeline=PipelineSettings(extra_rules_folder="//studio/share/extra_rules")
    )

    assert studio_extra_rules_folder(config) == Path("//studio/share/extra_rules")
