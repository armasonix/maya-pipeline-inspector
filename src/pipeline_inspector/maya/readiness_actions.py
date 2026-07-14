"""Maya actions for the machine readiness tab."""
from __future__ import annotations

import platform
import socket
from dataclasses import dataclass, replace
from typing import Any, Callable

from pipeline_inspector.integrations.readiness import (
    OsReadinessProbes,
    ReadinessNotifyResult,
    ReadinessReport,
    run_readiness_checks,
)
from pipeline_inspector.integrations.readiness.notify import (
    ReadinessRecipient,
    send_readiness_report_to_telegram,
)
from pipeline_inspector.integrations.readiness.probes import (
    ReadinessProbes,
    normalize_plugin_name,
)
from pipeline_inspector.studio_config import ReadinessSettings, StudioConfig
from pipeline_inspector.ui.readiness_tab import ReadinessTabState, readiness_tab_state_from_report

TelegramClientFactory = Callable[[Any], Any]


@dataclass(frozen=True)
class ReadinessActionResult:
    """Result from running or reporting machine readiness checks."""

    succeeded: bool
    message: str
    tab_state: ReadinessTabState
    report: ReadinessReport | None = None


@dataclass(frozen=True)
class ReadinessNotifyActionResult:
    """Result from sending a readiness report to support staff."""

    succeeded: bool
    message: str
    tab_state: ReadinessTabState
    notify_result: ReadinessNotifyResult | None = None


def collect_maya_readiness_probes(*, cmds: Any | None = None) -> ReadinessProbes:
    """Build readiness probes backed by the live Maya session."""

    maya_cmds = cmds or _maya_cmds()
    base = OsReadinessProbes()
    return MayaReadinessProbes(maya_cmds=maya_cmds, base=base)


def run_readiness_check_action(
    studio_config: StudioConfig,
    *,
    probes: ReadinessProbes | None = None,
    host_name: str | None = None,
) -> ReadinessActionResult:
    """Evaluate configured readiness checks and build tab state."""

    readiness = studio_config.readiness
    active_probes = probes or OsReadinessProbes()
    report = run_readiness_checks(
        readiness,
        probes=active_probes,
        host_name=host_name or _default_host_name(),
        maya_version=_probe_maya_version(active_probes),
    )
    tab_state = _tab_state_from_report(studio_config, report)
    return ReadinessActionResult(
        succeeded=report.ok,
        message=report.summary,
        tab_state=tab_state,
        report=report,
    )


def send_readiness_report_action(
    studio_config: StudioConfig,
    report: ReadinessReport,
    *,
    recipient: str,
    client_factory: TelegramClientFactory | None = None,
) -> ReadinessNotifyActionResult:
    """Send a readiness failure report to sysadmin or support."""

    normalized_recipient: ReadinessRecipient = (
        "sysadmin" if recipient == "sysadmin" else "support"
    )
    notify_result = send_readiness_report_to_telegram(
        studio_config,
        report,
        recipient=normalized_recipient,
        client_factory=client_factory,
    )
    tab_state = _tab_state_from_report(studio_config, report)
    if notify_result.sent:
        label = "Sysadmin" if normalized_recipient == "sysadmin" else "Support"
        message = f"Readiness report sent to {label} via Telegram."
        succeeded = True
    else:
        message = _notify_failure_message(notify_result)
        succeeded = False
    tab_state = replace(tab_state, status_message=message)
    return ReadinessNotifyActionResult(
        succeeded=succeeded,
        message=message,
        tab_state=tab_state,
        notify_result=notify_result,
    )


def initial_readiness_tab_state(studio_config: StudioConfig) -> ReadinessTabState:
    """Return the idle Readiness tab state before the first check."""

    readiness = studio_config.readiness
    configured = _checks_configured(readiness)
    summary = (
        "Run Machine Readiness to evaluate plugins, drives, env vars, and network paths."
        if configured
        else "No readiness checks are configured in pipeline_inspector_studio.json."
    )
    return ReadinessTabState(
        summary=summary,
        status_message="No readiness check has been run yet.",
        checks_configured=configured,
        can_send_report=_can_send_report(studio_config),
    )


class MayaReadinessProbes:
    """Maya-aware readiness probes layered on top of OS probes."""

    def __init__(self, *, maya_cmds: Any, base: OsReadinessProbes) -> None:
        self._cmds = maya_cmds
        self._base = base

    def loaded_maya_plugins(self) -> frozenset[str]:
        loaded: set[str] = set()
        try:
            plugin_names = self._cmds.pluginInfo(query=True, listPlugins=True) or []
        except Exception:
            return frozenset()
        for plugin_name in plugin_names:
            text = str(plugin_name)
            try:
                if self._cmds.pluginInfo(text, query=True, loaded=True):
                    loaded.add(normalize_plugin_name(text))
            except Exception:
                continue
        return frozenset(loaded)

    def maya_version(self) -> str:
        try:
            return str(self._cmds.about(version=True) or "").strip()
        except Exception:
            return ""

    def env_var_value(self, name: str) -> str | None:
        return self._base.env_var_value(name)

    def path_exists(self, path: str) -> bool:
        return self._base.path_exists(path)

    def drive_mapped(self, drive: str) -> bool:
        return self._base.drive_mapped(drive)

    def software_version(self, product: str) -> str | None:
        installed = self.installed_versions(product)
        if not installed:
            return None
        return sorted(installed)[0]

    def installed_versions(self, product: str) -> frozenset[str]:
        product_key = str(product or "").strip().casefold()
        if product_key == "maya":
            return self._base.installed_versions(product)
        versions: set[str] = set()
        try:
            plugin_names = self._cmds.pluginInfo(query=True, listPlugins=True) or []
        except Exception:
            return frozenset()
        for plugin_name in plugin_names:
            text_name = str(plugin_name)
            if normalize_plugin_name(text_name) != product_key:
                continue
            try:
                version = self._cmds.pluginInfo(text_name, query=True, version=True)
            except Exception:
                continue
            version_text = str(version or "").strip()
            if version_text:
                versions.add(version_text)
            else:
                versions.add("installed")
        return frozenset(versions)


def _tab_state_from_report(
    studio_config: StudioConfig,
    report: ReadinessReport,
) -> ReadinessTabState:
    return readiness_tab_state_from_report(
        summary=report.summary,
        status_message=report.summary,
        results=report.results,
        checks_configured=_checks_configured(studio_config.readiness),
        can_send_report=_can_send_report(studio_config),
    )


def _checks_configured(readiness: ReadinessSettings) -> bool:
    checks = readiness.checks
    return bool(
        checks.maya_plugins
        or checks.mapped_drives
        or checks.env_vars
        or checks.network_paths
        or checks.software_version_requirements
    )


def _can_send_report(studio_config: StudioConfig) -> bool:
    telegram = studio_config.connectors.telegram
    support = studio_config.readiness.support
    if not telegram.enabled or not telegram.bot_token.strip():
        return False
    return bool(
        support.sysadmin_telegram_chat_id.strip() or support.support_telegram_chat_id.strip()
    )


def _default_host_name() -> str:
    return platform.node() or socket.gethostname()


def _probe_maya_version(probes: ReadinessProbes) -> str:
    version = probes.maya_version()
    return str(version or "").strip()


def _notify_failure_message(result: ReadinessNotifyResult) -> str:
    errors = {
        "studio_config_missing": "Studio config is unavailable.",
        "support_chat_id_missing": "Support chat ID is not configured.",
        "telegram_connector_disabled": (
            "Telegram connector is disabled or incomplete. Configure bot token under Connectors."
        ),
        "telegram_api_error": "Telegram API rejected the readiness report.",
    }
    return errors.get(result.error_message, "Failed to send readiness report.")


def _maya_cmds() -> Any:
    import maya.cmds as cmds

    return cmds
