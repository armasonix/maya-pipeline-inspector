from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from examples.deadline import submit_preflight


def test_example_reexports_integration_constants():
    assert submit_preflight.VALIDATOR_OK == 0
    assert submit_preflight.SUBMISSION_BLOCKED == 2
    assert submit_preflight.run_deadline_preflight is not None


def test_example_wrapper_still_blocks_on_farm_issue(tmp_path: Path):
    def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, submit_preflight.VALIDATOR_DEADLINE_BLOCK)

    result = submit_preflight.run_deadline_preflight(
        scene_path=tmp_path / "scene.ma",
        report_path=tmp_path / "report.json",
        profile_path=tmp_path / "deadline_critical.json",
        runner=runner,
    )
    assert result.allowed is False
    assert result.exit_code == submit_preflight.SUBMISSION_BLOCKED
