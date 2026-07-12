from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_SUFFIXES = [
    "test_ftrack_client.py",
    "test_maya_ui_launcher.py",
    "test_settings_panel.py",
]

RECOVERY_RELATIVE_PATHS = {
    "test_ftrack_client.py": Path("tests/unit/test_ftrack_client.py"),
    "test_maya_ui_launcher.py": Path("tests/unit/test_maya_ui_launcher.py"),
    "test_settings_panel.py": Path("tests/unit/test_settings_panel.py"),
}


@dataclass
class Event:
    idx: int
    line_no: int
    source: str
    kind: str
    path: str
    content: str | None = None
    old: str | None = None
    new: str | None = None


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").lower()


def target_suffix_for_path(path: str) -> str | None:
    p = normalize_path(path)
    for suffix in TARGET_SUFFIXES:
        if suffix in p:
            return suffix
    return None


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


def extract_events_from_obj(
    obj: dict[str, Any],
    idx_base: int,
    line_no: int,
    source: str,
) -> list[Event]:
    events: list[Event] = []
    idx = idx_base

    for d in iter_dicts(obj):
        if not isinstance(d, dict):
            continue

        tool_name = d.get("name")
        tool_type = d.get("type")
        if tool_type != "tool_use":
            continue
        if tool_name not in {"Write", "StrReplace"}:
            continue

        tool_input = d.get("input")
        if not isinstance(tool_input, dict):
            continue

        path = pick_first_str(tool_input, ["path", "file_path", "filepath", "target_file"])
        if not path:
            continue
        suffix = target_suffix_for_path(path)
        if not suffix:
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
                    path=path,
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
                path=path,
                old=old_value,
                new=new_value,
            )
        )
        idx += 1

    return events


def reconstruct(
    events: list[Event],
    *,
    fallback_content: str | None = None,
) -> tuple[str | None, list[str]]:
    if not events:
        return None, ["no matching events found"]

    ordered = sorted(events, key=lambda e: e.idx)
    writes = [e for e in ordered if e.kind == "write"]
    notes: list[str] = []

    if writes:
        last_write = writes[-1]
        content = last_write.content or ""
        replace_start_idx = last_write.idx
    elif fallback_content is not None:
        content = fallback_content
        replace_start_idx = -1
        notes.append("using fallback base content (no Write in transcripts)")
    else:
        return None, ["no Write event found for file"]

    for event in ordered:
        if event.idx <= replace_start_idx:
            continue
        if event.kind != "replace":
            continue
        old = event.old or ""
        new = event.new or ""
        if old in content:
            content = content.replace(old, new, 1)
        else:
            notes.append(
                f"StrReplace old string not found ({event.source}:{event.line_no}, idx {event.idx})"
            )
    return content, notes


def _transcript_files(transcript_root: Path) -> list[Path]:
    files = [p for p in transcript_root.rglob("*.jsonl") if p.is_file()]
    return sorted(files, key=lambda p: (p.stat().st_mtime, str(p).lower()))


def read_events(transcript_root: Path) -> dict[str, list[Event]]:
    by_suffix: dict[str, list[Event]] = {suffix: [] for suffix in TARGET_SUFFIXES}
    idx = 0

    for transcript_file in _transcript_files(transcript_root):
        with transcript_file.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                events = extract_events_from_obj(
                    obj,
                    idx_base=idx,
                    line_no=line_no,
                    source=str(transcript_file),
                )
                if not events:
                    continue
                idx = max(e.idx for e in events) + 1
                for event in events:
                    suffix = target_suffix_for_path(event.path)
                    if suffix:
                        by_suffix[suffix].append(event)

    return by_suffix


def count_tests(content: str) -> int:
    return len(re.findall(r"^\s*def test_", content, flags=re.MULTILINE))


def merge_event_maps(*maps: dict[str, list[Event]]) -> dict[str, list[Event]]:
    merged: dict[str, list[Event]] = {suffix: [] for suffix in TARGET_SUFFIXES}
    for suffix in TARGET_SUFFIXES:
        pooled: list[Event] = []
        for event_map in maps:
            pooled.extend(event_map.get(suffix, []))
        pooled.sort(key=lambda e: (Path(e.source).stat().st_mtime, e.line_no, e.idx))
        for next_idx, event in enumerate(pooled):
            merged[suffix].append(
                Event(
                    idx=next_idx,
                    line_no=event.line_no,
                    source=event.source,
                    kind=event.kind,
                    path=event.path,
                    content=event.content,
                    old=event.old,
                    new=event.new,
                )
            )
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover test files from Cursor transcript JSONL.")
    parser.add_argument(
        "--transcript-root",
        action="append",
        required=True,
        help="Transcript directory root (repeatable).",
    )
    parser.add_argument("--repo-root", required=True, help="Repository root to deploy into.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write files.")
    args = parser.parse_args()

    transcript_roots = [Path(value) for value in args.transcript_root]
    repo_root = Path(args.repo_root)

    event_maps = [read_events(root) for root in transcript_roots]
    by_suffix = merge_event_maps(*event_maps)

    print("=== Test Recovery Report ===")
    print("Transcript roots:")
    for root in transcript_roots:
        print(f"- {root}")
    print(f"Repo root: {repo_root}")
    print()

    for suffix in TARGET_SUFFIXES:
        events = by_suffix.get(suffix, [])
        current_path = repo_root / RECOVERY_RELATIVE_PATHS[suffix]
        fallback = current_path.read_text(encoding="utf-8") if current_path.exists() else None
        content, notes = reconstruct(events, fallback_content=fallback)
        current_content = fallback or ""
        current_tests = count_tests(current_content)
        current_lines = len(current_content.splitlines()) if current_content else 0

        print(f"--- {suffix} ---")
        print(f"Events: {len(events)} (writes={sum(1 for e in events if e.kind == 'write')}, replaces={sum(1 for e in events if e.kind == 'replace')})")

        if content is None:
            print(f"Recovery: FAILED ({'; '.join(notes)})")
            print(f"Current: {current_tests} tests, {current_lines} lines")
            print()
            continue

        recovered_tests = count_tests(content)
        recovered_lines = len(content.splitlines())
        print(f"Recovered: {recovered_tests} tests, {recovered_lines} lines")
        print(f"Current: {current_tests} tests, {current_lines} lines")

        if notes:
            for note in notes:
                print(f"  note: {note}")

        deploy = recovered_tests > current_tests or (
            recovered_tests == current_tests and recovered_lines > current_lines
        )
        if deploy:
            if args.dry_run:
                print("Action: WOULD DEPLOY (more tests/lines in transcript)")
            else:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.write_text(content, encoding="utf-8")
                print(f"Action: DEPLOYED -> {current_path}")
        else:
            print("Action: SKIP (current is same or better)")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
