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

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "DiscordClient",
    "DiscordClientError",
    "DiscordConfig",
    "DiscordResponse",
    "HttpRequest",
    "HttpTransport",
    "ValidationEmbedContext",
    "default_http_transport",
    "format_validation_embed",
    "validation_embed_context_from_mapping",
]
