"""Discord incoming webhook integration for Shader Health Inspector notifications."""

from shader_health.integrations.discord.client import (
    DiscordClient,
    DiscordClientError,
    DiscordResponse,
    HttpRequest,
    HttpTransport,
    default_http_transport,
)
from shader_health.integrations.discord.config import (
    DEFAULT_TIMEOUT_SECONDS,
    DiscordConfig,
)
from shader_health.integrations.discord.embed import (
    ValidationEmbedContext,
    format_validation_embed,
    validation_embed_context_from_mapping,
)
from shader_health.integrations.discord.notify import (
    DiscordNotificationResult,
    matched_notify_events,
    maybe_send_discord_validation_notification,
    send_discord_validation_notification,
    should_send_discord_notification,
    validation_notification_context_from_run,
)

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "DiscordClient",
    "DiscordClientError",
    "DiscordConfig",
    "DiscordNotificationResult",
    "DiscordResponse",
    "HttpRequest",
    "HttpTransport",
    "ValidationEmbedContext",
    "default_http_transport",
    "format_validation_embed",
    "matched_notify_events",
    "maybe_send_discord_validation_notification",
    "send_discord_validation_notification",
    "should_send_discord_notification",
    "validation_embed_context_from_mapping",
    "validation_notification_context_from_run",
]
