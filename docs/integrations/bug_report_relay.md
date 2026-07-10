# Bug report relay server specification

Shader Health Inspector ships a **client-only** bug report integration. Each studio deploys its own **HTTPS relay** that accepts artist submissions from Maya, creates a GitHub Issue, and returns the issue URL to the panel.

The open-source plugin never stores a GitHub PAT on artist workstations. Relay credentials (`relay_url`, `api_key`) live in `shader_health_studio.json` and are managed by pipeline TDs.

See [ADR 0007](../adr/0007-settings-and-connectors-architecture.md) for the security checklist and Settings architecture.

## End-to-end flow

```text
Maya panel (Bug Report form)
  -> integrations/bug_report/relay_client.py
  -> HTTPS POST multipart to studio bug_report.relay_url
  -> relay validates API key, payload size, image type, rate limits
  -> relay creates GitHub Issue (labels: bug, user-report)
  -> relay optionally emails maintainer
  -> relay returns issue URL JSON to the panel
```

Client-side throttling mirrors `max_reports_per_day` per `{machine_id}:{os_user}` before the HTTP call (`integrations/bug_report/throttle.py`). The relay must enforce the same limit server-side and return **HTTP 429** when exceeded.

## Studio config

```json
{
  "bug_report": {
    "enabled": true,
    "relay_url": "https://pipeline.studio.internal/shader-health/bug-report",
    "api_key": "rotatable-studio-secret",
    "allow_screenshot": true,
    "max_reports_per_day": 5
  }
}
```

| Field | Purpose |
| --- | --- |
| `enabled` | Master toggle for bug report submissions |
| `relay_url` | Full HTTPS URL of the studio relay `POST` endpoint |
| `api_key` | Shared secret sent as `Authorization: Bearer` (or `X-Shader-Health-Key`) |
| `allow_screenshot` | When `false`, the Maya client omits the screenshot part even if captured |
| `max_reports_per_day` | Daily cap per `{machine_id}:{os_user}`; enforced client-side and on the relay |

Bug Report stays **disabled** until `relay_url` and `api_key` are set. Store secrets in the studio config file on a controlled network share — not in git. See [STUDIO_OVERRIDES.md](../STUDIO_OVERRIDES.md).

## HTTP contract (plugin client)

The shipped client (`BugReportRelayClient.submit`) implements this contract today.

### Request

| Item | Value |
| --- | --- |
| Method | `POST` |
| URL | Studio `bug_report.relay_url` (full URL; no path prefix assumed by the client) |
| Transport | **HTTPS only** — relays must reject plain HTTP |
| Timeout | 30 seconds (client default) |

**Headers**

| Header | Required | Value |
| --- | --- | --- |
| `Authorization` | Yes | `Bearer <api_key>` |
| `Accept` | Yes | `application/json` |
| `Content-Type` | Yes | `multipart/form-data; boundary=...` |

Alternative auth accepted by relay implementers: `X-Shader-Health-Key: <api_key>` (document which header your relay uses; the plugin sends `Authorization` only).

**Multipart body**

| Part name | Required | Content |
| --- | --- | --- |
| `payload` | Yes | JSON document (UTF-8) — see [Payload schema](#payload-schema) |
| `screenshot` | No | JPEG file; client filename `screenshot.jpg`, `Content-Type: image/jpeg` |

Client behavior:

- Omits `screenshot` when `allow_screenshot` is `false`, no bytes were captured, or bytes fail the JPEG magic-prefix check (`\xff\xd8\xff`).
- Invalid screenshots do **not** block submission; the report is sent without the image.

### Success response

| Status | Body |
| --- | --- |
| `200` or `201` | JSON object with a created issue URL |

The client reads the first non-empty string from, in order:

1. `issue_url`
2. `html_url`
3. `url`

Example:

```json
{
  "issue_url": "https://github.com/org/maya-shader-health-inspector/issues/184"
}
```

### Error responses

| Status | When | JSON body (recommended) |
| --- | --- | --- |
| `400` | Malformed multipart, invalid JSON payload, missing required fields | `{"error":"invalid_payload","message":"..."}` |
| `401` | Missing or invalid API key | `{"error":"unauthorized"}` |
| `413` | Total body or screenshot exceeds size cap | `{"error":"payload_too_large"}` |
| `415` | Screenshot present but not JPEG/PNG | `{"error":"unsupported_media_type"}` |
| `429` | Server-side daily rate limit exceeded | `{"error":"rate_limited","message":"..."}` plus optional `Retry-After` header |
| `502` / `503` | GitHub or mailer unavailable | `{"error":"upstream_unavailable"}` |

The Maya client maps **429** to `skipped_reason="rate_limited"`. Other failures surface `error`, `message`, or `detail` from the JSON body when present.

## Payload schema

`schema_version` is currently **`1.0`**. The `payload` multipart field contains this JSON object:

```json
{
  "schema_version": "1.0",
  "title": "Validation crash after profile switch",
  "description": "Panel freezes when switching to publish_strict.",
  "plugin_version": "0.5.0",
  "scene_basename": "hero.ma",
  "app_name": "Maya Shader Health Inspector",
  "maya_version": "2024.2",
  "os_user": "artist",
  "machine_id": "workstation-01",
  "validation_summary": "Health 42/100; 2 critical issues.",
  "profile_id": "publish_strict",
  "steps_to_reproduce": "Open scene\nValidate Scene",
  "health_score": 42
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `schema_version` | Yes | Must be `1.0` for v0.5 clients |
| `title` | Yes | Short issue title from the artist |
| `description` | Yes | Free-text bug description |
| `plugin_version` | Yes | Shader Health release string |
| `scene_basename` | Yes | Filename only — **no full scene path** |
| `app_name` | No | Application display name |
| `maya_version` | No | Maya build string when available |
| `os_user` | No | OS username; used for rate limiting |
| `machine_id` | No | Hostname or stable machine id; used for rate limiting |
| `validation_summary` | No | Compact validation context |
| `profile_id` | No | Active validation profile |
| `steps_to_reproduce` | No | Multi-line reproduction steps |
| `health_score` | No | Integer 0–100 when known |

Privacy rules (enforced by the client; relay must not re-expand):

- Scene path is reduced to `scene_basename` before upload.
- No environment variable dump or arbitrary URL fields in the payload.
- Relay must not fetch user-supplied URLs (SSRF hardening).

## Relay implementer checklist

| Control | Requirement |
| --- | --- |
| Transport | HTTPS only |
| Authentication | Validate API key on every request; support rotation |
| Rate limiting | Per API key + `machine_id`/`os_user` from parsed payload; enforce `max_reports_per_day` server-side |
| Payload size | Total multipart body cap **3 MB**; screenshot part cap **2 MB** |
| Image types | Whitelist **JPEG** and **PNG**; reject SVG, HTML, and other active content |
| SSRF | Do not fetch URLs from the payload |
| GitHub scope | Optional allowlist of target repo, labels (`bug`, `user-report`), milestones |
| Logging | Log actor key and outcome; never log API keys or full descriptions in shared logs |
| Upstream | Create GitHub Issue via server-held GitHub App or PAT |

Suggested GitHub issue body template for the relay:

```markdown
**Reporter:** {os_user}@{machine_id}
**Plugin:** {plugin_version} ({app_name})
**Maya:** {maya_version}
**Scene:** {scene_basename}
**Profile:** {profile_id}
**Health score:** {health_score}

## Description
{description}

## Steps to reproduce
{steps_to_reproduce}

## Validation summary
{validation_summary}
```

Attach the screenshot part as an issue comment or inline image when present and valid.

## OpenAPI 3.0 sketch

Reference contract for studio relay implementers. Path is illustrative — the plugin posts to the full URL configured in `relay_url`.

```yaml
openapi: 3.0.3
info:
  title: Shader Health Bug Report Relay
  version: 1.0.0
  description: >
    Studio-hosted HTTPS relay between Maya Shader Health Inspector and GitHub Issues.
    The open-source plugin implements the client; each studio hosts this API.
servers:
  - url: https://pipeline.studio.internal/shader-health
    description: Example studio relay base URL
paths:
  /bug-report:
    post:
      operationId: submitBugReport
      summary: Accept a bug report and create a GitHub Issue
      security:
        - bearerAuth: []
        - shaderHealthKey: []
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - payload
              properties:
                payload:
                  type: string
                  description: JSON-encoded BugReportPayload (schema_version 1.0)
                  example: >-
                    {"schema_version":"1.0","title":"Missing textures","description":"UDIM false positive","plugin_version":"0.5.0","scene_basename":"hero.ma","os_user":"artist","machine_id":"workstation-01"}
                screenshot:
                  type: string
                  format: binary
                  description: Optional JPEG screenshot (max 2 MB)
            encoding:
              payload:
                contentType: application/json
              screenshot:
                contentType: image/jpeg
      responses:
        "201":
          description: GitHub Issue created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelaySuccess"
              example:
                issue_url: https://github.com/org/maya-shader-health-inspector/issues/184
        "200":
          description: GitHub Issue created (alternate success code)
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelaySuccess"
        "400":
          description: Invalid multipart or payload
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelayError"
        "401":
          description: Invalid or missing API key
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelayError"
        "413":
          description: Payload or screenshot too large
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelayError"
        "415":
          description: Unsupported screenshot media type
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelayError"
        "429":
          description: Server-side daily rate limit exceeded
          headers:
            Retry-After:
              schema:
                type: integer
              description: Seconds until the client may retry
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelayError"
              example:
                error: rate_limited
                message: Daily bug report limit reached (5/5).
        "502":
          description: GitHub or notification upstream failed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BugReportRelayError"
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      description: Preferred auth header used by the Maya plugin
    shaderHealthKey:
      type: apiKey
      in: header
      name: X-Shader-Health-Key
      description: Optional alternative to Bearer auth
  schemas:
    BugReportPayload:
      type: object
      required:
        - schema_version
        - title
        - description
        - plugin_version
        - scene_basename
      properties:
        schema_version:
          type: string
          enum: ["1.0"]
        title:
          type: string
          maxLength: 200
        description:
          type: string
          maxLength: 8000
        plugin_version:
          type: string
        scene_basename:
          type: string
          maxLength: 255
        app_name:
          type: string
        maya_version:
          type: string
        os_user:
          type: string
        machine_id:
          type: string
        validation_summary:
          type: string
          maxLength: 4000
        profile_id:
          type: string
        steps_to_reproduce:
          type: string
          maxLength: 4000
        health_score:
          type: integer
          minimum: 0
          maximum: 100
    BugReportRelaySuccess:
      type: object
      required:
        - issue_url
      properties:
        issue_url:
          type: string
          format: uri
        html_url:
          type: string
          format: uri
        url:
          type: string
          format: uri
    BugReportRelayError:
      type: object
      properties:
        error:
          type: string
        message:
          type: string
        detail:
          type: string
```

## Package layout (plugin client)

```text
src/shader_health/integrations/bug_report/
  config.py        # BugReportRelayConfig
  payload.py       # BugReportPayload schema 1.0
  relay_client.py  # multipart POST, issue_url parsing
  throttle.py      # per-machine/user daily limit (~/.shader_health/bug_report_throttle.json)
```

Entry point for UI and automation: `maybe_submit_bug_report(studio_config, payload, screenshot_jpeg=...)`.

## Settings UI

Open **Settings → Bug Report** in the Maya panel to configure relay URL, API key (password echo), screenshot policy, daily cap, and the privacy notice shown to artists.

Submissions from the Bug Report dialog (issue #151) call the same client path documented here.

## Testing notes

Plugin unit tests mock HTTP transport — no live relay or GitHub required:

- `tests/unit/test_bug_report_payload.py`
- `tests/unit/test_bug_report_relay_client.py`
- `tests/unit/test_bug_report_throttle.py`

Relay implementers should add integration tests against a staging GitHub repo and verify 401, 413, 429, and success paths independently of Maya.
