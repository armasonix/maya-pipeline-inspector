"""Regression guards for CI/debug hygiene baseline (#166)."""
from __future__ import annotations

import logging
from pathlib import Path

from pipeline_inspector.ui.user_preferences_ui import _apply_debug_logging

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = REPO_ROOT / ".github" / "workflows"
FORBIDDEN_DEBUG_MARKERS = (
    "agent_debug_log",
    "_debug_session_trace",
    "DEBUG_SESSION_LOG",
    "DEBUG_RUN_ID",
)


def test_apply_debug_logging_targets_pipeline_inspector_namespace():
    logger = logging.getLogger("pipeline_inspector")
    other_logger = logging.getLogger("pipeline_inspector.maya.scanner")

    _apply_debug_logging(True)
    assert logger.level == logging.DEBUG
    assert other_logger.level == logging.NOTSET

    _apply_debug_logging(False)
    assert logger.level == logging.INFO


def test_workflows_do_not_reference_debug_session_env():
    workflow_files = sorted(WORKFLOW_ROOT.glob("*.yml"))
    assert workflow_files, "Expected GitHub workflow files under .github/workflows"

    for workflow_file in workflow_files:
        text = workflow_file.read_text(encoding="utf-8")
        for marker in FORBIDDEN_DEBUG_MARKERS:
            assert marker not in text, f"{workflow_file.name} still references {marker}"


def test_repo_has_no_agent_debug_trace_references():
    search_roots = (
        REPO_ROOT / "src",
        REPO_ROOT / "tools",
        REPO_ROOT / "maya_module",
        REPO_ROOT / ".github",
    )
    allowed_suffixes = {".py", ".yml", ".yaml", ".md", ".mel", ".ps1", ".sh"}
    forbidden_markers = ("agent_debug_log", "_debug_session_trace")

    for root in search_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in allowed_suffixes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in forbidden_markers:
                assert marker not in text, (
                    f"{path.relative_to(REPO_ROOT)} still references {marker}"
                )
