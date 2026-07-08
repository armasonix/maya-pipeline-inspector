"""Studio-wide plugin settings loaded from JSON or the Maya settings UI."""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from shader_health.core.rule_loader import RuleOverride

STUDIO_CONFIG_SCHEMA_VERSION = "1.0"
STUDIO_CONFIG_ENV_VAR = "SHADER_HEALTH_STUDIO_CONFIG"
STUDIO_CONFIG_FILENAME = "shader_health_studio.json"
DEFAULT_DEADLINE_WEB_SERVICE_PORT = 8081
DEFAULT_DEADLINE_PROFILE_ID = "deadline_critical"
DEFAULT_DEADLINE_TIMEOUT_SECONDS = 30.0
DEFAULT_DEADLINE_API_URL = "http://localhost:8081"

TX_DERIVATIVE_RULE_IDS = (
    "common.texture.optimized.exists",
    "common.texture.optimized.fresh",
    "common.texture.optimized.udim_tx.missing",
)


@dataclass(frozen=True)
class PipelineSettings:
    """Pipeline policy toggles controlled by studio configuration."""

    require_tx_derivatives: bool = True

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> PipelineSettings:
        if not data:
            return cls()
        value = data.get("require_tx_derivatives", True)
        return cls(require_tx_derivatives=bool(value))

    def to_dict(self) -> dict[str, Any]:
        return {"require_tx_derivatives": self.require_tx_derivatives}


@dataclass(frozen=True)
class DeadlineConnectorSettings:
    """Thinkbox Deadline connector settings stored in the studio config."""

    enabled: bool = False
    web_service_host: str = "localhost"
    web_service_port: int = DEFAULT_DEADLINE_WEB_SERVICE_PORT
    timeout_seconds: float = DEFAULT_DEADLINE_TIMEOUT_SECONDS
    profile_id: str = DEFAULT_DEADLINE_PROFILE_ID
    profile_path: str = ""
    mayapy: str = "mayapy"
    repo_root: str = ""
    queue: str = ""
    pool: str = ""
    group: str = ""
    user_name: str = ""

    @property
    def api_url(self) -> str:
        host = self.web_service_host.strip() or "localhost"
        if host.startswith("http://") or host.startswith("https://"):
            return host
        return f"http://{host}:{int(self.web_service_port)}"

    def to_deadline_config(self) -> Any:
        """Convert connector settings into a Deadline runtime config object."""

        from shader_health.integrations.deadline.config import DeadlineConfig

        return DeadlineConfig(
            api_url=self.api_url,
            timeout_seconds=float(self.timeout_seconds),
            profile_id=self.profile_id.strip() or DEFAULT_DEADLINE_PROFILE_ID,
            profile_path=_optional_path(self.profile_path),
            mayapy=self.mayapy.strip() or "mayapy",
            repo_root=_optional_path(self.repo_root),
            queue=_optional_str(self.queue),
            pool=_optional_str(self.pool),
            group=_optional_str(self.group),
            user_name=_optional_str(self.user_name),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "web_service_host": self.web_service_host,
            "web_service_port": int(self.web_service_port),
            "timeout_seconds": float(self.timeout_seconds),
            "profile_id": self.profile_id,
            "profile_path": self.profile_path,
            "mayapy": self.mayapy,
            "repo_root": self.repo_root,
            "queue": self.queue,
            "pool": self.pool,
            "group": self.group,
            "user_name": self.user_name,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> DeadlineConnectorSettings:
        if not data:
            return cls()
        host = str(data.get("web_service_host", "") or "")
        port = data.get("web_service_port")
        if not host and data.get("api_url"):
            host, port = _parse_api_url(str(data["api_url"]))
        return cls(
            enabled=bool(data.get("enabled", False)),
            web_service_host=host or "localhost",
            web_service_port=int(port or DEFAULT_DEADLINE_WEB_SERVICE_PORT),
            timeout_seconds=float(data.get("timeout_seconds", DEFAULT_DEADLINE_TIMEOUT_SECONDS)),
            profile_id=str(
                data.get("profile_id", DEFAULT_DEADLINE_PROFILE_ID) or DEFAULT_DEADLINE_PROFILE_ID
            ),
            profile_path=str(data.get("profile_path", "") or ""),
            mayapy=str(data.get("mayapy", "mayapy") or "mayapy"),
            repo_root=str(data.get("repo_root", "") or ""),
            queue=str(data.get("queue", "") or ""),
            pool=str(data.get("pool", "") or ""),
            group=str(data.get("group", "") or ""),
            user_name=str(data.get("user_name", "") or ""),
        )

    @classmethod
    def from_deadline_config(
        cls,
        config: Any,
        *,
        enabled: bool = True,
    ) -> DeadlineConnectorSettings:
        host, port = _parse_api_url(config.api_url)
        return cls(
            enabled=enabled,
            web_service_host=host,
            web_service_port=port,
            timeout_seconds=float(config.timeout_seconds),
            profile_id=config.profile_id,
            profile_path=str(config.profile_path) if config.profile_path else "",
            mayapy=config.mayapy,
            repo_root=str(config.repo_root) if config.repo_root else "",
            queue=config.queue or "",
            pool=config.pool or "",
            group=config.group or "",
            user_name=config.user_name or "",
        )


@dataclass(frozen=True)
class ConnectorSettings:
    """Third-party integration settings grouped by connector."""

    deadline: DeadlineConnectorSettings = DeadlineConnectorSettings()

    def to_dict(self) -> dict[str, Any]:
        return {"deadline": self.deadline.to_dict()}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> ConnectorSettings:
        if not data:
            return cls()
        deadline_raw = data.get("deadline")
        deadline = (
            DeadlineConnectorSettings.from_mapping(deadline_raw)
            if isinstance(deadline_raw, Mapping)
            else DeadlineConnectorSettings()
        )
        return cls(deadline=deadline)


@dataclass(frozen=True)
class StudioConfig:
    """Persistent studio settings for Shader Health Inspector."""

    schema_version: str = STUDIO_CONFIG_SCHEMA_VERSION
    studio_name: str = ""
    pipeline: PipelineSettings = PipelineSettings()
    connectors: ConnectorSettings = ConnectorSettings()
    config_path: Optional[Path] = None

    def with_updates(
        self,
        *,
        studio_name: Optional[str] = None,
        pipeline: Optional[PipelineSettings] = None,
        connectors: Optional[ConnectorSettings] = None,
        config_path: Optional[Path] = None,
    ) -> StudioConfig:
        return replace(
            self,
            studio_name=self.studio_name if studio_name is None else studio_name,
            pipeline=self.pipeline if pipeline is None else pipeline,
            connectors=self.connectors if connectors is None else connectors,
            config_path=self.config_path if config_path is None else config_path,
        )

    def rule_overrides(self) -> dict[str, RuleOverride]:
        """Return profile rule overrides implied by studio pipeline settings."""

        if self.pipeline.require_tx_derivatives:
            return {}
        return {
            rule_id: RuleOverride(rule_id=rule_id, enabled=False)
            for rule_id in TX_DERIVATIVE_RULE_IDS
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "studio_name": self.studio_name,
            "pipeline": self.pipeline.to_dict(),
            "connectors": self.connectors.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, config_path: Path | None = None) -> StudioConfig:
        schema_version = str(data.get("schema_version", STUDIO_CONFIG_SCHEMA_VERSION))
        studio_name = str(data.get("studio_name", "") or "")
        pipeline_raw = data.get("pipeline")
        pipeline = (
            PipelineSettings.from_mapping(pipeline_raw)
            if isinstance(pipeline_raw, Mapping)
            else PipelineSettings()
        )
        connectors_raw = data.get("connectors")
        connectors = (
            ConnectorSettings.from_mapping(connectors_raw)
            if isinstance(connectors_raw, Mapping)
            else ConnectorSettings()
        )
        return cls(
            schema_version=schema_version,
            studio_name=studio_name,
            pipeline=pipeline,
            connectors=connectors,
            config_path=config_path,
        )

    @classmethod
    def default(cls) -> StudioConfig:
        discovered = discover_studio_config_path()
        if discovered is None:
            return cls()
        return load_studio_config(discovered)


def resolve_deadline_config(config: StudioConfig | None) -> Any:
    """Return Deadline runtime config from studio settings, env, or disabled state."""

    from shader_health.integrations.deadline.config import DeadlineConfig

    if config is None:
        return DeadlineConfig.from_env()
    deadline = config.connectors.deadline
    if not deadline.enabled:
        return None
    return deadline.to_deadline_config()


def _parse_api_url(api_url: str) -> tuple[str, int]:
    normalized = api_url.strip() or DEFAULT_DEADLINE_API_URL
    if "://" not in normalized:
        normalized = f"http://{normalized}"
    parsed = urlparse(normalized)
    host = parsed.hostname or "localhost"
    port = parsed.port or DEFAULT_DEADLINE_WEB_SERVICE_PORT
    return host, port


def _optional_str(value: str) -> str | None:
    text = value.strip()
    return text or None


def _optional_path(value: str) -> Path | None:
    text = _optional_str(value)
    return Path(text) if text else None


def discover_studio_config_path() -> Path | None:
    """Return the first discovered studio config path, if any."""

    env_path = os.environ.get(STUDIO_CONFIG_ENV_VAR, "").strip()
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate

    candidates = (
        Path.home() / ".shader_health" / STUDIO_CONFIG_FILENAME,
        Path.home() / STUDIO_CONFIG_FILENAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_studio_config(path: Path) -> StudioConfig:
    """Load studio settings from a JSON file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Studio config must be a JSON object: {path}")
    return StudioConfig.from_dict(payload, config_path=path.resolve())


def save_studio_config(path: Path, config: StudioConfig) -> Path:
    """Write studio settings to a JSON file."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.to_dict()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def merge_studio_rule_overrides(
    profile_overrides: Mapping[str, RuleOverride],
    studio_config: StudioConfig | None,
) -> dict[str, RuleOverride]:
    """Merge studio pipeline overrides on top of a composed workflow profile."""

    merged = dict(profile_overrides)
    if studio_config is None:
        return merged
    merged.update(studio_config.rule_overrides())
    return merged
