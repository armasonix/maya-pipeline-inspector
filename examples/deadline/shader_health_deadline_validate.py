"""Farm worker script for MayaBatch Pipeline Inspector validation jobs."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _deadline_plugin_info(name: str, default: str = "") -> str:
    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]

        value = cmds.deadlinePluginInfo(name)
        return str(value) if value is not None else default
    except Exception:
        return os.environ.get(name, default)


def main() -> int:
    scene_path = Path(_deadline_plugin_info("SceneFile"))
    report_path = Path(
        _deadline_plugin_info("ReportPath", str(scene_path.with_suffix(".pipeline_inspector.json")))
    )
    profile_path = Path(_deadline_plugin_info("ProfilePath"))
    mayapy = _deadline_plugin_info("Mayapy", "mayapy")

    command = [
        mayapy,
        "-m",
        "pipeline_inspector",
        "validate",
        str(scene_path),
        "--input-kind",
        "scene",
        "--report",
        str(report_path),
        "--profile",
        str(profile_path),
    ]
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
