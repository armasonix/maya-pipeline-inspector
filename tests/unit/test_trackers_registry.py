from __future__ import annotations

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
from shader_health.trackers_registry import (
    TRACKER_CONNECTOR_IDS,
    first_enabled_tracker,
    get_tracker,
    iter_trackers,
    resolve_tracker,
    tracker_is_enabled,
)


def test_iter_trackers_includes_ftrack_shotgrid_and_cerebro():
    trackers = iter_trackers()

    assert len(trackers) == 3
    assert TRACKER_CONNECTOR_IDS == ("ftrack", "shotgrid", "cerebro")
    assert trackers[0].id == "ftrack"
    assert trackers[0].settings_dataclass is FtrackConnectorSettings
    assert "api_key" in trackers[0].secret_field_names
    assert trackers[1].id == "shotgrid"
    assert trackers[1].settings_dataclass is ShotGridConnectorSettings
    assert trackers[2].id == "cerebro"
    assert trackers[2].settings_dataclass is CerebroConnectorSettings


def test_get_tracker_returns_none_for_unknown_id():
    assert get_tracker("unknown") is None
    assert get_tracker("ftrack") is iter_trackers()[0]


def test_resolve_tracker_returns_settings_only_when_enabled():
    enabled = StudioConfig(
        connectors=ConnectorSettings(
            ftrack=FtrackConnectorSettings(
                enabled=True,
                api_url="https://studio.ftrackapp.com",
                api_user="pipeline.bot",
                api_key="secret",
                project="Demo Project",
            ),
            shotgrid=ShotGridConnectorSettings(enabled=False),
        )
    )

    resolved = resolve_tracker(enabled, "ftrack")

    assert resolved is not None
    assert resolved.api_url == "https://studio.ftrackapp.com"
    assert resolve_tracker(enabled, "shotgrid") is None
    assert resolve_ftrack_config(enabled) is not None
    assert resolve_shotgrid_config(enabled) is None
    assert resolve_cerebro_config(enabled) is None


def test_first_enabled_tracker_returns_registry_order_match():
    config = StudioConfig(
        connectors=ConnectorSettings(
            ftrack=FtrackConnectorSettings(enabled=False),
            shotgrid=ShotGridConnectorSettings(enabled=True),
            cerebro=CerebroConnectorSettings(enabled=True),
        )
    )

    tracker = first_enabled_tracker(config)

    assert tracker is not None
    assert tracker.id == "shotgrid"


def test_tracker_is_enabled_reflects_connector_settings():
    config = StudioConfig(
        connectors=ConnectorSettings(
            cerebro=CerebroConnectorSettings(enabled=True),
        )
    )

    assert tracker_is_enabled(config, "cerebro") is True
    assert tracker_is_enabled(config, "ftrack") is False
