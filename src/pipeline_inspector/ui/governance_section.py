"""Governance and supervisor routing fields for the Studio settings tab."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from pipeline_inspector.core.governance import ROLE_OPTIONS
from pipeline_inspector.studio_config import (
    GovernanceSettings,
    StudioConfig,
    SupervisorRoute,
)
from pipeline_inspector.ui.settings_widgets import (
    find_child,
    widget_has_focus,
    wire_plain_text_changed,
)

SETTINGS_GOVERNANCE_SECTION_OBJECT_NAME = "pipelineInspectorSettingsGovernanceSection"
SETTINGS_TRACKER_ROLE_MAP_INPUT_OBJECT_NAME = "pipelineInspectorSettingsTrackerRoleMapInput"
SETTINGS_SUPERVISOR_ROUTES_INPUT_OBJECT_NAME = "pipelineInspectorSettingsSupervisorRoutesInput"


def build_governance_section(
    qt_widgets: Any,
    config: StudioConfig,
    *,
    on_settings_changed: Optional[Callable[[], None]] = None,
) -> Any:
    """Build governance hierarchy controls for the Studio tab."""

    section = qt_widgets.QWidget()
    section.setObjectName(SETTINGS_GOVERNANCE_SECTION_OBJECT_NAME)
    layout = qt_widgets.QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    intro = qt_widgets.QLabel(
        "Map tracker roles to pipeline roles and route validation reports "
        "to supervisor notification targets by reporter role."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    layout.addWidget(_section_title(qt_widgets, "Tracker role map"))
    tracker_map_input = qt_widgets.QPlainTextEdit(_format_tracker_role_map(config.governance))
    tracker_map_input.setObjectName(SETTINGS_TRACKER_ROLE_MAP_INPUT_OBJECT_NAME)
    tracker_map_input.setPlaceholderText(
        "Artist=technical_artist\nPipeline Supervisor=pipeline_td"
    )
    tracker_map_input.setToolTip(
        "One mapping per line: TrackerRole=pipeline_role. "
        "Used with Ftrack security roles and Cerebro groups."
    )
    _set_plain_text_height(tracker_map_input, 72)
    wire_plain_text_changed(tracker_map_input, on_settings_changed)
    layout.addWidget(tracker_map_input)

    layout.addWidget(_section_title(qt_widgets, "Supervisor routes"))
    routes_input = qt_widgets.QPlainTextEdit(_format_supervisor_routes(config.governance))
    routes_input.setObjectName(SETTINGS_SUPERVISOR_ROUTES_INPUT_OBJECT_NAME)
    routes_input.setPlaceholderText(
        "technical_artist|Lead TD|-100111||\n"
        "technical_support|Support Lead|-100222|https://discord...|https://hooks.slack..."
    )
    routes_input.setToolTip(
        "One route per line: pipeline_role|supervisor_label|telegram_chat_id|"
        "discord_webhook_url|slack_webhook_url"
    )
    _set_plain_text_height(routes_input, 96)
    wire_plain_text_changed(routes_input, on_settings_changed)
    layout.addWidget(routes_input)

    role_hint = qt_widgets.QLabel(
        "Pipeline roles: "
        + ", ".join(f"{label} ({role_id})" for label, role_id in ROLE_OPTIONS)
    )
    role_hint.setWordWrap(True)
    layout.addWidget(role_hint)
    return section


def read_governance_from_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: StudioConfig | None = None,
) -> GovernanceSettings:
    """Read governance fields from the settings view."""

    current = (base or StudioConfig.default()).governance
    tracker_map_input = find_child(
        view,
        qt_widgets.QPlainTextEdit,
        SETTINGS_TRACKER_ROLE_MAP_INPUT_OBJECT_NAME,
    )
    routes_input = find_child(
        view,
        qt_widgets.QPlainTextEdit,
        SETTINGS_SUPERVISOR_ROUTES_INPUT_OBJECT_NAME,
    )
    tracker_role_map = _parse_tracker_role_map(_plain_text(tracker_map_input))
    supervisor_routes = _parse_supervisor_routes(_plain_text(routes_input))
    return GovernanceSettings(
        enforced_role=current.enforced_role,
        tracker_role_map=tracker_role_map,
        capability_denials=current.capability_denials,
        supervisor_routes=supervisor_routes,
    )


def update_governance_view(view: Any, qt_widgets: Any, config: StudioConfig) -> None:
    """Refresh governance controls from studio config."""

    tracker_map_input = find_child(
        view,
        qt_widgets.QPlainTextEdit,
        SETTINGS_TRACKER_ROLE_MAP_INPUT_OBJECT_NAME,
    )
    routes_input = find_child(
        view,
        qt_widgets.QPlainTextEdit,
        SETTINGS_SUPERVISOR_ROUTES_INPUT_OBJECT_NAME,
    )
    if tracker_map_input is not None and not widget_has_focus(tracker_map_input):
        _set_plain_text(tracker_map_input, _format_tracker_role_map(config.governance))
    if routes_input is not None and not widget_has_focus(routes_input):
        _set_plain_text(routes_input, _format_supervisor_routes(config.governance))


def _format_tracker_role_map(governance: GovernanceSettings) -> str:
    lines = [
        f"{tracker_role}={pipeline_role}"
        for tracker_role, pipeline_role in sorted(governance.tracker_role_map.items())
    ]
    return "\n".join(lines)


def _parse_tracker_role_map(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        tracker_role, pipeline_role = line.split("=", 1)
        tracker_key = tracker_role.strip()
        pipeline_value = pipeline_role.strip()
        if tracker_key and pipeline_value:
            mapping[tracker_key] = pipeline_value
    return mapping


def _format_supervisor_routes(governance: GovernanceSettings) -> str:
    lines: list[str] = []
    for role_id in _sorted_route_roles(governance.supervisor_routes):
        route = governance.supervisor_routes[role_id]
        lines.append(
            "|".join(
                (
                    role_id,
                    route.supervisor_label,
                    route.telegram_chat_id,
                    route.discord_webhook_url,
                    route.slack_webhook_url,
                )
            )
        )
    return "\n".join(lines)


def _sorted_route_roles(routes: dict[str, SupervisorRoute]) -> tuple[str, ...]:
    order = [role_id for _, role_id in ROLE_OPTIONS]
    known = [role for role in order if role in routes]
    extras = sorted(role for role in routes if role not in known)
    return tuple(known + extras)


def _parse_supervisor_routes(text: str) -> dict[str, SupervisorRoute]:
    routes: dict[str, SupervisorRoute] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        role_id = parts[0].strip()
        if not role_id:
            continue
        route = SupervisorRoute(
            supervisor_label=parts[1].strip() if len(parts) > 1 else "",
            telegram_chat_id=parts[2].strip() if len(parts) > 2 else "",
            discord_webhook_url=parts[3].strip() if len(parts) > 3 else "",
            slack_webhook_url=parts[4].strip() if len(parts) > 4 else "",
        )
        if any(
            (
                route.supervisor_label,
                route.telegram_chat_id,
                route.discord_webhook_url,
                route.slack_webhook_url,
            )
        ):
            routes[role_id] = route
    return routes


def _section_title(qt_widgets: Any, text: str) -> Any:
    label = qt_widgets.QLabel(text)
    font = getattr(label, "font", lambda: None)()
    if font is not None:
        set_bold = getattr(font, "setBold", None)
        if set_bold is not None:
            set_bold(True)
            set_font = getattr(label, "setFont", None)
            if set_font is not None:
                set_font(font)
    return label


def _plain_text(widget: Any) -> str:
    if widget is None:
        return ""
    to_plain_text = getattr(widget, "toPlainText", None)
    if to_plain_text is not None:
        return str(to_plain_text() or "")
    return ""


def _set_plain_text(widget: Any, text: str) -> None:
    if widget is None:
        return
    set_plain_text = getattr(widget, "setPlainText", None)
    if set_plain_text is not None:
        set_plain_text(text)


def _set_plain_text_height(widget: Any, height: int) -> None:
    set_fixed_height = getattr(widget, "setFixedHeight", None)
    if set_fixed_height is not None:
        set_fixed_height(height)
