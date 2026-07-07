"""Resolve mayapy for Maya integration CI (GitHub Actions + local debug)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path


def _debug_log(message: str, data: dict, hypothesis_id: str) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "ee1eca",
            "runId": os.environ.get("DEBUG_RUN_ID", "ci"),
            "hypothesisId": hypothesis_id,
            "location": "tools/ci/resolve_mayapy.py",
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        log_path = Path(os.environ.get("DEBUG_SESSION_LOG", "debug-ee1eca.log"))
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except OSError:
        pass
    # endregion


def resolve_mayapy_path() -> Path:
    """Return the first usable mayapy path from env, PATH, or common install dirs."""

    _debug_log(
        "resolve_mayapy_start",
        {
            "has_input": bool(os.environ.get("MAYA_PY_INPUT", "").strip()),
            "has_secret": bool(os.environ.get("MAYA_PY_SECRET", "").strip()),
            "has_var": bool(os.environ.get("MAYA_PY_VAR", "").strip()),
            "has_env": bool(os.environ.get("MAYA_PY", "").strip()),
            "path_entries": (os.environ.get("PATH", "").count(os.pathsep) + 1),
            "os_name": os.name,
        },
        "H1",
    )

    candidates: list[str] = []
    for key in ("MAYA_PY_INPUT", "MAYA_PY_SECRET", "MAYA_PY_VAR", "MAYA_PY"):
        value = os.environ.get(key, "").strip()
        if value:
            candidates.append(value)

    which = shutil.which("mayapy")
    if which:
        candidates.append(which)

    candidates.extend(
        (
            r"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe",
            r"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe",
            "/usr/autodesk/maya2025/bin/mayapy",
            "/usr/autodesk/maya2024/bin/mayapy",
        )
    )

    seen: set[str] = set()
    checked: list[str] = []
    for raw in candidates:
        if not raw or raw in seen:
            continue
        seen.add(raw)
        path = Path(raw)
        checked.append(str(path))
        if path.is_file():
            resolved = path.resolve()
            _debug_log(
                "resolve_mayapy_found",
                {"path": str(resolved), "candidate_index": len(checked) - 1},
                "H2",
            )
            return resolved

    _debug_log(
        "resolve_mayapy_not_found",
        {"checked": checked[:12], "checked_count": len(checked)},
        "H3",
    )
    raise FileNotFoundError(
        "Maya integration requires mayapy on the self-hosted runner. "
        "Set repository secret MAYA_PY, variable MAYA_PY, runner env MAYA_PY, "
        "workflow input mayapy_path, or install mayapy on PATH."
    )


def main() -> int:
    resolved = resolve_mayapy_path()
    print(f"Using mayapy: {resolved}")

    github_output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"path={resolved}\n")
        _debug_log("resolve_mayapy_github_output", {"path": str(resolved)}, "H4")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
