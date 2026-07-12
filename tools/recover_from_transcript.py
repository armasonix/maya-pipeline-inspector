from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TARGET_SUFFIXES = [
    "cerebro/adapter.py",
    "test_cerebro_adapter.py",
    "ftrack/verify.py",
    "test_ftrack_verify.py",
    "ftrack/client.py",
]

RECOVERY_RELATIVE_PATHS = {
    "cerebro/adapter.py": Path("src/shader_health/integrations/cerebro/adapter.py"),
    "test_cerebro_adapter.py": Path("tests/unit/test_cerebro_adapter.py"),
    "ftrack/verify.py": Path("src/shader_health/integrations/ftrack/verify.py"),
    "test_ftrack_verify.py": Path("tests/unit/test_ftrack_verify.py"),
    "ftrack/client.py": Path("src/shader_health/integrations/ftrack/client.py"),
}


@dataclass
class Event:
    idx: int
    line_no: int
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


def extract_events_from_obj(obj: dict[str, Any], idx_base: int, line_no: int) -> list[Event]:
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
            events.append(Event(idx=idx, line_no=line_no, kind="write", path=path, content=content))
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
                kind="replace",
                path=path,
                old=old_value,
                new=new_value,
            )
        )
        idx += 1

    return events


def reconstruct(events: list[Event]) -> tuple[str | None, list[str]]:
    if not events:
        return None, ["no matching events found"]

    ordered = sorted(events, key=lambda e: e.idx)
    writes = [e for e in ordered if e.kind == "write"]
    if not writes:
        return None, ["no Write event found for file"]

    last_write = writes[-1]
    content = last_write.content or ""
    notes: list[str] = []

    for event in ordered:
        if event.idx <= last_write.idx:
            continue
        if event.kind != "replace":
            continue
        old = event.old or ""
        new = event.new or ""
        if old in content:
            content = content.replace(old, new, 1)
        else:
            notes.append(
                f"StrReplace old string not found (line {event.line_no}, idx {event.idx})"
            )
    return content, notes


def _transcript_files(transcript_path: Path) -> list[Path]:
    root = transcript_path.parent
    files = [p for p in root.rglob("*.jsonl") if p.is_file()]
    # Process by modification time to approximate chronological event order.
    return sorted(files, key=lambda p: (p.stat().st_mtime, str(p).lower()))


def read_events(transcript_path: Path) -> dict[str, list[Event]]:
    by_suffix: dict[str, list[Event]] = {suffix: [] for suffix in TARGET_SUFFIXES}
    idx = 0

    for transcript_file in _transcript_files(transcript_path):
        with transcript_file.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                events = extract_events_from_obj(obj, idx_base=idx, line_no=line_no)
                if not events:
                    continue
                idx = max(e.idx for e in events) + 1
                for event in events:
                    suffix = target_suffix_for_path(event.path)
                    if suffix:
                        by_suffix[suffix].append(event)

    return by_suffix


def find_class_mentions(transcript_root: Path, class_name: str) -> list[Path]:
    found: list[Path] = []
    for candidate in transcript_root.rglob("*.jsonl"):
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if class_name in text:
            found.append(candidate)
    return sorted(found)


def write_recovered(output_root: Path, suffix: str, content: str) -> Path:
    relative_path = RECOVERY_RELATIVE_PATHS[suffix]
    out_path = output_root / relative_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover file contents from Cursor transcript JSONL.")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSONL.")
    parser.add_argument("--output-root", required=True, help="Recovery output root directory.")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    output_root = Path(args.output_root)

    by_suffix = read_events(transcript_path)

    primary = [
        "cerebro/adapter.py",
        "test_cerebro_adapter.py",
        "ftrack/verify.py",
        "test_ftrack_verify.py",
    ]
    recovered: dict[str, tuple[Path, int, list[str]]] = {}
    failures: dict[str, str] = {}

    cumulative_lines = 0
    for suffix in primary:
        content, notes = reconstruct(by_suffix.get(suffix, []))
        if content is None:
            failures[suffix] = "; ".join(notes)
            continue
        path = write_recovered(output_root, suffix, content)
        line_count = len(content.splitlines())
        cumulative_lines += line_count
        recovered[suffix] = (path, line_count, notes)

    # Recover ftrack/client.py only when primary cumulative line count exceeds 300.
    client_suffix = "ftrack/client.py"
    if cumulative_lines > 300:
        content, notes = reconstruct(by_suffix.get(client_suffix, []))
        if content is None:
            failures[client_suffix] = "; ".join(notes)
        else:
            path = write_recovered(output_root, client_suffix, content)
            recovered[client_suffix] = (path, len(content.splitlines()), notes)

    transcript_root = transcript_path.parent
    class_hits = find_class_mentions(transcript_root, "PycerebroHttpDatabaseAdapter")

    print("=== Recovery Report ===")
    print(f"Transcript: {transcript_path}")
    print(f"Output root: {output_root}")
    print()
    if recovered:
        print("Recovered files:")
        for suffix, (path, lines, notes) in recovered.items():
            print(f"- {suffix}: {lines} lines -> {path}")
            if notes:
                for note in notes:
                    print(f"  note: {note}")
    else:
        print("Recovered files: none")

    print()
    if failures:
        print("Failures:")
        for suffix, reason in failures.items():
            print(f"- {suffix}: {reason}")
    else:
        print("Failures: none")

    print()
    print(f"Primary cumulative lines: {cumulative_lines}")
    print()
    print("Subagent transcript class search:")
    if class_hits:
        for hit in class_hits:
            print(f"- found in: {hit}")
    else:
        print("- no matches")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
