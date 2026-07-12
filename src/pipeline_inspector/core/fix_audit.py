"""Fix apply audit sidecar support."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

FIX_AUDIT_SCHEMA_VERSION = "1.0"
JsonDict = dict[str, Any]

class ApplyFixReportLike(Protocol):
    undo_chunk_name: str
    total: int
    applied_count: int
    blocked_count: int
    failed_count: int

    @property
    def records(self) -> Iterable[Any]: ...

@dataclass(frozen=True)
class FixAuditSession:
    applied_at_utc: str
    scene_path: str
    profile_id: str
    undo_chunk_name: str
    total: int
    applied_count: int
    blocked_count: int
    failed_count: int
    records: tuple[JsonDict, ...]

    def to_dict(self) -> JsonDict:
        return {
            "applied_at_utc": self.applied_at_utc,
            "scene_path": self.scene_path,
            "profile_id": self.profile_id,
            "undo_chunk_name": self.undo_chunk_name,
            "total": self.total,
            "applied_count": self.applied_count,
            "blocked_count": self.blocked_count,
            "failed_count": self.failed_count,
            "records": list(self.records),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FixAuditSession:
        raw_records = data.get("records", [])
        if not isinstance(raw_records, list):
            raise ValueError("fix audit session records must be a list")
        return cls(
            applied_at_utc=str(data["applied_at_utc"]),
            scene_path=str(data["scene_path"]),
            profile_id=str(data["profile_id"]),
            undo_chunk_name=str(data["undo_chunk_name"]),
            total=int(data["total"]),
            applied_count=int(data["applied_count"]),
            blocked_count=int(data["blocked_count"]),
            failed_count=int(data["failed_count"]),
            records=tuple(
                dict(item)
                for item in raw_records
                if isinstance(item, Mapping)
            ),
        )

@dataclass(frozen=True)
class FixAuditSidecar:
    scene_path: str
    sessions: tuple[FixAuditSession, ...] = ()

    def to_dict(self) -> JsonDict:
        return {
            "fix_audit_schema_version": FIX_AUDIT_SCHEMA_VERSION,
            "scene_path": self.scene_path,
            "sessions": [session.to_dict() for session in self.sessions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FixAuditSidecar:
        raw = data.get("sessions", [])
        if not isinstance(raw, list):
            raise ValueError("fix audit sidecar sessions must be a list")
        return cls(
            scene_path=str(data.get("scene_path", "")),
            sessions=tuple(
                FixAuditSession.from_dict(item)
                for item in raw
                if isinstance(item, Mapping)
            ),
        )

def build_fix_audit_session(
    *,
    scene_path: str,
    profile_id: str,
    apply_report: ApplyFixReportLike,
    applied_at_utc: Optional[str] = None,
) -> FixAuditSession:
    """Build a deterministic audit session payload from an apply report."""

    records = tuple(
        sorted(
            (_record_to_dict(record) for record in apply_report.records),
            key=_record_sort_key,
        )
    )
    return FixAuditSession(
        applied_at_utc=applied_at_utc or _utc_now(),
        scene_path=scene_path,
        profile_id=profile_id,
        undo_chunk_name=apply_report.undo_chunk_name,
        total=apply_report.total,
        applied_count=apply_report.applied_count,
        blocked_count=apply_report.blocked_count,
        failed_count=apply_report.failed_count,
        records=records,
    )

def load_fix_audit_sidecar(path: str | Path) -> FixAuditSidecar:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("fix audit sidecar root must be an object")
    return FixAuditSidecar.from_dict(data)

def write_fix_audit_sidecar(path: str | Path, sidecar: FixAuditSidecar) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(sidecar.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out

def append_fix_audit_session(
    path: str | Path,
    session: FixAuditSession,
) -> Path:
    """Append a session to the scene fix audit sidecar."""

    sidecar_path = Path(path)
    if sidecar_path.is_file():
        sidecar = load_fix_audit_sidecar(sidecar_path)
        scene_path = sidecar.scene_path or session.scene_path
    else:
        sidecar = FixAuditSidecar(scene_path=session.scene_path, sessions=())
        scene_path = session.scene_path

    sessions = _sorted_sessions((*sidecar.sessions, session))
    updated = FixAuditSidecar(scene_path=scene_path, sessions=sessions)
    return write_fix_audit_sidecar(sidecar_path, updated)

def _record_to_dict(record: Any) -> JsonDict:
    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    if isinstance(record, Mapping):
        return dict(record)
    raise TypeError("fix audit record must provide to_dict() or be a mapping")

def _record_sort_key(record: JsonDict) -> tuple[str, str, str]:
    return (
        str(record.get("fix_id", "")),
        str(record.get("target_node", "")),
        str(record.get("target_attr", "")),
    )

def _sorted_sessions(
    sessions: Iterable[FixAuditSession],
) -> tuple[FixAuditSession, ...]:
    return tuple(
        sorted(
            sessions,
            key=lambda session: (
                session.applied_at_utc,
                session.profile_id,
                session.undo_chunk_name,
            ),
        )
    )

def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
