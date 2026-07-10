"""Registry of task tracker connector integrations."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from shader_health.studio_config import (
    CerebroConnectorSettings,
    ConnectorSettings,
    FtrackConnectorSettings,
    ShotGridConnectorSettings,
    StudioConfig,
    resolve_cerebro_config,
    resolve_ftrack_config,
    resolve_shotgrid_config,
)

TrackerSettingsValue = Any


@dataclass(frozen=True)
class TrackerConnectorDefinition:
    """Metadata for one task tracker connector."""

    id: str
    display_name: str
    settings_dataclass: type
    resolve_fn: Callable[[StudioConfig], Any | None]
    get_settings: Callable[[ConnectorSettings], TrackerSettingsValue]
    apply_settings: Callable[[ConnectorSettings, TrackerSettingsValue], ConnectorSettings]
    secret_field_names: frozenset[str] = frozenset()


def _get_ftrack_settings(connectors: ConnectorSettings) -> FtrackConnectorSettings:
    return connectors.ftrack


def _apply_ftrack_settings(
    connectors: ConnectorSettings,
    settings: TrackerSettingsValue,
) -> ConnectorSettings:
    return replace(connectors, ftrack=settings)


def _get_shotgrid_settings(connectors: ConnectorSettings) -> ShotGridConnectorSettings:
    return connectors.shotgrid


def _apply_shotgrid_settings(
    connectors: ConnectorSettings,
    settings: TrackerSettingsValue,
) -> ConnectorSettings:
    return replace(connectors, shotgrid=settings)


def _get_cerebro_settings(connectors: ConnectorSettings) -> CerebroConnectorSettings:
    return connectors.cerebro


def _apply_cerebro_settings(
    connectors: ConnectorSettings,
    settings: TrackerSettingsValue,
) -> ConnectorSettings:
    return replace(connectors, cerebro=settings)


TRACKERS: tuple[TrackerConnectorDefinition, ...] = (
    TrackerConnectorDefinition(
        id="ftrack",
        display_name="Ftrack",
        settings_dataclass=FtrackConnectorSettings,
        resolve_fn=resolve_ftrack_config,
        get_settings=_get_ftrack_settings,
        apply_settings=_apply_ftrack_settings,
    ),
    TrackerConnectorDefinition(
        id="shotgrid",
        display_name="ShotGrid",
        settings_dataclass=ShotGridConnectorSettings,
        resolve_fn=resolve_shotgrid_config,
        get_settings=_get_shotgrid_settings,
        apply_settings=_apply_shotgrid_settings,
    ),
    TrackerConnectorDefinition(
        id="cerebro",
        display_name="Cerebro",
        settings_dataclass=CerebroConnectorSettings,
        resolve_fn=resolve_cerebro_config,
        get_settings=_get_cerebro_settings,
        apply_settings=_apply_cerebro_settings,
    ),
)

TRACKER_CONNECTOR_IDS: tuple[str, ...] = tuple(tracker.id for tracker in TRACKERS)


def iter_trackers() -> tuple[TrackerConnectorDefinition, ...]:
    """Return registered tracker connector definitions in display order."""

    return TRACKERS


def get_tracker(tracker_id: str) -> TrackerConnectorDefinition | None:
    for tracker in TRACKERS:
        if tracker.id == tracker_id:
            return tracker
    return None


def resolve_tracker(config: StudioConfig, tracker_id: str) -> Any | None:
    """Resolve runtime tracker settings for a connector id."""

    tracker = get_tracker(tracker_id)
    if tracker is None:
        return None
    return tracker.resolve_fn(config)


def tracker_is_enabled(config: StudioConfig, tracker_id: str) -> bool:
    """Return True when the given tracker connector is enabled in studio config."""

    tracker = get_tracker(tracker_id)
    if tracker is None:
        return False
    settings = tracker.get_settings(config.connectors)
    return bool(getattr(settings, "enabled", False))


def first_enabled_tracker(config: StudioConfig) -> TrackerConnectorDefinition | None:
    """Return the first enabled tracker connector in registry order."""

    for tracker in iter_trackers():
        if tracker_is_enabled(config, tracker.id):
            return tracker
    return None
