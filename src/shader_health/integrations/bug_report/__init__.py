"""Studio bug report relay integration for Shader Health Inspector."""

from shader_health.integrations.bug_report.config import (
    DEFAULT_TIMEOUT_SECONDS,
    BugReportRelayConfig,
)
from shader_health.integrations.bug_report.payload import (
    BUG_REPORT_PAYLOAD_SCHEMA_VERSION,
    BugReportPayload,
    scene_basename,
)
from shader_health.integrations.bug_report.relay_client import (
    BugReportRelayClient,
    BugReportRelayClientError,
    BugReportRelayResult,
    HttpRequest,
    HttpTransport,
    RelayResponse,
    build_multipart_body,
    default_http_transport,
    maybe_submit_bug_report,
    parse_issue_url,
)

__all__ = [
    "BUG_REPORT_PAYLOAD_SCHEMA_VERSION",
    "BugReportPayload",
    "BugReportRelayClient",
    "BugReportRelayClientError",
    "BugReportRelayConfig",
    "BugReportRelayResult",
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpRequest",
    "HttpTransport",
    "RelayResponse",
    "build_multipart_body",
    "default_http_transport",
    "maybe_submit_bug_report",
    "parse_issue_url",
    "scene_basename",
]
