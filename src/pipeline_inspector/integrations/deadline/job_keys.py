"""Shot and render-pass key extraction from Deadline job metadata."""
from __future__ import annotations

import re
from typing import Any

from pipeline_inspector.integrations.deadline.job_payload import job_name_from_payload

_DEFAULT_SHOT_KEY_PATTERN = re.compile(
    r"(?P<shot_key>[A-Za-z0-9]+_(?:seq|SEQ)\d+_(?:sh|SH)\d+)",
    re.IGNORECASE,
)

_PASS_LABEL_TOKENS: dict[str, tuple[str, ...]] = {
    "beauty": ("beauty", "master", "rgb", "beauty_pass", "beautypass"),
    "matte": ("matte", "holdout", "mask", "matte_pass", "mattepass"),
}


def shot_key_from_job(
    payload: dict[str, Any],
    *,
    pattern: re.Pattern[str] | None = None,
) -> str:
    """Return a normalized shot key when job metadata matches studio naming."""

    compiled = pattern or _DEFAULT_SHOT_KEY_PATTERN
    candidates = _job_text_candidates(payload)
    for candidate in candidates:
        match = compiled.search(candidate)
        if match:
            return str(match.group("shot_key")).lower()
    return ""


def pass_label_from_job(payload: dict[str, Any]) -> str:
    """Classify a render pass from job naming conventions."""

    haystack = " ".join(_job_text_candidates(payload)).casefold()
    for label, tokens in _PASS_LABEL_TOKENS.items():
        if any(token in haystack for token in tokens):
            return label
    return "other"


def scene_path_hint_from_job(payload: dict[str, Any]) -> str:
    """Return a scene path hint when the job name or ExtraInfo carries one."""

    for candidate in _job_text_candidates(payload):
        lowered = candidate.casefold()
        for suffix in (".ma", ".mb"):
            index = lowered.find(suffix)
            if index >= 0:
                return candidate[: index + len(suffix)]
    return ""


def _job_text_candidates(payload: dict[str, Any]) -> list[str]:
    job_id = str(payload.get("_id") or payload.get("JobID") or "").strip()
    values = [
        job_name_from_payload(payload, fallback_job_id=job_id),
        str(payload.get("BatchName") or ""),
        str(payload.get("Comment") or ""),
    ]
    props = payload.get("Props")
    if isinstance(props, dict):
        values.extend(
            str(props.get(key) or "")
            for key in ("Name", "BatchName", "Comment", "ExtraInfo0", "ExtraInfo1")
        )
    for key in ("ExtraInfo0", "ExtraInfo1", "ExtraInfo2"):
        values.append(str(payload.get(key) or ""))
    return [value for value in values if value.strip()]
