"""Studio-wide plugin settings loaded from JSON or the Maya settings UI."""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from pipeline_inspector.core.manifest_gate import ManifestGatePolicy
from pipeline_inspector.core.naming_conventions import normalize_naming_templates
from pipeline_inspector.core.render_presets import RenderSettings
from pipeline_inspector.core.rule_loader import RuleOverride
from pipeline_inspector.integrations.notification_triggers import (
    CONNECTOR_NOTIFY_EVENTS,
    NOTIFY_EVENT_BLOCK_DEADLINE,
    NOTIFY_EVENT_BLOCK_PUBLISH,
)

STUDIO_CONFIG_SCHEMA_VERSION = "2.0"
LEGACY_STUDIO_CONFIG_SCHEMA_VERSION = "1.0"
SUPPORTED_STUDIO_CONFIG_SCHEMA_VERSIONS = (
    LEGACY_STUDIO_CONFIG_SCHEMA_VERSION,
    STUDIO_CONFIG_SCHEMA_VERSION,
)
STUDIO_CONFIG_ENV_VAR = "PIPELINE_INSPECTOR_STUDIO_CONFIG"
LEGACY_STUDIO_CONFIG_ENV_VAR = "SHADER_HEALTH_STUDIO_CONFIG"
STUDIO_CONFIG_FILENAME = "pipeline_inspector_studio.json"
LEGACY_STUDIO_CONFIG_FILENAME = "shader_health_studio.json"
LEGACY_STUDIO_CONFIG_DIRNAME = ".shader_health"
DEFAULT_DEADLINE_WEB_SERVICE_PORT = 8081
DEFAULT_DEADLINE_PROFILE_ID = "deadline_critical"
DEFAULT_DEADLINE_TIMEOUT_SECONDS = 30.0
DEFAULT_DEADLINE_API_URL = "http://localhost:8081"

TX_DERIVATIVE_RULE_IDS = (
    "common.texture.optimized.exists",
    "common.texture.optimized.fresh",
    "common.texture.optimized.udim_tx.missing",
)
DEFAULT_WAIVER_EXPIRY_DAYS = 30


@dataclass(frozen=True)
class WaiverDefaultsSettings:
    """Studio defaults applied when artists create waiver sidecar entries."""

    default_approved_by: str = ""
    default_expiry_days: int = DEFAULT_WAIVER_EXPIRY_DAYS
    allow_critical_waivers: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_approved_by": self.default_approved_by,
            "default_expiry_days": int(self.default_expiry_days),
            "allow_critical_waivers": self.allow_critical_waivers,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> WaiverDefaultsSettings:
        if not data:
            return cls()
        approved_by = data.get("default_approved_by")
        if not approved_by:
            approved_by = data.get("approved_by")
        return cls(
            default_approved_by=str(approved_by or ""),
            default_expiry_days=int(data.get("default_expiry_days", DEFAULT_WAIVER_EXPIRY_DAYS)),
            allow_critical_waivers=bool(data.get("allow_critical_waivers", False)),
        )


@dataclass(frozen=True)
class NamingTemplatesSettings:
    """Per-object-type regex naming templates configured by the studio."""

    templates: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.templates)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> NamingTemplatesSettings:
        return cls(templates=normalize_naming_templates(data))


@dataclass(frozen=True)
class PipelineSettings:
    """Pipeline policy toggles controlled by studio configuration."""

    require_tx_derivatives: bool = True
    waiver_defaults: WaiverDefaultsSettings = WaiverDefaultsSettings()
    manifest_gate_defaults: ManifestGatePolicy = ManifestGatePolicy()
    naming_templates: NamingTemplatesSettings = field(default_factory=NamingTemplatesSettings)
    pinned_workflow_profile_ids: tuple[str, ...] = ()
    pinned_asset_class_profile_ids: tuple[str, ...] = ()
    extra_rules_folder: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> PipelineSettings:
        if not data:
            return cls()
        waiver_raw = data.get("waiver_defaults")
        waiver_defaults = (
            WaiverDefaultsSettings.from_mapping(waiver_raw)
            if isinstance(waiver_raw, Mapping)
            else WaiverDefaultsSettings()
        )
        manifest_raw = data.get("manifest_gate_defaults")
        manifest_gate_defaults = ManifestGatePolicy.from_mapping(
            manifest_raw if isinstance(manifest_raw, Mapping) else None
        )
        naming_raw = data.get("naming_templates")
        naming_templates = (
            NamingTemplatesSettings.from_mapping(naming_raw)
            if isinstance(naming_raw, Mapping)
            else NamingTemplatesSettings()
        )
        return cls(
            require_tx_derivatives=bool(data.get("require_tx_derivatives", True)),
            waiver_defaults=waiver_defaults,
            manifest_gate_defaults=manifest_gate_defaults,
            naming_templates=naming_templates,
            pinned_workflow_profile_ids=_profile_ids_from_value(
                data.get("pinned_workflow_profile_ids")
            ),
            pinned_asset_class_profile_ids=_profile_ids_from_value(
                data.get("pinned_asset_class_profile_ids")
            ),
            extra_rules_folder=str(data.get("extra_rules_folder", "") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "require_tx_derivatives": self.require_tx_derivatives,
            "waiver_defaults": self.waiver_defaults.to_dict(),
            "manifest_gate_defaults": {
                "max_new_changes": int(self.manifest_gate_defaults.max_new_changes),
                "max_fingerprint_changes": int(
                    self.manifest_gate_defaults.max_fingerprint_changes
                ),
                "block_on_new_textures": bool(
                    self.manifest_gate_defaults.block_on_new_textures
                ),
            },
            "naming_templates": self.naming_templates.to_dict(),
            "pinned_workflow_profile_ids": list(self.pinned_workflow_profile_ids),
            "pinned_asset_class_profile_ids": list(self.pinned_asset_class_profile_ids),
            "extra_rules_folder": self.extra_rules_folder,
        }


@dataclass(frozen=True)
class StudioEnvironmentSettings:
    """Studio network path roots and variable aliases for path substitution."""

    texture_root: str = ""
    asset_root: str = ""
    cache_root: str = ""
    render_root: str = ""
    variable_aliases: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "texture_root": self.texture_root,
            "asset_root": self.asset_root,
            "cache_root": self.cache_root,
            "render_root": self.render_root,
            "variable_aliases": dict(self.variable_aliases),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> StudioEnvironmentSettings:
        if not data:
            return cls()
        aliases_raw = data.get("variable_aliases")
        aliases: dict[str, str] = {}
        if isinstance(aliases_raw, Mapping):
            aliases = {str(key): str(value) for key, value in aliases_raw.items()}
        return cls(
            texture_root=str(data.get("texture_root", "") or ""),
            asset_root=str(data.get("asset_root", "") or ""),
            cache_root=str(data.get("cache_root", "") or ""),
            render_root=str(data.get("render_root", "") or ""),
            variable_aliases=aliases,
        )


@dataclass(frozen=True)
class StudioUiSettings:
    """Optional studio-level UI defaults deployed with the studio config."""

    documentation_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"documentation_url": self.documentation_url}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> StudioUiSettings:
        if not data:
            return cls()
        return cls(documentation_url=str(data.get("documentation_url", "") or ""))


@dataclass(frozen=True)
class ReadinessSupportContacts:
    """Telegram chat IDs used for machine readiness escalation."""

    sysadmin_telegram_chat_id: str = ""
    support_telegram_chat_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sysadmin_telegram_chat_id": self.sysadmin_telegram_chat_id,
            "support_telegram_chat_id": self.support_telegram_chat_id,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> ReadinessSupportContacts:
        if not data:
            return cls()
        return cls(
            sysadmin_telegram_chat_id=str(data.get("sysadmin_telegram_chat_id", "") or ""),
            support_telegram_chat_id=str(data.get("support_telegram_chat_id", "") or ""),
        )


@dataclass(frozen=True)
class SoftwareVersionRequirement:
    """One installed-software version requirement for machine readiness."""

    product: str
    version: str

    def to_dict(self) -> dict[str, str]:
        return {"product": self.product, "version": self.version}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SoftwareVersionRequirement:
        return cls(
            product=str(data.get("product", "") or "").strip(),
            version=str(data.get("version", "") or "").strip(),
        )


def parse_software_version_requirements(
    raw: object,
) -> tuple[SoftwareVersionRequirement, ...]:
    """Parse readiness software requirements from JSON or UI text."""

    if raw is None:
        return ()
    if isinstance(raw, str):
        return _parse_software_version_text(raw)
    if isinstance(raw, list):
        requirements: list[SoftwareVersionRequirement] = []
        for item in raw:
            if isinstance(item, Mapping):
                requirement = SoftwareVersionRequirement.from_mapping(item)
                if requirement.product and requirement.version:
                    requirements.append(requirement)
            elif isinstance(item, str):
                requirements.extend(_parse_software_version_text(item))
        return tuple(requirements)
    if isinstance(raw, Mapping):
        requirements = []
        for product, version in raw.items():
            product_text = str(product or "").strip()
            if not product_text:
                continue
            if isinstance(version, list):
                for entry in version:
                    version_text = str(entry or "").strip()
                    if version_text:
                        requirements.append(
                            SoftwareVersionRequirement(product_text, version_text)
                        )
            else:
                version_text = str(version or "").strip()
                if version_text:
                    requirements.append(
                        SoftwareVersionRequirement(product_text, version_text)
                    )
        return tuple(requirements)
    return ()


def _parse_software_version_text(text: str) -> tuple[SoftwareVersionRequirement, ...]:
    requirements: list[SoftwareVersionRequirement] = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        entry = line.strip()
        if not entry or "=" not in entry:
            continue
        product, version = entry.split("=", 1)
        product_text = product.strip()
        version_text = version.strip()
        if product_text and version_text:
            requirements.append(SoftwareVersionRequirement(product_text, version_text))
    return tuple(requirements)


@dataclass(frozen=True)
class ReadinessCheckRequirements:
    """Studio-configured machine readiness requirements."""

    maya_plugins: tuple[str, ...] = ()
    mapped_drives: tuple[str, ...] = ()
    env_vars: tuple[str, ...] = ()
    network_paths: tuple[str, ...] = ()
    software_version_requirements: tuple[SoftwareVersionRequirement, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "maya_plugins": list(self.maya_plugins),
            "mapped_drives": list(self.mapped_drives),
            "env_vars": list(self.env_vars),
            "network_paths": list(self.network_paths),
            "software_versions": [
                requirement.to_dict() for requirement in self.software_version_requirements
            ],
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> ReadinessCheckRequirements:
        if not data:
            return cls()
        return cls(
            maya_plugins=_as_str_tuple(data.get("maya_plugins")),
            mapped_drives=_as_str_tuple(data.get("mapped_drives")),
            env_vars=_as_str_tuple(data.get("env_vars")),
            network_paths=_as_str_tuple(data.get("network_paths")),
            software_version_requirements=parse_software_version_requirements(
                data.get("software_versions")
            ),
        )


@dataclass(frozen=True)
class ReadinessSettings:
    """Machine readiness policy and support escalation contacts."""

    checks: ReadinessCheckRequirements = field(default_factory=ReadinessCheckRequirements)
    support: ReadinessSupportContacts = field(default_factory=ReadinessSupportContacts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": self.checks.to_dict(),
            "support": self.support.to_dict(),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> ReadinessSettings:
        if not data:
            return cls()
        checks_raw = data.get("checks")
        support_raw = data.get("support")
        checks = (
            ReadinessCheckRequirements.from_mapping(checks_raw)
            if isinstance(checks_raw, Mapping)
            else ReadinessCheckRequirements()
        )
        support = (
            ReadinessSupportContacts.from_mapping(support_raw)
            if isinstance(support_raw, Mapping)
            else ReadinessSupportContacts()
        )
        return cls(checks=checks, support=support)


@dataclass(frozen=True)
class BugReportSettings:
    """Bug report relay settings controlled by the studio."""

    enabled: bool = False
    relay_url: str = ""
    api_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "relay_url": self.relay_url,
            "api_key": self.api_key,
        }

    def to_bug_report_config(self) -> Any | None:
        """Convert connector settings into a bug report relay runtime config object."""

        from pipeline_inspector.integrations.bug_report.config import (
            BUG_REPORT_MAX_REPORTS_PER_DAY,
            BugReportRelayConfig,
            effective_bug_report_relay_url,
        )

        relay_url = effective_bug_report_relay_url(self.relay_url)
        api_key = self.api_key.strip()
        if not relay_url:
            return None
        return BugReportRelayConfig(
            relay_url=relay_url,
            api_key=api_key,
            max_reports_per_day=BUG_REPORT_MAX_REPORTS_PER_DAY,
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> BugReportSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            relay_url=str(data.get("relay_url", "") or ""),
            api_key=str(data.get("api_key", "") or ""),
        )


@dataclass(frozen=True)
class StudioUpdatesSettings:
    """Studio policy for in-app update checks."""

    allow_check: bool = True
    pinned_version: str = ""
    github_owner: str = ""
    github_repo: str = ""
    github_token: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_check": self.allow_check,
            "pinned_version": self.pinned_version,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "github_token": self.github_token,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> StudioUpdatesSettings:
        if not data:
            return cls()
        return cls(
            allow_check=bool(data.get("allow_check", True)),
            pinned_version=str(data.get("pinned_version", "") or ""),
            github_owner=str(data.get("github_owner", "") or ""),
            github_repo=str(data.get("github_repo", "") or ""),
            github_token=str(data.get("github_token", "") or ""),
        )


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
    allow_draft_submit: bool = True
    allow_production_submit: bool = False

    @property
    def enabled_submit_qualities(self) -> tuple[str, ...]:
        from pipeline_inspector.core.render_presets import (
            RENDER_QUALITY_DRAFT,
            RENDER_QUALITY_PRODUCTION,
        )

        qualities: list[str] = []
        if self.allow_draft_submit:
            qualities.append(RENDER_QUALITY_DRAFT)
        if self.allow_production_submit:
            qualities.append(RENDER_QUALITY_PRODUCTION)
        return tuple(qualities)

    def to_deadline_config_for_quality(self, quality: str) -> Any:
        """Convert connector settings into a Deadline config for a quality tier."""

        _ = quality
        return self.to_deadline_config()

    @property
    def api_url(self) -> str:
        host = self.web_service_host.strip() or "localhost"
        if host.startswith("http://") or host.startswith("https://"):
            return host
        return f"http://{host}:{int(self.web_service_port)}"

    def to_deadline_config(self) -> Any:
        """Convert connector settings into a Deadline runtime config object."""

        from pipeline_inspector.integrations.deadline.config import DeadlineConfig

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
            "allow_draft_submit": self.allow_draft_submit,
            "allow_production_submit": self.allow_production_submit,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> DeadlineConnectorSettings:
        if not data:
            return cls()
        host = str(data.get("web_service_host", "") or "")
        port = data.get("web_service_port")
        if not host and data.get("api_url"):
            host, port = _parse_api_url(str(data["api_url"]))
        allow_draft, allow_production = _normalize_farm_submit_qualities(
            bool(data.get("allow_draft_submit", True)),
            bool(data.get("allow_production_submit", False)),
        )
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
            allow_draft_submit=allow_draft,
            allow_production_submit=allow_production,
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


SLACK_NOTIFY_EVENT_BLOCK_PUBLISH = NOTIFY_EVENT_BLOCK_PUBLISH
SLACK_NOTIFY_EVENT_BLOCK_DEADLINE = NOTIFY_EVENT_BLOCK_DEADLINE
SLACK_NOTIFY_EVENTS = CONNECTOR_NOTIFY_EVENTS


@dataclass(frozen=True)
class NotifyTarget:
    """Per-destination notification routing entry stored in connector settings."""

    role: str = ""
    chat_id: str = ""
    webhook_url: str = ""
    events: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"events": list(self.events)}
        if self.role.strip():
            payload["role"] = self.role
        if self.chat_id.strip():
            payload["chat_id"] = self.chat_id
        if self.webhook_url.strip():
            payload["webhook_url"] = self.webhook_url
        return payload

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> NotifyTarget:
        if not data:
            return cls()
        events_raw = data.get("events")
        events: tuple[str, ...] = ()
        if isinstance(events_raw, (list, tuple)):
            events = tuple(
                str(event).strip()
                for event in events_raw
                if str(event).strip()
            )
        return cls(
            role=str(data.get("role", "") or ""),
            chat_id=str(data.get("chat_id", "") or ""),
            webhook_url=str(data.get("webhook_url", "") or ""),
            events=events,
        )


def _parse_notify_on(data: Mapping[str, Any]) -> tuple[str, ...]:
    notify_raw = data.get("notify_on")
    if not isinstance(notify_raw, (list, tuple)):
        return ()
    return tuple(
        str(event).strip()
        for event in notify_raw
        if str(event).strip()
    )


def _parse_notify_targets(data: Mapping[str, Any]) -> tuple[NotifyTarget, ...]:
    targets_raw = data.get("notify_targets")
    if not isinstance(targets_raw, (list, tuple)):
        return ()
    targets: list[NotifyTarget] = []
    for entry in targets_raw:
        if not isinstance(entry, Mapping):
            continue
        target = NotifyTarget.from_mapping(entry)
        if target.events:
            targets.append(target)
    return tuple(targets)


def _parse_notify_score_below(data: Mapping[str, Any]) -> int | None:
    raw = data.get("notify_score_below")
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


@dataclass(frozen=True)
class SlackConnectorSettings:
    """Slack incoming webhook connector settings stored in the studio config."""

    enabled: bool = False
    publish_webhook_url: str = ""
    deadline_webhook_url: str = ""
    notify_on: tuple[str, ...] = ()
    notify_targets: tuple[NotifyTarget, ...] = ()
    notify_score_below: int | None = None
    include_report_link: bool = True

    def to_slack_config(self) -> Any | None:
        """Convert connector settings into a Slack runtime config object."""

        from pipeline_inspector.integrations.slack.config import SlackConfig

        publish = self.publish_webhook_url.strip()
        deadline = self.deadline_webhook_url.strip()
        if not publish and not deadline:
            return None
        return SlackConfig(
            publish_webhook_url=publish,
            deadline_webhook_url=deadline,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "publish_webhook_url": self.publish_webhook_url,
            "deadline_webhook_url": self.deadline_webhook_url,
            "notify_on": list(self.notify_on),
            "notify_targets": [target.to_dict() for target in self.notify_targets],
            "notify_score_below": self.notify_score_below,
            "include_report_link": self.include_report_link,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> SlackConnectorSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            publish_webhook_url=str(data.get("publish_webhook_url", "") or ""),
            deadline_webhook_url=str(data.get("deadline_webhook_url", "") or ""),
            notify_on=_parse_notify_on(data),
            notify_targets=_parse_notify_targets(data),
            notify_score_below=_parse_notify_score_below(data),
            include_report_link=bool(data.get("include_report_link", True)),
        )


@dataclass(frozen=True)
class FtrackConnectorSettings:
    """Ftrack task tracker connector settings stored in the studio config."""

    enabled: bool = False
    api_url: str = ""
    api_user: str = ""
    api_key: str = ""
    project: str = ""
    note_author_username: str = ""
    task_status_name: str = ""

    def to_ftrack_config(self) -> Any | None:
        """Convert connector settings into an Ftrack runtime config object."""

        from pipeline_inspector.integrations.ftrack.config import (
            DEFAULT_NOTE_AUTHOR_USERNAME,
            DEFAULT_TASK_STATUS_NAME,
            FtrackConfig,
        )

        api_url = self.api_url.strip()
        api_user = self.api_user.strip()
        api_key = self.api_key.strip()
        project = self.project.strip()
        if not api_url or not api_user or not api_key or not project:
            return None
        note_author_username = self.note_author_username.strip() or DEFAULT_NOTE_AUTHOR_USERNAME
        task_status_name = self.task_status_name.strip() or DEFAULT_TASK_STATUS_NAME
        return FtrackConfig(
            api_url=api_url,
            api_user=api_user,
            api_key=api_key,
            project=project,
            note_author_username=note_author_username,
            task_status_name=task_status_name,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "api_url": self.api_url,
            "api_user": self.api_user,
            "api_key": self.api_key,
            "project": self.project,
            "note_author_username": self.note_author_username,
            "task_status_name": self.task_status_name,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> FtrackConnectorSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            api_url=str(data.get("api_url", "") or ""),
            api_user=str(data.get("api_user", "") or ""),
            api_key=str(data.get("api_key", "") or ""),
            project=str(data.get("project", "") or ""),
            note_author_username=str(data.get("note_author_username", "") or ""),
            task_status_name=str(data.get("task_status_name", "") or ""),
        )


@dataclass(frozen=True)
class ShotGridConnectorSettings:
    """ShotGrid task tracker connector settings stored in the studio config."""

    enabled: bool = False
    site_url: str = ""
    script_name: str = ""
    api_key: str = ""
    project: str = ""
    entity_type: str = "Shot"

    def to_shotgrid_config(self) -> Any | None:
        """Convert connector settings into a ShotGrid runtime config object."""

        from pipeline_inspector.integrations.shotgrid.config import ShotGridConfig

        site_url = self.site_url.strip()
        script_name = self.script_name.strip()
        api_key = self.api_key.strip()
        project = self.project.strip()
        entity_type = self.entity_type.strip() or "Shot"
        if not site_url or not script_name or not api_key or not project:
            return None
        return ShotGridConfig(
            site_url=site_url,
            script_name=script_name,
            api_key=api_key,
            project=project,
            entity_type=entity_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "site_url": self.site_url,
            "script_name": self.script_name,
            "api_key": self.api_key,
            "project": self.project,
            "entity_type": self.entity_type,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> ShotGridConnectorSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            site_url=str(data.get("site_url", "") or ""),
            script_name=str(data.get("script_name", "") or ""),
            api_key=str(data.get("api_key", "") or ""),
            project=str(data.get("project", "") or ""),
            entity_type=str(data.get("entity_type", "Shot") or "Shot"),
        )


@dataclass(frozen=True)
class CerebroConnectorSettings:
    """Cerebro task tracker connector settings stored in the studio config."""

    enabled: bool = False
    server_url: str = ""
    api_user: str = ""
    api_password: str = ""
    project: str = ""
    service_tools_path: str = ""
    pause_status_name: str = "Pause"
    set_pause_status_on_publish: bool = True

    def to_cerebro_config(self) -> Any | None:
        """Convert connector settings into a Cerebro runtime config object."""

        from pipeline_inspector.integrations.cerebro.config import CerebroConfig

        server_url = self.server_url.strip()
        api_user = self.api_user.strip()
        api_password = self.api_password.strip()
        project = self.project.strip()
        if not server_url or not api_user or not api_password or not project:
            return None
        return CerebroConfig(
            server_url=server_url,
            api_user=api_user,
            api_password=api_password,
            project=project,
            service_tools_path=self.service_tools_path.strip(),
            pause_status_name=self.pause_status_name.strip() or "Pause",
            set_pause_status_on_publish=self.set_pause_status_on_publish,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "server_url": self.server_url,
            "api_user": self.api_user,
            "api_password": self.api_password,
            "project": self.project,
            "service_tools_path": self.service_tools_path,
            "pause_status_name": self.pause_status_name,
            "set_pause_status_on_publish": self.set_pause_status_on_publish,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> CerebroConnectorSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            server_url=str(data.get("server_url", "") or ""),
            api_user=str(data.get("api_user", "") or ""),
            api_password=str(data.get("api_password", "") or ""),
            project=str(data.get("project", "") or ""),
            service_tools_path=str(data.get("service_tools_path", "") or ""),
            pause_status_name=str(data.get("pause_status_name", "Pause") or "Pause"),
            set_pause_status_on_publish=bool(data.get("set_pause_status_on_publish", True)),
        )


DISCORD_NOTIFY_EVENT_BLOCK_PUBLISH = NOTIFY_EVENT_BLOCK_PUBLISH
DISCORD_NOTIFY_EVENT_BLOCK_DEADLINE = NOTIFY_EVENT_BLOCK_DEADLINE
DISCORD_NOTIFY_EVENTS = CONNECTOR_NOTIFY_EVENTS


@dataclass(frozen=True)
class DiscordConnectorSettings:
    """Discord incoming webhook connector settings stored in the studio config."""

    enabled: bool = False
    webhook_url: str = ""
    notify_on: tuple[str, ...] = ()
    notify_targets: tuple[NotifyTarget, ...] = ()
    notify_score_below: int | None = None

    def to_discord_config(self) -> Any | None:
        """Convert connector settings into a Discord runtime config object."""

        from pipeline_inspector.integrations.discord.config import DiscordConfig

        webhook_url = self.webhook_url.strip()
        if not webhook_url:
            return None
        return DiscordConfig(webhook_url=webhook_url)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "webhook_url": self.webhook_url,
            "notify_on": list(self.notify_on),
            "notify_targets": [target.to_dict() for target in self.notify_targets],
            "notify_score_below": self.notify_score_below,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> DiscordConnectorSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            webhook_url=str(data.get("webhook_url", "") or ""),
            notify_on=_parse_notify_on(data),
            notify_targets=_parse_notify_targets(data),
            notify_score_below=_parse_notify_score_below(data),
        )


TELEGRAM_NOTIFY_EVENT_BLOCK_PUBLISH = NOTIFY_EVENT_BLOCK_PUBLISH
TELEGRAM_NOTIFY_EVENT_BLOCK_DEADLINE = NOTIFY_EVENT_BLOCK_DEADLINE
TELEGRAM_NOTIFY_EVENTS = CONNECTOR_NOTIFY_EVENTS


@dataclass(frozen=True)
class TelegramConnectorSettings:
    """Telegram Bot API connector settings stored in the studio config."""

    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    notify_on: tuple[str, ...] = ()
    notify_targets: tuple[NotifyTarget, ...] = ()
    notify_score_below: int | None = None

    def to_telegram_config(self) -> Any | None:
        """Convert connector settings into a Telegram runtime config object."""

        from pipeline_inspector.integrations.telegram.config import TelegramConfig

        token = self.bot_token.strip()
        chat_id = self.chat_id.strip()
        if not token or not chat_id:
            return None
        return TelegramConfig(bot_token=token, chat_id=chat_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "bot_token": self.bot_token,
            "chat_id": self.chat_id,
            "notify_on": list(self.notify_on),
            "notify_targets": [target.to_dict() for target in self.notify_targets],
            "notify_score_below": self.notify_score_below,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> TelegramConnectorSettings:
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            bot_token=str(data.get("bot_token", "") or ""),
            chat_id=str(data.get("chat_id", "") or ""),
            notify_on=_parse_notify_on(data),
            notify_targets=_parse_notify_targets(data),
            notify_score_below=_parse_notify_score_below(data),
        )


@dataclass(frozen=True)
class ConnectorSettings:
    """Third-party integration settings grouped by connector."""

    deadline: DeadlineConnectorSettings = DeadlineConnectorSettings()
    telegram: TelegramConnectorSettings = TelegramConnectorSettings()
    discord: DiscordConnectorSettings = DiscordConnectorSettings()
    slack: SlackConnectorSettings = SlackConnectorSettings()
    ftrack: FtrackConnectorSettings = FtrackConnectorSettings()
    shotgrid: ShotGridConnectorSettings = ShotGridConnectorSettings()
    cerebro: CerebroConnectorSettings = CerebroConnectorSettings()
    extra: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    _TYPED_CONNECTOR_IDS = frozenset(
        {
            "deadline",
            "telegram",
            "discord",
            "slack",
            "ftrack",
            "shotgrid",
            "cerebro",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "deadline": self.deadline.to_dict(),
            "telegram": self.telegram.to_dict(),
            "discord": self.discord.to_dict(),
            "slack": self.slack.to_dict(),
            "ftrack": self.ftrack.to_dict(),
            "shotgrid": self.shotgrid.to_dict(),
            "cerebro": self.cerebro.to_dict(),
        }
        for connector_id in sorted(self.extra):
            if connector_id in self._TYPED_CONNECTOR_IDS:
                continue
            connector_payload = self.extra[connector_id]
            payload[connector_id] = dict(connector_payload)
        return payload

    def connector_settings(self, connector_id: str) -> Mapping[str, Any] | None:
        """Return raw settings for a connector id, including Deadline."""

        if connector_id == "deadline":
            return self.deadline.to_dict()
        if connector_id == "telegram":
            return self.telegram.to_dict()
        if connector_id == "discord":
            return self.discord.to_dict()
        if connector_id == "slack":
            return self.slack.to_dict()
        if connector_id == "ftrack":
            return self.ftrack.to_dict()
        if connector_id == "shotgrid":
            return self.shotgrid.to_dict()
        if connector_id == "cerebro":
            return self.cerebro.to_dict()
        return self.extra.get(connector_id)

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
        telegram_raw = data.get("telegram")
        telegram = (
            TelegramConnectorSettings.from_mapping(telegram_raw)
            if isinstance(telegram_raw, Mapping)
            else TelegramConnectorSettings()
        )
        discord_raw = data.get("discord")
        discord = (
            DiscordConnectorSettings.from_mapping(discord_raw)
            if isinstance(discord_raw, Mapping)
            else DiscordConnectorSettings()
        )
        slack_raw = data.get("slack")
        slack = (
            SlackConnectorSettings.from_mapping(slack_raw)
            if isinstance(slack_raw, Mapping)
            else SlackConnectorSettings()
        )
        ftrack_raw = data.get("ftrack")
        ftrack = (
            FtrackConnectorSettings.from_mapping(ftrack_raw)
            if isinstance(ftrack_raw, Mapping)
            else FtrackConnectorSettings()
        )
        shotgrid_raw = data.get("shotgrid")
        shotgrid = (
            ShotGridConnectorSettings.from_mapping(shotgrid_raw)
            if isinstance(shotgrid_raw, Mapping)
            else ShotGridConnectorSettings()
        )
        cerebro_raw = data.get("cerebro")
        cerebro = (
            CerebroConnectorSettings.from_mapping(cerebro_raw)
            if isinstance(cerebro_raw, Mapping)
            else CerebroConnectorSettings()
        )
        extra: dict[str, dict[str, Any]] = {}
        for connector_id, connector_raw in data.items():
            if connector_id in ConnectorSettings._TYPED_CONNECTOR_IDS:
                continue
            if not isinstance(connector_raw, Mapping):
                continue
            extra[str(connector_id)] = dict(connector_raw)
        return cls(
            deadline=deadline,
            telegram=telegram,
            discord=discord,
            slack=slack,
            ftrack=ftrack,
            shotgrid=shotgrid,
            cerebro=cerebro,
            extra=extra,
        )


@dataclass(frozen=True)
class SupervisorRoute:
    """Notification targets for reports escalated from a reporter pipeline role."""

    supervisor_label: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    slack_webhook_url: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "supervisor_label": self.supervisor_label,
            "telegram_chat_id": self.telegram_chat_id,
            "discord_webhook_url": self.discord_webhook_url,
            "slack_webhook_url": self.slack_webhook_url,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> SupervisorRoute:
        if not data:
            return cls()
        return cls(
            supervisor_label=str(data.get("supervisor_label", "") or ""),
            telegram_chat_id=str(data.get("telegram_chat_id", "") or ""),
            discord_webhook_url=str(data.get("discord_webhook_url", "") or ""),
            slack_webhook_url=str(data.get("slack_webhook_url", "") or ""),
        )


@dataclass(frozen=True)
class GovernanceSettings:
    """Studio role policy overrides for permission resolution."""

    enforced_role: str = ""
    tracker_role_map: dict[str, str] = field(default_factory=dict)
    capability_denials: dict[str, tuple[str, ...]] = field(default_factory=dict)
    supervisor_routes: dict[str, SupervisorRoute] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enforced_role": self.enforced_role,
            "tracker_role_map": dict(self.tracker_role_map),
            "capability_denials": {
                role: list(capabilities)
                for role, capabilities in self.capability_denials.items()
            },
            "supervisor_routes": {
                role: route.to_dict() for role, route in self.supervisor_routes.items()
            },
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> GovernanceSettings:
        if not data:
            return cls()
        tracker_raw = data.get("tracker_role_map")
        tracker_role_map: dict[str, str] = {}
        if isinstance(tracker_raw, Mapping):
            tracker_role_map = {
                str(key): str(value)
                for key, value in tracker_raw.items()
                if str(key).strip() and str(value).strip()
            }
        denials_raw = data.get("capability_denials")
        capability_denials: dict[str, tuple[str, ...]] = {}
        if isinstance(denials_raw, Mapping):
            for role, capabilities in denials_raw.items():
                if not isinstance(capabilities, list):
                    continue
                normalized = tuple(
                    str(item).strip() for item in capabilities if str(item).strip()
                )
                if normalized:
                    capability_denials[str(role)] = normalized
        routes_raw = data.get("supervisor_routes")
        supervisor_routes: dict[str, SupervisorRoute] = {}
        if isinstance(routes_raw, Mapping):
            for role, route_data in routes_raw.items():
                if not isinstance(route_data, Mapping):
                    continue
                route = SupervisorRoute.from_mapping(route_data)
                if any(
                    (
                        route.supervisor_label.strip(),
                        route.telegram_chat_id.strip(),
                        route.discord_webhook_url.strip(),
                        route.slack_webhook_url.strip(),
                    )
                ):
                    supervisor_routes[str(role)] = route
        return cls(
            enforced_role=str(data.get("enforced_role", "") or ""),
            tracker_role_map=tracker_role_map,
            capability_denials=capability_denials,
            supervisor_routes=supervisor_routes,
        )


@dataclass(frozen=True)
class StudioConfig:
    """Persistent studio settings for Pipeline Inspector."""

    schema_version: str = STUDIO_CONFIG_SCHEMA_VERSION
    studio_name: str = ""
    pipeline: PipelineSettings = PipelineSettings()
    studio_environment: StudioEnvironmentSettings = StudioEnvironmentSettings()
    ui: StudioUiSettings = StudioUiSettings()
    bug_report: BugReportSettings = BugReportSettings()
    readiness: ReadinessSettings = ReadinessSettings()
    updates: StudioUpdatesSettings = StudioUpdatesSettings()
    connectors: ConnectorSettings = ConnectorSettings()
    governance: GovernanceSettings = GovernanceSettings()
    render: RenderSettings = RenderSettings()
    config_path: Optional[Path] = None

    def with_updates(
        self,
        *,
        schema_version: Optional[str] = None,
        studio_name: Optional[str] = None,
        pipeline: Optional[PipelineSettings] = None,
        studio_environment: Optional[StudioEnvironmentSettings] = None,
        ui: Optional[StudioUiSettings] = None,
        bug_report: Optional[BugReportSettings] = None,
        readiness: Optional[ReadinessSettings] = None,
        updates: Optional[StudioUpdatesSettings] = None,
        connectors: Optional[ConnectorSettings] = None,
        governance: Optional[GovernanceSettings] = None,
        render: Optional[RenderSettings] = None,
        config_path: Optional[Path] = None,
    ) -> StudioConfig:
        return replace(
            self,
            schema_version=self.schema_version if schema_version is None else schema_version,
            studio_name=self.studio_name if studio_name is None else studio_name,
            pipeline=self.pipeline if pipeline is None else pipeline,
            studio_environment=(
                self.studio_environment if studio_environment is None else studio_environment
            ),
            ui=self.ui if ui is None else ui,
            bug_report=self.bug_report if bug_report is None else bug_report,
            readiness=self.readiness if readiness is None else readiness,
            updates=self.updates if updates is None else updates,
            connectors=self.connectors if connectors is None else connectors,
            governance=self.governance if governance is None else governance,
            render=self.render if render is None else render,
            config_path=self.config_path if config_path is None else config_path,
        )

    def normalized(self) -> StudioConfig:
        """Return a copy with the current schema version for persistence."""

        if self.schema_version == STUDIO_CONFIG_SCHEMA_VERSION:
            return self
        return replace(self, schema_version=STUDIO_CONFIG_SCHEMA_VERSION)

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
            "studio_environment": self.studio_environment.to_dict(),
            "ui": self.ui.to_dict(),
            "bug_report": self.bug_report.to_dict(),
            "readiness": self.readiness.to_dict(),
            "updates": self.updates.to_dict(),
            "connectors": self.connectors.to_dict(),
            "governance": self.governance.to_dict(),
            "render": self.render.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, config_path: Path | None = None) -> StudioConfig:
        schema_version = _normalize_schema_version(data.get("schema_version"))
        studio_name = str(data.get("studio_name", "") or "")
        pipeline_raw = data.get("pipeline")
        pipeline = (
            PipelineSettings.from_mapping(pipeline_raw)
            if isinstance(pipeline_raw, Mapping)
            else PipelineSettings()
        )
        studio_environment_raw = data.get("studio_environment")
        studio_environment = (
            StudioEnvironmentSettings.from_mapping(studio_environment_raw)
            if isinstance(studio_environment_raw, Mapping)
            else StudioEnvironmentSettings()
        )
        ui_raw = data.get("ui")
        ui = (
            StudioUiSettings.from_mapping(ui_raw)
            if isinstance(ui_raw, Mapping)
            else StudioUiSettings()
        )
        bug_report_raw = data.get("bug_report")
        bug_report = (
            BugReportSettings.from_mapping(bug_report_raw)
            if isinstance(bug_report_raw, Mapping)
            else BugReportSettings()
        )
        readiness_raw = data.get("readiness")
        readiness = (
            ReadinessSettings.from_mapping(readiness_raw)
            if isinstance(readiness_raw, Mapping)
            else ReadinessSettings()
        )
        updates_raw = data.get("updates")
        updates = (
            StudioUpdatesSettings.from_mapping(updates_raw)
            if isinstance(updates_raw, Mapping)
            else StudioUpdatesSettings()
        )
        connectors_raw = data.get("connectors")
        connectors = (
            ConnectorSettings.from_mapping(connectors_raw)
            if isinstance(connectors_raw, Mapping)
            else ConnectorSettings()
        )
        governance_raw = data.get("governance")
        governance = (
            GovernanceSettings.from_mapping(governance_raw)
            if isinstance(governance_raw, Mapping)
            else GovernanceSettings()
        )
        render_raw = data.get("render")
        render = (
            RenderSettings.from_mapping(render_raw)
            if isinstance(render_raw, Mapping)
            else RenderSettings()
        )
        return cls(
            schema_version=schema_version,
            studio_name=studio_name,
            pipeline=pipeline,
            studio_environment=studio_environment,
            ui=ui,
            bug_report=bug_report,
            readiness=readiness,
            updates=updates,
            connectors=connectors,
            governance=governance,
            render=render,
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

    from pipeline_inspector.integrations.deadline.config import DeadlineConfig

    if config is None:
        return DeadlineConfig.from_env()
    deadline = config.connectors.deadline
    if not deadline.enabled:
        return None
    runtime = deadline.to_deadline_config()
    if config.config_path is not None:
        runtime = runtime.with_overrides(studio_config_path=config.config_path)
        # region agent log
        try:
            import json
            import time
            from pathlib import Path as _Path

            payload = {
                "sessionId": "618f4f",
                "timestamp": int(time.time() * 1000),
                "location": "studio_config.py:resolve_deadline_config",
                "message": "merged studio config path into deadline runtime config",
                "data": {"studio_config_path": str(config.config_path)},
                "hypothesisId": "H2",
            }
            log_path = _Path(__file__).resolve().parents[1] / "debug-618f4f.log"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except OSError:
            pass
        # endregion
    return runtime


def resolve_telegram_config(config: StudioConfig | None) -> Any | None:
    """Return Telegram runtime config from studio settings when enabled."""

    if config is None:
        return None
    telegram = config.connectors.telegram
    if not telegram.enabled:
        return None
    return telegram.to_telegram_config()


def resolve_discord_config(config: StudioConfig | None) -> Any | None:
    """Return Discord runtime config from studio settings when enabled."""

    if config is None:
        return None
    discord = config.connectors.discord
    if not discord.enabled:
        return None
    return discord.to_discord_config()


def resolve_slack_config(config: StudioConfig | None) -> Any | None:
    """Return Slack runtime config from studio settings when enabled."""

    if config is None:
        return None
    slack = config.connectors.slack
    if not slack.enabled:
        return None
    return slack.to_slack_config()


def resolve_ftrack_config(config: StudioConfig | None) -> Any | None:
    """Return Ftrack runtime config from studio settings when enabled."""

    if config is None:
        return None
    ftrack = config.connectors.ftrack
    if not ftrack.enabled:
        return None
    return ftrack.to_ftrack_config()


def resolve_shotgrid_config(config: StudioConfig | None) -> Any | None:
    """Return ShotGrid runtime config from studio settings when enabled."""

    if config is None:
        return None
    shotgrid = config.connectors.shotgrid
    if not shotgrid.enabled:
        return None
    return shotgrid.to_shotgrid_config()


def resolve_cerebro_config(config: StudioConfig | None) -> Any | None:
    """Return Cerebro runtime config from studio settings when enabled."""

    if config is None:
        return None
    cerebro = config.connectors.cerebro
    if not cerebro.enabled:
        return None
    return cerebro.to_cerebro_config()


def resolve_bug_report_config(config: StudioConfig | None) -> Any | None:
    """Return bug report relay runtime config from studio settings when enabled."""

    if config is None:
        return None
    bug_report = config.bug_report
    if not bug_report.enabled:
        return None
    return bug_report.to_bug_report_config()


def _normalize_schema_version(value: Any) -> str:
    schema_version = str(value or LEGACY_STUDIO_CONFIG_SCHEMA_VERSION)
    if schema_version in SUPPORTED_STUDIO_CONFIG_SCHEMA_VERSIONS:
        return schema_version
    return LEGACY_STUDIO_CONFIG_SCHEMA_VERSION


def _parse_api_url(api_url: str) -> tuple[str, int]:
    normalized = api_url.strip() or DEFAULT_DEADLINE_API_URL
    if "://" not in normalized:
        normalized = f"http://{normalized}"
    parsed = urlparse(normalized)
    host = parsed.hostname or "localhost"
    port = parsed.port or DEFAULT_DEADLINE_WEB_SERVICE_PORT
    return host, port


def _normalize_farm_submit_qualities(
    allow_draft: bool,
    allow_production: bool,
) -> tuple[bool, bool]:
    if allow_production and not allow_draft:
        return False, True
    return True, False


def _optional_str(value: str) -> str | None:
    text = value.strip()
    return text or None


def _optional_path(value: str) -> Path | None:
    text = _optional_str(value)
    return Path(text) if text else None


def _profile_ids_from_value(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def discover_studio_config_path() -> Path | None:
    """Return the first discovered studio config path, if any."""

    env_path = os.environ.get(STUDIO_CONFIG_ENV_VAR, "").strip()
    if not env_path:
        env_path = os.environ.get(LEGACY_STUDIO_CONFIG_ENV_VAR, "").strip()
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate

    candidates = (
        Path.home() / ".pipeline_inspector" / STUDIO_CONFIG_FILENAME,
        Path.home() / LEGACY_STUDIO_CONFIG_DIRNAME / STUDIO_CONFIG_FILENAME,
        Path.home() / LEGACY_STUDIO_CONFIG_DIRNAME / LEGACY_STUDIO_CONFIG_FILENAME,
        Path.home() / STUDIO_CONFIG_FILENAME,
        Path.home() / LEGACY_STUDIO_CONFIG_FILENAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_studio_config_for_headless(
    *,
    cli_path: Path | None = None,
) -> StudioConfig | None:
    """Resolve studio config for headless CLI entrypoints.

    Precedence:
    1. Explicit ``--studio-config`` path when provided.
    2. ``PIPELINE_INSPECTOR_STUDIO_CONFIG`` env var.
    3. Default discovery under ``~/.pipeline_inspector/`` and home directory.
    """

    if cli_path is not None:
        resolved = cli_path.resolve()
        if not resolved.is_file():
            raise ValueError(f"Studio config file does not exist: {resolved}")
        return load_studio_config(resolved)
    discovered = discover_studio_config_path()
    if discovered is None:
        return None
    return load_studio_config(discovered)


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
    payload = config.normalized().to_dict()
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
