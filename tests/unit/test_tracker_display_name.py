from __future__ import annotations

from pipeline_inspector.integrations.ftrack.users import fetch_ftrack_user_display_name
from pipeline_inspector.integrations.trackers.display_name import (
    format_reporter_line,
    resolve_tracker_display_name,
)
from pipeline_inspector.studio_config import (
    ConnectorSettings,
    FtrackConnectorSettings,
    StudioConfig,
)
from pipeline_inspector.user_config import UserPreferences


class FakeFtrackClient:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def query(self, _expression: str) -> list[dict[str, str]]:
        return self._rows


def test_fetch_ftrack_user_display_name_uses_first_and_last_name():
    studio = StudioConfig(
        connectors=ConnectorSettings(
            ftrack=FtrackConnectorSettings(
                enabled=True,
                api_url="https://ftrack.example.com",
                api_user="svc",
                api_key="secret",
                project="demo",
            )
        )
    )

    display_name = fetch_ftrack_user_display_name(
        studio,
        username="jdoe",
        client_factory=lambda _config: FakeFtrackClient(
            [{"username": "jdoe", "first_name": "John", "last_name": "Doe"}]
        ),
    )

    assert display_name == "John Doe"


def test_format_reporter_line_includes_pipeline_role_label():
    assert (
        format_reporter_line(
            display_name="John Doe",
            pipeline_role="technical_artist",
        )
        == "John Doe (Technical Artist)"
    )


def test_resolve_tracker_display_name_prefers_ftrack_full_name(monkeypatch):
    studio = StudioConfig()
    user = UserPreferences(tracker_username="jdoe")

    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.display_name.resolve_tracker_username",
        lambda _user=None: "jdoe",
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.display_name.fetch_ftrack_user_display_name",
        lambda _studio, *, username: "John Doe" if username == "jdoe" else "",
    )
    monkeypatch.setattr(
        "pipeline_inspector.integrations.trackers.display_name.fetch_cerebro_user_display_name",
        lambda *_args, **_kwargs: "",
    )

    assert resolve_tracker_display_name(studio, user=user) == "John Doe"
