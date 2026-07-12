"""Shared Ftrack integration helpers."""
from __future__ import annotations

from typing import Any


def ftrack_username_hint(api_user: str) -> str:
    if " " in api_user.strip():
        return (
            " API user must be the Ftrack username (User name column, e.g. armasonix), "
            "not the display name or email. See System settings → Users or "
            "My Account → Security → API key."
        )
    return (
        " Use the User name from System settings → Users (e.g. armasonix) with a "
        "matching personal API key from My Account → Security."
    )


def sample_project_names(rows: list[dict[str, Any]], *, limit: int = 5) -> tuple[str, ...]:
    names: list[str] = []
    for row in rows:
        for field in ("name", "full_name"):
            value = str(row.get(field, "") or "").strip()
            if value and value not in names:
                names.append(value)
            if len(names) >= limit:
                return tuple(names)
    return tuple(names)


_AUTH_MARKERS = (
    "credential",
    "authenticated",
    "authentication",
    "not authorized",
    "permission denied",
    "invalid user",
)


def is_auth_exception(message: str) -> bool:
    lowered = message.casefold()
    return any(marker in lowered for marker in _AUTH_MARKERS)
