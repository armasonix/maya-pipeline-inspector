"""Restore repo files from agent transcript events BEFORE debug-cleanup request."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_MARKER = "maya-shader-health-inspector"
CUTOFF_MARKERS = (
    "убрать всю дебаг инструментацию",
    "_strip_debug_instrumentation",
    "strip_agent_debug",
    "strip debug instrumentation",
)


@dataclass
class Event:
    idx: int
    line_no: int
    source: str
    kind: str
    rel_path: Path
    content: str | None = None
    old: str | None = None
    new: str | None = None


def pick_first_str(d: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = d.get(key)
        if isinstance(value, str):
            return value
    return None


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from iter_dicts(v)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dicts(item)


def to_rel_path(raw_path: str, repo_root: Path) -> Path | None:
    normalized = raw_path.replace("\\", "/")
    lower = normalized.lower()
    marker = REPO_MARKER.lower()
    if marker not in lower:
        return None
    tail = normalized[normalized.lower().index(marker) + len(marker) :].lstrip("/\\")
    if not tail:
        return None
    rel = Path(tail)
    if ".." in rel.parts:
        return None
    return rel


def extract_events_from_line(
    obj: dict[str, Any],
    *,
    idx_base: int,
    line_no: int,
    source: str,
    repo_root: Path,
) -> list[Event]:
    events: list[Event] = []
    idx = idx_base
    for d in iter_dicts(obj):
        if d.get("type") != "tool_use":
            continue
        tool_name = d.get("name")
        if tool_name not in {"Write", "StrReplace"}:
            continue
        tool_input = d.get("input")
        if not isinstance(tool_input, dict):
            continue
        raw_path = pick_first_str(tool_input, ["path", "file_path", "filepath", "target_file"])
        if not raw_path:
            continue
        rel_path = to_rel_path(raw_path, repo_root)
        if rel_path is None:
            continue
        if tool_name == "Write":
            content = pick_first_str(
                tool_input,
                ["content", "contents", "text", "file_text", "new_content"],
            )
            if content is None:
                continue
            events.append(
                Event(
                    idx=idx,
                    line_no=line_no,
                    source=source,
                    kind="write",
                    rel_path=rel_path,
                    content=content,
                )
            )
            idx += 1
            continue
        old_value = pick_first_str(tool_input, ["old_str", "old_string", "old", "search"])
        new_value = pick_first_str(tool_input, ["new_str", "new_string", "new", "replace"])
        if old_value is None or new_value is None:
            continue
        events.append(
            Event(
                idx=idx,
                line_no=line_no,
                source=source,
                kind="replace",
                rel_path=rel_path,
                old=old_value,
                new=new_value,
            )
        )
        idx += 1
    return events


def reconstruct(
    events: list[Event], *, base_content: str | None = None
) -> tuple[str | None, list[str]]:
    if not events:
        return None, ["no events"]
    ordered = sorted(events, key=lambda e: (e.line_no, e.idx))
    writes = [e for e in ordered if e.kind == "write"]
    if not writes:
        if base_content is None:
            return None, ["no Write event and no base content"]
        content = base_content
        notes: list[str] = ["using git HEAD as base for StrReplace-only file"]
        for event in ordered:
            if event.kind != "replace":
                continue
            old = event.old or ""
            new = event.new or ""
            if old in content:
                content = content.replace(old, new, 1)
            else:
                notes.append(f"replace miss line {event.line_no}")
        return content, notes

    last_write = writes[-1]
    content = last_write.content or ""
    notes: list[str] = []
    last_write_key = (last_write.line_no, last_write.idx)
    for event in ordered:
        if (event.line_no, event.idx) <= last_write_key:
            continue
        if event.kind != "replace":
            continue
        old = event.old or ""
        new = event.new or ""
        if old in content:
            content = content.replace(old, new, 1)
        else:
            notes.append(f"replace miss line {event.line_no} idx {event.idx}")
    return content, notes


def git_head_content(repo_root: Path, rel_path: Path) -> str | None:
    import subprocess

    rel_posix = rel_path.as_posix()
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_posix}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def find_cutoff_line(transcript_files: list[Path]) -> int:
    for transcript_file in transcript_files:
        with transcript_file.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                lower = raw.lower()
                if any(marker in lower for marker in CUTOFF_MARKERS):
                    return line_no
    return 10**9


def collect_events(
    transcript_root: Path, repo_root: Path, cutoff_line: int
) -> dict[Path, list[Event]]:
    by_path: dict[Path, list[Event]] = {}
    idx = 0
    files = sorted(transcript_root.rglob("*.jsonl"), key=lambda p: (p.stat().st_mtime, str(p)))
    for transcript_file in files:
        with transcript_file.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                if line_no >= cutoff_line and transcript_file.name.startswith(
                    "88835a31-114c-4ca1-b7f9-bd3d26b13840"
                ):
                    continue
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                events = extract_events_from_line(
                    obj,
                    idx_base=idx,
                    line_no=line_no,
                    source=str(transcript_file),
                    repo_root=repo_root,
                )
                if not events:
                    continue
                idx = max(e.idx for e in events) + 1
                for event in events:
                    by_path.setdefault(event.rel_path, []).append(event)
    return by_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    transcript_root = Path(args.transcript_root)
    repo_root = Path(args.repo_root)
    main_transcript = transcript_root / "88835a31-114c-4ca1-b7f9-bd3d26b13840.jsonl"
    cutoff = find_cutoff_line([main_transcript] if main_transcript.is_file() else [])
    by_path = collect_events(transcript_root, repo_root, cutoff)

    restored = 0
    skipped = 0
    report: list[str] = []
    for rel_path in sorted(by_path, key=str):
        if rel_path.suffix != ".py" and rel_path.suffix != ".mel" and rel_path.suffix != ".qss":
            skipped += 1
            continue
        if rel_path.parts[0] in {".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__"}:
            skipped += 1
            continue
        content, notes = reconstruct(
            by_path[rel_path], base_content=git_head_content(repo_root, rel_path)
        )
        if content is None:
            report.append(f"SKIP {rel_path}: no content")
            continue
        target = repo_root / rel_path
        if args.dry_run:
            report.append(f"DRY {rel_path}: {len(content.splitlines())} lines")
            restored += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        note_text = f" ({len(notes)} replace misses)" if notes else ""
        report.append(f"OK {rel_path}: {len(content.splitlines())} lines{note_text}")
        restored += 1

    print(f"cutoff_line={cutoff}")
    print(f"restored={restored} skipped={skipped}")
    for line in report:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
