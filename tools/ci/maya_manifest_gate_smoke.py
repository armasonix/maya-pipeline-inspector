"""Export a manifest and gate against it in one mayapy process (Maya CI smoke)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shader_health import cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manifest export + gate smoke in one Maya session.",
    )
    parser.add_argument("scene_path", type=Path)
    parser.add_argument("--profile-id", default="publish_strict")
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--gate-out", type=Path, required=True)
    args = parser.parse_args(argv)

    manifest_code = cli.main(
        [
            "manifest",
            str(args.scene_path),
            "--input-kind",
            "scene",
            "--profile-id",
            args.profile_id,
            "--out",
            str(args.manifest_out),
        ]
    )
    if manifest_code != cli.EXIT_OK:
        print(
            f"::error::Manifest export smoke failed with exit code {manifest_code}",
            file=sys.stderr,
        )
        return manifest_code

    gate_code = cli.main(
        [
            "gate",
            str(args.scene_path),
            str(args.manifest_out),
            "--input-kind",
            "scene",
            "--profile-id",
            args.profile_id,
            "--out",
            str(args.gate_out),
        ]
    )
    if gate_code not in (cli.EXIT_OK,):
        print(f"::error::Manifest gate smoke failed with exit code {gate_code}", file=sys.stderr)
        return gate_code if gate_code != cli.EXIT_PUBLISH_BLOCK else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
