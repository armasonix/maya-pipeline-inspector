"""Machine readiness evaluation engine."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pipeline_inspector.integrations.readiness.probes import (
    ReadinessProbes,
    normalize_drive_letter,
    normalize_plugin_name,
)

if TYPE_CHECKING:
    from pipeline_inspector.studio_config import ReadinessSettings


@dataclass(frozen=True)
class ReadinessCheckResult:
    """Outcome for one configured readiness requirement."""

    check_id: str
    category: str
    label: str
    ok: bool
    message: str


@dataclass(frozen=True)
class ReadinessReport:
    """Aggregated readiness results for one workstation."""

    results: tuple[ReadinessCheckResult, ...]
    ok: bool
    summary: str
    host_name: str = ""
    maya_version: str = ""


def run_readiness_checks(
    readiness: ReadinessSettings,
    *,
    probes: ReadinessProbes,
    host_name: str = "",
    maya_version: str = "",
) -> ReadinessReport:
    """Evaluate configured readiness requirements against live probes."""

    checks = readiness.checks
    detected_maya_version = str(maya_version or probes.maya_version() or "").strip()
    loaded_plugins = probes.loaded_maya_plugins()
    results: list[ReadinessCheckResult] = []

    for plugin_name in checks.maya_plugins:
        normalized = normalize_plugin_name(plugin_name)
        ok = normalized in loaded_plugins
        results.append(
            ReadinessCheckResult(
                check_id=f"maya_plugin:{plugin_name}",
                category="maya_plugin",
                label=f"Maya plugin {plugin_name}",
                ok=ok,
                message=(
                    f"Plugin '{plugin_name}' is loaded."
                    if ok
                    else f"Required Maya plugin '{plugin_name}' is not loaded."
                ),
            )
        )

    for drive in checks.mapped_drives:
        letter = normalize_drive_letter(drive)
        ok = probes.drive_mapped(drive)
        results.append(
            ReadinessCheckResult(
                check_id=f"mapped_drive:{letter or drive}",
                category="mapped_drive",
                label=f"Mapped drive {letter or drive}",
                ok=ok,
                message=(
                    f"Drive {letter or drive} is mapped."
                    if ok
                    else f"Required mapped drive '{drive}' is missing."
                ),
            )
        )

    for env_name in checks.env_vars:
        value = probes.env_var_value(env_name)
        ok = value is not None
        results.append(
            ReadinessCheckResult(
                check_id=f"env_var:{env_name}",
                category="env_var",
                label=f"Environment variable {env_name}",
                ok=ok,
                message=(
                    f"{env_name}={value}"
                    if ok
                    else f"Required environment variable '{env_name}' is not set."
                ),
            )
        )

    for network_path in checks.network_paths:
        ok = probes.path_exists(network_path)
        results.append(
            ReadinessCheckResult(
                check_id=f"network_path:{network_path}",
                category="network_path",
                label=f"Network path {network_path}",
                ok=ok,
                message=(
                    f"Path is reachable: {network_path}"
                    if ok
                    else f"Required network path is not reachable: {network_path}"
                ),
            )
        )

    for product, required_version in checks.software_versions.items():
        detected = _detect_software_version(product, probes, detected_maya_version)
        ok = _version_requirement_met(required_version, detected)
        results.append(
            ReadinessCheckResult(
                check_id=f"software_version:{product}",
                category="software_version",
                label=f"{product} version",
                ok=ok,
                message=(
                    (
                        f"{product} version {detected or 'unknown'} meets "
                        f"requirement {required_version}."
                    )
                    if ok
                    else (
                        f"{product} version {detected or 'unknown'} does not meet "
                        f"required {required_version}."
                    )
                ),
            )
        )

    all_ok = all(result.ok for result in results) if results else True
    if not results:
        summary = "No readiness checks are configured."
    elif all_ok:
        summary = f"All {len(results)} readiness checks passed."
    else:
        failed = sum(1 for result in results if not result.ok)
        summary = f"{failed} of {len(results)} readiness checks failed."
    return ReadinessReport(
        results=tuple(results),
        ok=all_ok,
        summary=summary,
        host_name=str(host_name or "").strip(),
        maya_version=detected_maya_version,
    )


def format_readiness_report_text(report: ReadinessReport) -> str:
    """Render a readiness report for Telegram or log output."""

    lines = [
        "Pipeline Inspector machine readiness report",
        f"Host: {report.host_name or 'unknown'}",
        f"Maya: {report.maya_version or 'unknown'}",
        report.summary,
        "",
    ]
    for result in report.results:
        status = "PASS" if result.ok else "FAIL"
        lines.append(f"[{status}] {result.label}: {result.message}")
    return "\n".join(lines)


def _detect_software_version(
    product: str,
    probes: ReadinessProbes,
    maya_version: str,
) -> str | None:
    product_key = str(product or "").strip().casefold()
    if product_key == "maya":
        return maya_version or probes.maya_version() or None
    detected = probes.software_version(product)
    if detected:
        return detected
    plugin_version = probes.software_version(product_key)
    return plugin_version or None


def _version_requirement_met(required: str, detected: str | None) -> bool:
    required_text = str(required or "").strip()
    if not required_text:
        return True
    detected_text = str(detected or "").strip()
    if not detected_text:
        return False
    if required_text.casefold() in detected_text.casefold():
        return True
    required_numbers = _version_numbers(required_text)
    detected_numbers = _version_numbers(detected_text)
    if required_numbers and detected_numbers:
        return detected_numbers >= required_numbers
    return detected_text.casefold() == required_text.casefold()


def _version_numbers(text: str) -> tuple[int, ...] | None:
    numbers = tuple(int(value) for value in re.findall(r"\d+", text))
    return numbers or None
