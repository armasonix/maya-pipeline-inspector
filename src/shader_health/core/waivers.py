"""Waiver sidecar support."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from shader_health.core.rule_schema import RuleResult

WAIVER_SCHEMA_VERSION = "1.0"
WAIVED_STATUS = "waived"
JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WaiverRecord:
    id: str
    rule_id: str
    target_kind: str
    target_id: str
    reason: str
    approved_by: str
    created_at_utc: str
    expires_at_utc: str
    target_node: Optional[str] = None
    target_material: Optional[str] = None

    def matches(self, result: RuleResult) -> bool:
        return (
            self.rule_id == result.rule_id
            and self.target_kind == result.target_kind
            and self.target_id == result.target_id
            and (self.target_node is None or self.target_node == result.node)
            and (self.target_material is None or self.target_material == result.material)
        )

    def expired(self, now_utc: Optional[str] = None) -> bool:
        if not self.expires_at_utc:
            return False
        now = _parse_utc(now_utc) if now_utc else datetime.now(timezone.utc)
        return _parse_utc(self.expires_at_utc) <= now

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "target_node": self.target_node,
            "target_material": self.target_material,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "created_at_utc": self.created_at_utc,
            "expires_at_utc": self.expires_at_utc,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WaiverRecord:
        return cls(
            id=str(data.get("id", "")),
            rule_id=str(data.get("rule_id", "")),
            target_kind=str(data.get("target_kind", "")),
            target_id=str(data.get("target_id", "")),
            target_node=_optional(data.get("target_node")),
            target_material=_optional(data.get("target_material")),
            reason=str(data.get("reason", "")),
            approved_by=str(data.get("approved_by", "")),
            created_at_utc=str(data.get("created_at_utc", "")),
            expires_at_utc=str(data.get("expires_at_utc", "")),
        )


@dataclass(frozen=True)
class WaiverSidecar:
    waivers: tuple[WaiverRecord, ...] = ()
    schema_version: str = WAIVER_SCHEMA_VERSION

    def active_for(
        self,
        result: RuleResult,
        now_utc: Optional[str] = None,
    ) -> Optional[WaiverRecord]:
        for waiver in self.waivers:
            if waiver.matches(result) and not waiver.expired(now_utc):
                return waiver
        return None

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "waivers": [waiver.to_dict() for waiver in self.waivers],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WaiverSidecar:
        raw = data.get("waivers", [])
        if not isinstance(raw, list):
            raise ValueError("waivers must be a list")
        return cls(
            schema_version=str(data.get("schema_version", WAIVER_SCHEMA_VERSION)),
            waivers=tuple(
                WaiverRecord.from_dict(item)
                for item in raw
                if isinstance(item, Mapping)
            ),
        )


def create_waiver_from_result(
    result: RuleResult,
    *,
    reason: str,
    approved_by: str,
    created_at_utc: str,
    expires_at_utc: str,
) -> WaiverRecord:
    waiver_id = f"waiver:{result.rule_id}:{result.target_kind}:{result.target_id}"
    return WaiverRecord(
        id=waiver_id,
        rule_id=result.rule_id,
        target_kind=result.target_kind,
        target_id=result.target_id,
        target_node=result.node,
        target_material=result.material,
        reason=reason,
        approved_by=approved_by,
        created_at_utc=created_at_utc,
        expires_at_utc=expires_at_utc,
    )


def apply_waivers(
    results: Iterable[RuleResult],
    sidecar: WaiverSidecar,
    *,
    now_utc: Optional[str] = None,
) -> tuple[RuleResult, ...]:
    resolved: list[RuleResult] = []
    for result in results:
        waiver = sidecar.active_for(result, now_utc)
        if result.status == "failed" and waiver is not None:
            resolved.append(_waive(result, waiver))
        else:
            resolved.append(result)
    return tuple(resolved)


def revoke_waiver(sidecar: WaiverSidecar, waiver_id: str) -> WaiverSidecar:
    """Return a sidecar copy with one waiver removed by id."""

    remaining = tuple(waiver for waiver in sidecar.waivers if waiver.id != waiver_id)
    if len(remaining) == len(sidecar.waivers):
        raise ValueError(f"Unknown waiver id: {waiver_id}")
    return WaiverSidecar(
        waivers=remaining,
        schema_version=sidecar.schema_version,
    )


def waiver_status_label(waiver: WaiverRecord, *, now_utc: Optional[str] = None) -> str:
    """Return a display status for waiver manager UI."""

    return "expired" if waiver.expired(now_utc) else "active"


def load_waiver_sidecar_optional(path: Optional[str | Path]) -> WaiverSidecar:
    """Load a waiver sidecar when present, otherwise return an empty sidecar."""

    if path is None:
        return WaiverSidecar()
    sidecar_path = Path(path)
    if not sidecar_path.is_file():
        return WaiverSidecar()
    return load_waiver_sidecar(sidecar_path)


def load_waiver_sidecar(path: str | Path) -> WaiverSidecar:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("waiver sidecar root must be an object")
    return WaiverSidecar.from_dict(data)


def write_waiver_sidecar(path: str | Path, sidecar: WaiverSidecar) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(sidecar.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out


def _waive(result: RuleResult, waiver: WaiverRecord) -> RuleResult:
    evidence = dict(result.evidence)
    evidence["waiver"] = waiver.to_dict()
    return replace(
        result,
        status=WAIVED_STATUS,
        block_publish=False,
        block_deadline=False,
        auto_fix_available=False,
        evidence=evidence,
    )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional(value: Any) -> Optional[str]:
    return None if value is None or str(value) == "" else str(value)
