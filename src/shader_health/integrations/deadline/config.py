"""Deadline 10 on-prem configuration for Shader Health farm integration."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from shader_health.maya.validation_pipeline import packaged_profile_path

DEFAULT_PROFILE_ID = "deadline_critical"
DEFAULT_API_URL = "http://localhost:8081"
DEFAULT_TIMEOUT_SECONDS = 30.0

_ENV_API_URL = "SHADER_HEALTH_DEADLINE_API_URL"
_ENV_TIMEOUT = "SHADER_HEALTH_DEADLINE_TIMEOUT"
_ENV_PROFILE_ID = "SHADER_HEALTH_DEADLINE_PROFILE_ID"
_ENV_PROFILE_PATH = "SHADER_HEALTH_DEADLINE_PROFILE_PATH"
_ENV_MAYAPY = "SHADER_HEALTH_DEADLINE_MAYAPY"
_ENV_REPO_ROOT = "SHADER_HEALTH_DEADLINE_REPO_ROOT"
_ENV_QUEUE = "SHADER_HEALTH_DEADLINE_QUEUE"
_ENV_POOL = "SHADER_HEALTH_DEADLINE_POOL"
_ENV_GROUP = "SHADER_HEALTH_DEADLINE_GROUP"
_ENV_USER_NAME = "SHADER_HEALTH_DEADLINE_USER_NAME"

@dataclass(frozen=True)
class DeadlineConfig:
    """Connection and validation defaults for Deadline 10 Web Service."""

    api_url: str = DEFAULT_API_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    profile_id: str = DEFAULT_PROFILE_ID
    profile_path: Path | None = None
    mayapy: str = "mayapy"
    repo_root: Path | None = None
    queue: str | None = None
    pool: str | None = None
    group: str | None = None
    user_name: str | None = None

    def resolved_profile_path(self) -> Path:
        """Return the profile JSON path used by preflight validation."""

        if self.profile_path is not None:
            return self.profile_path
        return packaged_profile_path(self.profile_id)

    def with_overrides(self, **kwargs: Any) -> DeadlineConfig:
        """Return a copy with selected fields replaced."""

        return replace(self, **kwargs)

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> DeadlineConfig:
        """Load config from ``SHADER_HEALTH_DEADLINE_*`` environment variables."""

        values = os.environ if environ is None else environ
        profile_path = _optional_path(values.get(_ENV_PROFILE_PATH))
        repo_root = _optional_path(values.get(_ENV_REPO_ROOT))
        return cls(
            api_url=values.get(_ENV_API_URL, DEFAULT_API_URL),
            timeout_seconds=_optional_float(values.get(_ENV_TIMEOUT), DEFAULT_TIMEOUT_SECONDS),
            profile_id=values.get(_ENV_PROFILE_ID, DEFAULT_PROFILE_ID),
            profile_path=profile_path,
            mayapy=values.get(_ENV_MAYAPY, "mayapy"),
            repo_root=repo_root,
            queue=_optional_str(values.get(_ENV_QUEUE)),
            pool=_optional_str(values.get(_ENV_POOL)),
            group=_optional_str(values.get(_ENV_GROUP)),
            user_name=_optional_str(values.get(_ENV_USER_NAME)),
        )

    @classmethod
    def from_json(cls, path: Path) -> DeadlineConfig:
        """Load config from a studio JSON file."""

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Deadline config must be a JSON object: {path}")
        profile_path = _optional_path(payload.get("profile_path"))
        repo_root = _optional_path(payload.get("repo_root"))
        return cls(
            api_url=str(payload.get("api_url", DEFAULT_API_URL)),
            timeout_seconds=_optional_float(
                payload.get("timeout_seconds"),
                DEFAULT_TIMEOUT_SECONDS,
            ),
            profile_id=str(payload.get("profile_id", DEFAULT_PROFILE_ID)),
            profile_path=profile_path,
            mayapy=str(payload.get("mayapy", "mayapy")),
            repo_root=repo_root,
            queue=_optional_str(payload.get("queue")),
            pool=_optional_str(payload.get("pool")),
            group=_optional_str(payload.get("group")),
            user_name=_optional_str(payload.get("user_name")),
        )

def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

def _optional_path(value: Any) -> Path | None:
    text = _optional_str(value)
    return Path(text) if text else None

def _optional_float(value: Any, default: float) -> float:
    if value is None:
        return default
    return float(value)
