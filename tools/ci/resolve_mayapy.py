"""Resolve mayapy for Maya integration CI (GitHub Actions + local debug)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def resolve_mayapy_path() -> Path:
    """Return the first usable mayapy path from env, PATH, or common install dirs."""

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
    for raw in candidates:
        if not raw or raw in seen:
            continue
        seen.add(raw)
        path = Path(raw)
        if path.is_file():
            return path.resolve()

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
            handle.write(f"mayapy_path={resolved}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
