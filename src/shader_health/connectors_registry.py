"""Registry of Settings Connectors integrations."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from shader_health.studio_config import (
    ConnectorSettings,
    DeadlineConnectorSettings,
    StudioConfig,
    TelegramConnectorSettings,
    resolve_deadline_config,
    resolve_telegram_config,
)
from shader_health.ui.deadline_connector_section import (
    apply_deadline_settings,
    build_deadline_connector_section,
    get_deadline_settings,
    read_deadline_connector_from_view,
    update_deadline_connector_view,
)
from shader_health.ui.telegram_connector_section import (
    apply_telegram_settings,
    build_telegram_connector_section,
    get_telegram_settings,
    read_telegram_connector_from_view,
    update_telegram_connector_view,
)

ConnectorSettingsValue = Any


@dataclass(frozen=True)
class ConnectorDefinition:
    """Metadata and UI hooks for one Settings connector."""

    id: str
    display_name: str
    settings_dataclass: type
    resolve_fn: Callable[[StudioConfig], Any | None]
    build_section: Callable[..., Any]
    read_from_view: Callable[[Any, Any], ConnectorSettingsValue]
    update_view: Callable[[Any, Any, ConnectorSettingsValue], None]
    get_settings: Callable[[ConnectorSettings], ConnectorSettingsValue]
    apply_settings: Callable[[ConnectorSettings, ConnectorSettingsValue], ConnectorSettings]
    secret_field_names: frozenset[str] = frozenset()


def _build_deadline_section(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: Any,
) -> Any:
    return build_deadline_connector_section(
        qt_widgets,
        config,
        on_enabled_changed=getattr(callbacks, "on_deadline_enabled_changed", None),
        on_settings_changed=getattr(callbacks, "on_deadline_settings_changed", None),
    )


def _resolve_deadline(config: StudioConfig) -> Any | None:
    return resolve_deadline_config(config)


def _build_telegram_section(
    qt_widgets: Any,
    config: StudioConfig,
    callbacks: Any,
) -> Any:
    return build_telegram_connector_section(
        qt_widgets,
        config,
        on_enabled_changed=getattr(callbacks, "on_telegram_enabled_changed", None),
        on_settings_changed=getattr(callbacks, "on_telegram_settings_changed", None),
    )


def _resolve_telegram(config: StudioConfig) -> Any | None:
    return resolve_telegram_config(config)


CONNECTORS: tuple[ConnectorDefinition, ...] = (
    ConnectorDefinition(
        id="deadline",
        display_name="Thinkbox Deadline",
        settings_dataclass=DeadlineConnectorSettings,
        resolve_fn=_resolve_deadline,
        build_section=_build_deadline_section,
        read_from_view=read_deadline_connector_from_view,
        update_view=update_deadline_connector_view,
        get_settings=get_deadline_settings,
        apply_settings=apply_deadline_settings,
        secret_field_names=frozenset(),
    ),
    ConnectorDefinition(
        id="telegram",
        display_name="Telegram",
        settings_dataclass=TelegramConnectorSettings,
        resolve_fn=_resolve_telegram,
        build_section=_build_telegram_section,
        read_from_view=read_telegram_connector_from_view,
        update_view=update_telegram_connector_view,
        get_settings=get_telegram_settings,
        apply_settings=apply_telegram_settings,
        secret_field_names=frozenset({"bot_token"}),
    ),
)


def iter_connectors() -> tuple[ConnectorDefinition, ...]:
    """Return registered connector definitions in display order."""

    return CONNECTORS


def get_connector(connector_id: str) -> ConnectorDefinition | None:
    for connector in CONNECTORS:
        if connector.id == connector_id:
            return connector
    return None


def resolve_connector(config: StudioConfig, connector_id: str) -> Any | None:
    """Resolve runtime integration config for a connector id."""

    connector = get_connector(connector_id)
    if connector is None:
        return None
    return connector.resolve_fn(config)


def read_connectors_from_settings_view(
    view: Any,
    qt_widgets: Any,
    *,
    base: ConnectorSettings | None = None,
) -> ConnectorSettings:
    """Read all registered connector settings from the settings UI."""

    connectors = base or ConnectorSettings()
    for connector in iter_connectors():
        settings = connector.read_from_view(view, qt_widgets)
        connectors = connector.apply_settings(connectors, settings)
    return connectors


def update_connector_views(
    view: Any,
    qt_widgets: Any,
    connectors: ConnectorSettings,
) -> None:
    """Refresh all registered connector sections from connector settings."""

    for connector in iter_connectors():
        connector.update_view(view, qt_widgets, connector.get_settings(connectors))
