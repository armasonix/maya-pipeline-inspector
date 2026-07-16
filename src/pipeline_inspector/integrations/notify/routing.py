"""Per-target notification routing for connector dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pipeline_inspector.integrations.notification_triggers import (
    NOTIFY_EVENT_BLOCK_DEADLINE,
    NOTIFY_EVENT_BLOCK_PUBLISH,
    NOTIFY_EVENT_ON_FARM_COMPLETE,
)
from pipeline_inspector.studio_config import (
    DiscordConnectorSettings,
    NotifyTarget,
    SlackConnectorSettings,
    StudioConfig,
    TelegramConnectorSettings,
)

ConnectorKind = Literal["telegram", "discord", "slack"]


@dataclass(frozen=True)
class ResolvedNotifyRoute:
    """One outbound destination and the events it should receive."""

    events: tuple[str, ...]
    chat_id: str = ""
    webhook_url: str = ""


def _intersect_events(
    matched_events: tuple[str, ...],
    target_events: tuple[str, ...],
) -> tuple[str, ...]:
    allowed = set(target_events)
    return tuple(event for event in matched_events if event in allowed)


def _resolve_role_destination(
    connector: ConnectorKind,
    role: str,
    studio_config: StudioConfig | None,
) -> str:
    if studio_config is None:
        return ""
    route = studio_config.governance.supervisor_routes.get(role.strip())
    if route is None:
        return ""
    if connector == "telegram":
        return route.telegram_chat_id.strip()
    if connector == "discord":
        return route.discord_webhook_url.strip()
    return route.slack_webhook_url.strip()


def _resolve_target_destination(
    connector: ConnectorKind,
    target: NotifyTarget,
    studio_config: StudioConfig | None,
) -> tuple[str, str]:
    chat_id = target.chat_id.strip()
    webhook_url = target.webhook_url.strip()
    if not chat_id and not webhook_url and target.role.strip():
        resolved = _resolve_role_destination(connector, target.role, studio_config)
        if connector == "telegram":
            return resolved, ""
        return "", resolved
    return chat_id, webhook_url


def _default_telegram_route(
    settings: TelegramConnectorSettings,
    matched_events: tuple[str, ...],
) -> ResolvedNotifyRoute | None:
    default_events = _intersect_events(matched_events, settings.notify_on)
    chat_id = settings.chat_id.strip()
    if not default_events or not chat_id:
        return None
    return ResolvedNotifyRoute(events=default_events, chat_id=chat_id)


def _default_discord_route(
    settings: DiscordConnectorSettings,
    matched_events: tuple[str, ...],
) -> ResolvedNotifyRoute | None:
    default_events = _intersect_events(matched_events, settings.notify_on)
    webhook_url = settings.webhook_url.strip()
    if not default_events or not webhook_url:
        return None
    return ResolvedNotifyRoute(events=default_events, webhook_url=webhook_url)


def _slack_webhook_for_event(settings: SlackConnectorSettings, event_id: str) -> str | None:
    if event_id == NOTIFY_EVENT_BLOCK_PUBLISH:
        url = settings.publish_webhook_url.strip()
    elif event_id in (NOTIFY_EVENT_BLOCK_DEADLINE, NOTIFY_EVENT_ON_FARM_COMPLETE):
        url = settings.deadline_webhook_url.strip()
    else:
        return None
    return url or None


def _default_slack_routes(
    settings: SlackConnectorSettings,
    matched_events: tuple[str, ...],
) -> tuple[ResolvedNotifyRoute, ...]:
    default_events = _intersect_events(matched_events, settings.notify_on)
    if not default_events:
        return ()

    publish_events: list[str] = []
    deadline_events: list[str] = []
    other_events: list[str] = []
    for event_id in default_events:
        if event_id == NOTIFY_EVENT_BLOCK_PUBLISH:
            publish_events.append(event_id)
        elif event_id in (NOTIFY_EVENT_BLOCK_DEADLINE, NOTIFY_EVENT_ON_FARM_COMPLETE):
            deadline_events.append(event_id)
        else:
            other_events.append(event_id)

    routes: list[ResolvedNotifyRoute] = []
    if publish_events:
        webhook_url = settings.publish_webhook_url.strip()
        if webhook_url:
            routes.append(
                ResolvedNotifyRoute(events=tuple(publish_events), webhook_url=webhook_url)
            )
    if deadline_events:
        webhook_url = settings.deadline_webhook_url.strip()
        if webhook_url:
            routes.append(
                ResolvedNotifyRoute(events=tuple(deadline_events), webhook_url=webhook_url)
            )
    if other_events:
        fallback = settings.publish_webhook_url.strip()
        if fallback:
            routes.append(
                ResolvedNotifyRoute(events=other_events, webhook_url=fallback)
            )
    return tuple(routes)


def _routes_from_targets(
    connector: ConnectorKind,
    targets: tuple[NotifyTarget, ...],
    studio_config: StudioConfig | None,
    matched_events: tuple[str, ...],
) -> tuple[ResolvedNotifyRoute, ...]:
    routes: list[ResolvedNotifyRoute] = []
    for target in targets:
        target_events = _intersect_events(matched_events, target.events)
        if not target_events:
            continue
        chat_id, webhook_url = _resolve_target_destination(
            connector,
            target,
            studio_config,
        )
        if not chat_id and not webhook_url:
            continue
        routes.append(
            ResolvedNotifyRoute(
                events=target_events,
                chat_id=chat_id,
                webhook_url=webhook_url,
            )
        )
    return tuple(routes)


def _dedupe_routes(routes: tuple[ResolvedNotifyRoute, ...]) -> tuple[ResolvedNotifyRoute, ...]:
    merged: dict[str, ResolvedNotifyRoute] = {}
    for route in routes:
        key = route.chat_id.strip() or route.webhook_url.strip()
        if not key:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = route
            continue
        combined_events = existing.events + tuple(
            event for event in route.events if event not in existing.events
        )
        merged[key] = ResolvedNotifyRoute(
            events=combined_events,
            chat_id=existing.chat_id or route.chat_id,
            webhook_url=existing.webhook_url or route.webhook_url,
        )
    return tuple(merged.values())


def resolve_telegram_routes(
    settings: TelegramConnectorSettings,
    studio_config: StudioConfig | None,
    matched_events: tuple[str, ...],
) -> tuple[ResolvedNotifyRoute, ...]:
    routes: list[ResolvedNotifyRoute] = []
    default_route = _default_telegram_route(settings, matched_events)
    if default_route is not None:
        routes.append(default_route)
    routes.extend(
        _routes_from_targets(
            "telegram",
            settings.notify_targets,
            studio_config,
            matched_events,
        )
    )
    return _dedupe_routes(tuple(routes))


def resolve_discord_routes(
    settings: DiscordConnectorSettings,
    studio_config: StudioConfig | None,
    matched_events: tuple[str, ...],
) -> tuple[ResolvedNotifyRoute, ...]:
    routes: list[ResolvedNotifyRoute] = []
    default_route = _default_discord_route(settings, matched_events)
    if default_route is not None:
        routes.append(default_route)
    routes.extend(
        _routes_from_targets(
            "discord",
            settings.notify_targets,
            studio_config,
            matched_events,
        )
    )
    return _dedupe_routes(tuple(routes))


def resolve_slack_routes(
    settings: SlackConnectorSettings,
    studio_config: StudioConfig | None,
    matched_events: tuple[str, ...],
) -> tuple[ResolvedNotifyRoute, ...]:
    routes: list[ResolvedNotifyRoute] = list(
        _default_slack_routes(settings, matched_events)
    )
    routes.extend(
        _routes_from_targets(
            "slack",
            settings.notify_targets,
            studio_config,
            matched_events,
        )
    )
    return _dedupe_routes(tuple(routes))
