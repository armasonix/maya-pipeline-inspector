from __future__ import annotations

from pipeline_inspector.integrations.notification_triggers import (
    NOTIFY_EVENT_BLOCK_PUBLISH,
    NOTIFY_EVENT_ON_CRITICAL,
    NOTIFY_EVENT_ON_FARM_COMPLETE,
    NOTIFY_EVENT_ON_PASS,
    ValidationTriggerContext,
    match_validation_notify_events,
    standalone_event_enabled,
)
from pipeline_inspector.integrations.notify.routing import (
    ResolvedNotifyRoute,
    resolve_slack_routes,
    resolve_telegram_routes,
)
from pipeline_inspector.studio_config import (
    NotifyTarget,
    StudioConfig,
    SupervisorRoute,
    TelegramConnectorSettings,
)


def test_match_validation_notify_events_supports_pass_critical_and_score_threshold():
    context = ValidationTriggerContext(
        block_publish=False,
        block_deadline=False,
        critical_count=0,
        health_score=72,
    )
    matched = match_validation_notify_events(
        ("on_pass", "on_critical", "score_below"),
        context,
        notify_score_below=80,
    )
    assert matched == ("on_pass", "score_below")

    critical_context = ValidationTriggerContext(
        block_publish=False,
        block_deadline=False,
        critical_count=2,
        health_score=40,
    )
    assert match_validation_notify_events(
        ("on_pass", "on_critical"),
        critical_context,
    ) == ("on_critical",)


def test_match_validation_notify_events_supports_failed_issues_trigger():
    warning_context = ValidationTriggerContext(
        block_publish=False,
        block_deadline=False,
        critical_count=0,
        health_score=73,
        failed_count=9,
    )
    assert match_validation_notify_events(
        ("on_fail",),
        warning_context,
    ) == ("on_fail",)


def test_standalone_event_enabled_checks_notify_on_membership():
    assert standalone_event_enabled(("on_readiness_fail",), "on_readiness_fail")
    assert not standalone_event_enabled(("on_pass",), "on_farm_complete")


def test_resolve_telegram_routes_uses_default_chat_and_notify_targets():
    settings = TelegramConnectorSettings(
        enabled=True,
        bot_token="token",
        chat_id="-1001",
        notify_on=(NOTIFY_EVENT_BLOCK_PUBLISH, NOTIFY_EVENT_ON_PASS),
        notify_targets=(
            NotifyTarget(
                chat_id="-1002",
                events=(NOTIFY_EVENT_ON_CRITICAL,),
            ),
        ),
    )
    studio_config = StudioConfig(
        governance=__import__(
            "pipeline_inspector.studio_config",
            fromlist=["GovernanceSettings"],
        ).GovernanceSettings(
            supervisor_routes={
                "technical_artist": SupervisorRoute(telegram_chat_id="-1003"),
            }
        )
    )

    routes = resolve_telegram_routes(
        settings,
        studio_config,
        (NOTIFY_EVENT_BLOCK_PUBLISH, NOTIFY_EVENT_ON_CRITICAL),
    )

    assert routes == (
        ResolvedNotifyRoute(events=(NOTIFY_EVENT_BLOCK_PUBLISH,), chat_id="-1001"),
        ResolvedNotifyRoute(events=(NOTIFY_EVENT_ON_CRITICAL,), chat_id="-1002"),
    )


def test_resolve_slack_routes_routes_non_block_events_to_publish_webhook():
    settings = __import__(
        "pipeline_inspector.studio_config",
        fromlist=["SlackConnectorSettings"],
    ).SlackConnectorSettings(
        enabled=True,
        publish_webhook_url="https://hooks.slack.com/publish",
        deadline_webhook_url="https://hooks.slack.com/deadline",
        notify_on=(NOTIFY_EVENT_BLOCK_PUBLISH, NOTIFY_EVENT_ON_PASS),
    )

    routes = resolve_slack_routes(
        settings,
        None,
        (NOTIFY_EVENT_BLOCK_PUBLISH, NOTIFY_EVENT_ON_PASS),
    )

    assert len(routes) == 1
    assert routes[0].webhook_url == "https://hooks.slack.com/publish"
    assert set(routes[0].events) == {NOTIFY_EVENT_BLOCK_PUBLISH, NOTIFY_EVENT_ON_PASS}


def test_resolve_slack_routes_routes_farm_complete_to_deadline_webhook():
    settings = __import__(
        "pipeline_inspector.studio_config",
        fromlist=["SlackConnectorSettings"],
    ).SlackConnectorSettings(
        enabled=True,
        publish_webhook_url="https://hooks.slack.com/publish",
        deadline_webhook_url="https://hooks.slack.com/deadline",
        notify_on=(NOTIFY_EVENT_ON_FARM_COMPLETE,),
    )

    routes = resolve_slack_routes(
        settings,
        None,
        (NOTIFY_EVENT_ON_FARM_COMPLETE,),
    )

    assert routes == (
        ResolvedNotifyRoute(
            events=(NOTIFY_EVENT_ON_FARM_COMPLETE,),
            webhook_url="https://hooks.slack.com/deadline",
        ),
    )
