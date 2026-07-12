from __future__ import annotations

import contextlib
import sys
import warnings
from pathlib import Path
from typing import Any

from shader_health.integrations.cerebro.config import (
    CerebroConfig,
    DEFAULT_TOKEN_CLIENT_TYPE,
    cerebro_auth_hint,
    is_cerebro_rpc_url,
    is_placeholder_db_host,
    normalize_cerebro_field,
)

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

PY_CEREBRO_MISSING_MESSAGE = (
    "py_cerebro is required for the Cerebro connector. "
    "Install Cerebro service-tools and set the Service tools path in "
    "Settings → Connectors → Cerebro."
)


class PyCerebroNotInstalledError(RuntimeError):
    """Raised when the optional py_cerebro package is unavailable."""


class PycerebroHttpDatabaseAdapter:
    """Wrap pycerebro.database.Database for cloud JSON-RPC API access."""

    def __init__(self, config: CerebroConfig) -> None:
        self._config = config
        self._database: Any | None = None

    def connect(self, user: str, password: str) -> bool:
        database_module = _import_pycerebro_database(
            service_tools_path=self._config.service_tools_path,
        )
        if database_module is None:
            raise PyCerebroNotInstalledError(PY_CEREBRO_MISSING_MESSAGE)
        self._database = database_module.Database(
            db_timeout=int(self._config.timeout_seconds),
        )
        api_user = normalize_cerebro_field(user or self._config.api_user)
        api_password = normalize_cerebro_field(password or self._config.api_password)
        rpc_url = self._config.normalized_server_url
        auth_errors: list[str] = []
        last_exc: BaseException | None = None

        # region agent log
        try:
            from shader_health._agent_debug_log import agent_debug_log

            agent_debug_log(
                "C5",
                "cerebro.adapter.http_connect",
                "auth attempt",
                data={
                    "transport": "http_jsonrpc",
                    "rpc_url_host": self._config.db_host,
                    "api_user_len": len(api_user),
                    "token_len": len(api_password),
                    "api_user_looks_like_api_account": _looks_like_api_user_email(api_user),
                },
                run_id="post-fix",
            )
        except ImportError:
            pass
        # endregion

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=Warning)
            try:
                self._database.connect_from_long_token(api_password, rpc_url)
                # region agent log
                try:
                    from shader_health._agent_debug_log import agent_debug_log

                    agent_debug_log(
                        "C5",
                        "cerebro.adapter.http_connect",
                        "auth ok",
                        data={"auth_method": "sessionStartLToken"},
                        run_id="post-fix",
                    )
                except ImportError:
                    pass
                # endregion
                return True
            except Exception as exc:
                last_exc = exc
                auth_errors.append(f"sessionStartLToken: {exc}")

            try:
                self._database.connect(api_user, api_password, rpc_url)
                # region agent log
                try:
                    from shader_health._agent_debug_log import agent_debug_log

                    agent_debug_log(
                        "C5",
                        "cerebro.adapter.http_connect",
                        "auth ok",
                        data={"auth_method": "sessionDirectStart"},
                        run_id="post-fix",
                    )
                except ImportError:
                    pass
                # endregion
                return True
            except Exception as exc:
                last_exc = exc
                auth_errors.append(f"sessionDirectStart: {exc}")

        # region agent log
        try:
            from shader_health._agent_debug_log import agent_debug_log

            agent_debug_log(
                "C5",
                "cerebro.adapter.http_connect",
                "auth failed",
                data={"errors": auth_errors},
                run_id="post-fix",
            )
        except ImportError:
            pass
        # endregion
        raise RuntimeError(_format_auth_failure_message(api_user, auth_errors)) from last_exc

    def task_by_url(self, task_url: str) -> int | None:
        database = _require_database(self._database)
        return _task_id_from_row(database.task_by_url(task_url))

    def task_definition_message_id(self, task_id: int) -> int | None:
        database = _require_database(self._database)
        dbtypes = _import_pycerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        definition = database.task_definition(task_id)
        if not definition:
            return None
        message_id = definition[dbtypes.MESSAGE_DATA_ID]
        if message_id in (None, 0):
            return None
        return int(message_id)

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        database = _require_database(self._database)
        message_id = database.add_note(task_id, parent_message_id, html_text)
        if message_id in (None, 0):
            return None
        return int(message_id)

    def set_task_status(self, task_id: int, status_name: str) -> bool:
        database = _require_database(self._database)
        dbtypes = _import_pycerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        success, detail, _available = _set_task_status(
            database,
            dbtypes,
            task_id,
            status_name,
        )
        self._last_status_detail = detail
        self._last_status_available = _available
        return success

    def list_root_task_names(self) -> tuple[str, ...]:
        database = _require_database(self._database)
        dbtypes = _import_pycerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        return _list_root_task_names(database, dbtypes)

    def resolve_task_in_project(self, project: str, task_name: str) -> int | None:
        database = _require_database(self._database)
        dbtypes = _import_pycerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        task_id, _debug = _resolve_task_in_project(database, dbtypes, project, task_name)
        _log_resolve_task_in_project(project, task_name, task_id, _debug)
        return task_id

    def list_visible_project_names(self) -> tuple[str, ...]:
        database = _require_database(self._database)
        return tuple(entry[0] for entry in _list_visible_projects(database))


class PyCerebroDatabaseAdapter:
    """Wrap py_cerebro.database.Database when the server package is installed."""

    def __init__(self, config: CerebroConfig) -> None:
        self._config = config
        self._database: Any | None = None

    def connect(self, user: str, password: str) -> bool:
        database_module = _import_py_cerebro_database(
            service_tools_path=self._config.service_tools_path,
        )
        if database_module is None:
            raise PyCerebroNotInstalledError(PY_CEREBRO_MISSING_MESSAGE)
        self._database = database_module.Database(
            self._config.db_host,
            self._config.resolved_db_port,
            db_timeout=int(self._config.timeout_seconds),
        )
        api_user = normalize_cerebro_field(user or self._config.api_user)
        api_password = normalize_cerebro_field(password or self._config.api_password)
        server_url = self._config.normalized_server_url
        db_host = self._config.db_host
        endpoint_source = self._config.server_endpoint_source
        auth_errors: list[str] = []

        if is_placeholder_db_host(db_host):
            raise RuntimeError(
                "Database host is still the placeholder value "
                f"({server_url!r}). Paste your Server API Url from Cerebro web "
                "(for example https://db5.cerebrohq.com/dapi5/rpc.php) or "
                "db5.cerebrohq.com:45432."
            )

        # region agent log
        try:
            from shader_health._agent_debug_log import agent_debug_log

            agent_debug_log(
                "C4",
                "cerebro.adapter.connect",
                "auth attempt",
                data={
                    "db_host": db_host,
                    "db_port": self._config.resolved_db_port,
                    "endpoint_source": endpoint_source,
                    "api_user_len": len(api_user),
                    "token_len": len(api_password),
                    "api_user_looks_like_api_account": _looks_like_api_user_email(api_user),
                },
                run_id="post-fix",
            )
        except ImportError:
            pass
        # endregion

        try:
            self._database.connect(api_user, api_password)
            # region agent log
            try:
                from shader_health._agent_debug_log import agent_debug_log

                agent_debug_log(
                    "C4",
                    "cerebro.adapter.connect",
                    "auth ok",
                    data={"auth_method": "webStart"},
                    run_id="post-fix",
                )
            except ImportError:
                pass
            # endregion
            return True
        except Exception as exc:
            auth_errors.append(f"webStart: {exc}")
            if not _is_auth_failure(exc):
                raise

        try:
            self._database.connect_from_long_token(api_password, DEFAULT_TOKEN_CLIENT_TYPE)
            # region agent log
            try:
                from shader_health._agent_debug_log import agent_debug_log

                agent_debug_log(
                    "C4",
                    "cerebro.adapter.connect",
                    "auth ok",
                    data={"auth_method": "webStartBySID"},
                    run_id="post-fix",
                )
            except ImportError:
                pass
            # endregion
            return True
        except Exception as token_exc:
            auth_errors.append(f"webStartBySID: {token_exc}")
            # region agent log
            try:
                from shader_health._agent_debug_log import agent_debug_log

                agent_debug_log(
                    "C4",
                    "cerebro.adapter.connect",
                    "auth failed",
                    data={
                        "endpoint_source": endpoint_source,
                        "api_user_looks_like_api_account": _looks_like_api_user_email(api_user),
                        "errors": auth_errors,
                    },
                    run_id="post-fix",
                )
            except ImportError:
                pass
            # endregion
            raise RuntimeError(_format_auth_failure_message(api_user, auth_errors)) from token_exc

    def task_by_url(self, task_url: str) -> int | None:
        database = _require_database(self._database)
        task_row = database.task_by_url(task_url)
        if task_row is None:
            return None
        task_id = task_row[0]
        if task_id is None:
            return None
        return int(task_id)

    def task_definition_message_id(self, task_id: int) -> int | None:
        database = _require_database(self._database)
        dbtypes = _import_py_cerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        definition = database.task_definition(task_id)
        if not definition:
            return None
        message_id = definition[dbtypes.MESSAGE_DATA_ID]
        if message_id in (None, 0):
            return None
        return int(message_id)

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        database = _require_database(self._database)
        message_id = database.add_note(task_id, parent_message_id, html_text)
        if message_id in (None, 0):
            return None
        return int(message_id)

    def list_root_task_names(self) -> tuple[str, ...]:
        database = _require_database(self._database)
        dbtypes = _import_py_cerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        return _list_root_task_names(database, dbtypes)

    def resolve_task_in_project(self, project: str, task_name: str) -> int | None:
        database = _require_database(self._database)
        dbtypes = _import_py_cerebro_dbtypes(
            service_tools_path=self._config.service_tools_path,
        )
        task_id, _debug = _resolve_task_in_project(database, dbtypes, project, task_name)
        _log_resolve_task_in_project(project, task_name, task_id, _debug)
        return task_id

    def list_visible_project_names(self) -> tuple[str, ...]:
        database = _require_database(self._database)
        return tuple(entry[0] for entry in _list_visible_projects(database))


def _task_id_from_row(task_row: Any) -> int | None:
    if task_row is None:
        return None
    task_id = task_row[0]
    if task_id in (None, 0):
        return None
    return int(task_id)


def _row_task_name(row: Any, dbtypes: Any) -> str:
    try:
        return str(row[dbtypes.TASK_DATA_NAME] or "")
    except (IndexError, KeyError, TypeError):
        return ""


def _list_root_task_names(database: Any, dbtypes: Any) -> tuple[str, ...]:
    try:
        rows = database.root_tasks()
    except Exception:
        return ()
    names: list[str] = []
    for row in rows or ():
        name = _row_task_name(row, dbtypes)
        if name:
            names.append(name)
    return tuple(names)


def _database_query(database: Any, read_only: bool, query: str, *parameters: Any) -> Any:
    if hasattr(database, "z_execute"):
        return database.z_execute(read_only, query, *parameters)
    execute = getattr(database, "execute", None)
    if execute is not None:
        return execute(query, *parameters)
    return ()


def _list_root_task_rows(database: Any) -> tuple[Any, ...]:
    try:
        rows = database.root_tasks()
    except Exception:
        return ()
    return tuple(rows or ())


def _row_task_url(row: Any, dbtypes: Any) -> str:
    parent_url = str(row[dbtypes.TASK_DATA_PARENT_URL] or "")
    name = _row_task_name(row, dbtypes)
    if not name:
        return ""
    if parent_url.endswith("/"):
        return f"{parent_url}{name}"
    if parent_url:
        return f"{parent_url}/{name}"
    return f"/{name}"


def _list_visible_projects(database: Any) -> tuple[tuple[str, int, int, int], ...]:
    try:
        rows = _database_query(database, True, 'select * from "listProjects_01"(?, ?)', False, True)
    except Exception:
        try:
            rows = _database_query(
                database,
                True,
                'select * from "listProjects_01"(%s, %s)',
                False,
                True,
            )
        except Exception:
            return ()
    projects: list[tuple[str, int, int, int]] = []
    for row in rows or ():
        try:
            name = str(row[4] or "")
            project_uid = int(row[1])
            root_task_uid = int(row[2])
            unid = int(row[9])
        except (IndexError, TypeError, ValueError):
            continue
        if name:
            projects.append((name, project_uid, root_task_uid, unid))
    return tuple(projects)


def _find_project_record(
    database: Any,
    project: str,
) -> tuple[str, int, int, int] | None:
    normalized_project = normalize_cerebro_field(project)
    if not normalized_project:
        return None
    for record in _list_visible_projects(database):
        if record[0].lower() == normalized_project.lower():
            return record
    return None


def _find_task_by_name_in_project_sql(
    database: Any,
    project_uid: int,
    task_name: str,
) -> tuple[int | None, list[str]]:
    normalized_task = normalize_cerebro_field(task_name)
    if not normalized_task:
        return None, []
    queries = (
        (
            "select uid, cc_url, name from tasks where prj_id = ? and del = 0 "
            "and lower(btrim(name::text)) = lower(?) limit 12",
            (project_uid, normalized_task),
        ),
        (
            "select uid, cc_url, name from tasks where prj_id = %s and del = 0 "
            "and lower(btrim(name::text)) = lower(%s) limit 12",
            (project_uid, normalized_task),
        ),
        (
            "select uid, cc_url, name from tasks where prj_id = ? and del = 0 "
            "and name = ? limit 12",
            (project_uid, normalized_task),
        ),
        (
            "select uid, cc_url, name from tasks where prj_id = %s and del = 0 "
            "and name = %s limit 12",
            (project_uid, normalized_task),
        ),
    )
    sample_urls: list[str] = []
    for query, params in queries:
        try:
            rows = _database_query(database, True, query, *params)
        except Exception:
            continue
        for row in rows or ():
            try:
                task_id = int(row[0])
                cc_url = str(row[1] or "")
                name = str(row[2] or "")
            except (IndexError, TypeError, ValueError):
                continue
            if name.lower() == normalized_task.lower():
                return task_id, sample_urls
            task_url = f"{cc_url}{name}" if cc_url else f"/{name}"
            if task_url and task_url not in sample_urls:
                sample_urls.append(task_url)
    return None, sample_urls[:12]


def _resolve_project_task_id(database: Any, dbtypes: Any, project: str) -> int | None:
    record = _find_project_record(database, project)
    if record is not None:
        return record[2]

    normalized_project = normalize_cerebro_field(project)
    if not normalized_project:
        return None

    for project_url in (f"/{normalized_project}", f"/{normalized_project}/"):
        project_id = _task_id_from_row(database.task_by_url(project_url))
        if project_id is not None:
            return project_id

    for row in _list_root_task_rows(database):
        if _row_task_name(row, dbtypes).lower() == normalized_project.lower():
            try:
                return int(row[dbtypes.TASK_DATA_ID])
            except (IndexError, KeyError, TypeError, ValueError):
                continue
    return None


def _collect_project_task_samples(
    database: Any,
    dbtypes: Any,
    root_task_id: int,
    *,
    max_depth: int = 6,
    limit: int = 16,
) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    queue: list[tuple[int, int]] = [(root_task_id, 0)]
    while queue and len(samples) < limit:
        parent_id, depth = queue.pop(0)
        try:
            children = database.task_children(parent_id) or ()
        except Exception:
            continue
        for row in children:
            name = _row_task_name(row, dbtypes)
            task_url = _row_task_url(row, dbtypes)
            if name:
                samples.append({"name": name, "url": task_url})
            if len(samples) >= limit:
                break
            try:
                child_id = int(row[dbtypes.TASK_DATA_ID])
            except (IndexError, KeyError, TypeError, ValueError):
                continue
            if depth + 1 < max_depth:
                queue.append((child_id, depth + 1))
    return samples


def _find_descendant_task_by_name(
    database: Any,
    dbtypes: Any,
    root_task_id: int,
    task_name: str,
    *,
    max_depth: int = 8,
) -> tuple[int | None, list[str]]:
    normalized_task = normalize_cerebro_field(task_name).lower()
    if not normalized_task:
        return None, []

    matched_urls: list[str] = []
    queue: list[tuple[int, int]] = [(root_task_id, 0)]
    while queue:
        parent_id, depth = queue.pop(0)
        try:
            children = database.task_children(parent_id) or ()
        except Exception:
            continue
        for row in children:
            name = _row_task_name(row, dbtypes)
            task_url = _row_task_url(row, dbtypes)
            try:
                child_id = int(row[dbtypes.TASK_DATA_ID])
            except (IndexError, KeyError, TypeError, ValueError):
                continue
            if name.lower() == normalized_task:
                if task_url:
                    matched_urls.append(task_url)
                return child_id, matched_urls
            if depth + 1 < max_depth:
                queue.append((child_id, depth + 1))
    return None, matched_urls


def _log_resolve_task_in_project(
    project: str,
    task_name: str,
    task_id: int | None,
    debug: dict[str, Any],
) -> None:
    # region agent log
    try:
        from shader_health._agent_debug_log import agent_debug_log

        agent_debug_log(
            "C7",
            "cerebro.adapter.resolve_task_in_project",
            "resolved task" if task_id is not None else "resolve failed",
            data={
                **debug,
                "project": project,
                "task_name": task_name,
                "task_id": task_id,
            },
            run_id="post-fix",
        )
    except ImportError:
        pass
    # endregion


def _resolve_task_in_project(
    database: Any,
    dbtypes: Any,
    project: str,
    task_name: str,
) -> tuple[int | None, dict[str, Any]]:
    normalized_task = normalize_cerebro_field(task_name)
    visible_projects = _list_visible_projects(database)
    debug: dict[str, Any] = {
        "visible_projects": [entry[0] for entry in visible_projects[:12]],
    }
    if not normalized_task:
        debug["reason"] = "empty_task_name"
        return None, debug

    project_record = _find_project_record(database, project)
    if project_record is None:
        debug["project_root_task_id"] = None
        debug["reason"] = "project_not_visible"
        return None, debug

    _project_name, project_uid, project_id, project_unid = project_record
    debug["project_root_task_id"] = project_id
    debug["project_uid"] = project_uid
    debug["project_unid"] = project_unid

    task_id, sql_urls = _find_task_by_name_in_project_sql(
        database,
        project_uid,
        normalized_task,
    )
    if sql_urls:
        debug["sql_task_urls"] = sql_urls
    if task_id is not None:
        debug["reason"] = "sql_prj_id_name"
        return task_id, debug

    for task_url in sql_urls:
        resolved_id = _task_id_from_row(database.task_by_url(task_url))
        if resolved_id is not None:
            debug["reason"] = "sql_url_lookup"
            debug["task_url"] = task_url
            return resolved_id, debug

    task_id, matched_urls = _find_descendant_task_by_name(
        database,
        dbtypes,
        project_id,
        normalized_task,
    )
    if matched_urls:
        debug["matched_urls"] = matched_urls
    if task_id is not None:
        debug["direct_child_names"] = [
            _row_task_name(row, dbtypes)
            for row in (database.task_children(project_id) or ())
        ][:12]
        debug["reason"] = "descendant_search"
        return task_id, debug

    debug["project_task_samples"] = _collect_project_task_samples(
        database,
        dbtypes,
        project_id,
    )
    debug["direct_child_names"] = [
        sample["name"] for sample in debug["project_task_samples"][:12]
    ]
    debug["reason"] = "task_not_under_project"
    return None, debug


_PAUSE_STATUS_ALIASES: tuple[str, ...] = (
    "pause",
    "paused",
    "on pause",
    "on hold",
    "hold",
    "stopped",
    "stop",
    "пауза",
    "на паузе",
)


def _status_name_candidates(status_name: str) -> tuple[str, ...]:
    primary = normalize_cerebro_field(status_name)
    candidates: list[str] = []
    seen: set[str] = set()
    for value in (primary, *_PAUSE_STATUS_ALIASES):
        normalized = normalize_cerebro_field(value)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(normalized)
    return tuple(candidates)


def _list_task_status_names(database: Any, dbtypes: Any, task_id: int) -> tuple[str, ...]:
    try:
        rows = database.task_possible_statuses(task_id) or ()
    except Exception:
        return ()
    names: list[str] = []
    for row in rows:
        try:
            name = str(row[dbtypes.STATUS_DATA_NAME] or "")
        except (IndexError, KeyError, TypeError, ValueError):
            continue
        if name:
            names.append(name)
    return tuple(names)


def _resolve_task_status_id(
    database: Any,
    dbtypes: Any,
    task_id: int,
    status_name: str,
) -> int | None:
    try:
        rows = database.task_possible_statuses(task_id) or ()
    except Exception:
        rows = ()

    for candidate in _status_name_candidates(status_name):
        normalized = candidate.lower()
        for row in rows:
            try:
                name = str(row[dbtypes.STATUS_DATA_NAME] or "")
                status_id = int(row[dbtypes.STATUS_DATA_ID])
            except (IndexError, KeyError, TypeError, ValueError):
                continue
            lowered = name.lower()
            if lowered == normalized or normalized in lowered or lowered in normalized:
                return status_id
    return None


def _set_task_status(
    database: Any,
    dbtypes: Any,
    task_id: int,
    status_name: str,
) -> tuple[bool, str, tuple[str, ...]]:
    available = _list_task_status_names(database, dbtypes, task_id)
    status_id = _resolve_task_status_id(database, dbtypes, task_id, status_name)
    if status_id is None:
        preview = ", ".join(available[:8]) if available else "(none visible to API user)"
        return False, f"status {status_name!r} not found; available: {preview}", available
    try:
        updated = database.task_set_status(task_id, status_id)
    except Exception as exc:
        return False, str(exc).strip() or "taskSetStatus_failed", available
    updated_ids: set[int] = set()
    for row in updated or ():
        try:
            updated_ids.add(int(row[0]))
        except (IndexError, TypeError, ValueError):
            continue
    if not updated_ids:
        return False, "taskSetStatus returned no updated task ids", available
    return True, "", available


def _is_auth_failure(exc: BaseException) -> bool:
    if exc.__class__.__name__ == "AuthFailedError":
        return True
    message = str(exc).strip().lower()
    return "invalid credentials" in message


def _looks_like_api_user_email(api_user: str) -> bool:
    normalized = normalize_cerebro_field(api_user).lower()
    return normalized.startswith("api@")


def _format_auth_failure_message(api_user: str, auth_errors: list[str]) -> str:
    details = "; ".join(auth_errors)
    if not _looks_like_api_user_email(api_user):
        return (
            "Invalid credentials provided. API user looks like a personal email "
            f"({api_user!r}); use the API Users email from Cerebro web "
            "(for example api@studio). Also re-copy the full Access token. "
            f"Tried: {details}"
        )
    if len(normalize_cerebro_field(api_user)) == 0:
        return f"Invalid credentials provided. API user is empty. Tried: {details}"
    return f"Invalid credentials provided. Tried: {details}. {cerebro_auth_hint()}"


def default_database_port_factory(
    config: CerebroConfig,
) -> PyCerebroDatabaseAdapter | PycerebroHttpDatabaseAdapter:
    """Create the production database adapter for Cerebro."""

    if is_cerebro_rpc_url(config.normalized_server_url):
        return PycerebroHttpDatabaseAdapter(config)
    return PyCerebroDatabaseAdapter(config)


def probe_cerebro_runtime(
    *,
    service_tools_path: str = "",
    server_url: str = "",
) -> tuple[Any | None, str]:
    """Try importing the Cerebro runtime needed for the configured server URL."""

    if is_cerebro_rpc_url(server_url):
        return probe_pycerebro_import(service_tools_path=service_tools_path)
    return probe_py_cerebro_import(service_tools_path=service_tools_path)


def probe_pycerebro_import(
    *,
    service_tools_path: str = "",
) -> tuple[Any | None, str]:
    """Try importing pycerebro.database and return (module, error_message)."""

    configured_path = service_tools_path.strip()
    if not configured_path:
        return None, "service_tools_path_empty"

    sys_paths = cerebro_core_sys_paths(configured_path)
    if not sys_paths:
        return None, f"service_tools_path_not_found: {configured_path}"

    _prepend_service_tools_paths(sys_paths)
    module, error = _try_import_pycerebro_database_module()
    if module is not None:
        return module, ""

    if "No module named 'pycerebro'" in error:
        return None, (
            "pycerebro is required for cloud Cerebro (Server API Url). "
            "Install Cerebro service-tools and set the Service tools path."
        )
    if "No module named 'requests'" in error:
        return None, "cerebro_dependency_requests: install requests for Maya Python"
    return None, f"cerebro_import_error: {error}"


def cerebro_service_tools_sys_paths(service_tools_path: str) -> tuple[str, ...]:
    """Return sys.path entries for py_cerebro without bundled platform psycopg2."""

    return cerebro_core_sys_paths(service_tools_path)


def cerebro_core_sys_paths(service_tools_path: str) -> tuple[str, ...]:
    """Return sys.path entries for py_cerebro and generic bundled deps."""

    root = Path(service_tools_path.strip())
    if not root.is_dir():
        return ()

    candidates = (
        root,
        root / "py-site-packages",
    )
    seen: set[str] = set()
    resolved: list[str] = []
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        resolved.append(normalized)
    return tuple(resolved)


def bundled_psycopg2_sys_path(service_tools_path: str) -> str | None:
    """Return the legacy bundled psycopg2 path (Python 3.7) when present."""

    root = Path(service_tools_path.strip())
    if not root.is_dir():
        return None
    platform_dir = _platform_site_packages_dir(root / "py-site-packages")
    if platform_dir is None or not platform_dir.is_dir():
        return None
    return str(platform_dir)


def is_py_cerebro_available(*, service_tools_path: str = "") -> bool:
    """Return True when py_cerebro.database can be imported."""

    module, _error = probe_py_cerebro_import(service_tools_path=service_tools_path)
    return module is not None


def probe_py_cerebro_import(
    *,
    service_tools_path: str = "",
) -> tuple[Any | None, str]:
    """Try importing py_cerebro.database and return (module, error_message)."""

    configured_path = service_tools_path.strip()
    if not configured_path:
        return None, "service_tools_path_empty"

    sys_paths = cerebro_core_sys_paths(configured_path)
    if not sys_paths:
        return None, f"service_tools_path_not_found: {configured_path}"

    _remove_bundled_psycopg2_from_sys_path(configured_path)
    _configure_cerebro_runtime(configured_path, sys_paths)

    module, error = _try_import_py_cerebro_database_module()
    if module is not None:
        # region agent log
        try:
            from shader_health._agent_debug_log import agent_debug_log

            agent_debug_log(
                "C3",
                "cerebro.adapter.probe_py_cerebro_import",
                "import ok",
                data={
                    "service_tools_path": configured_path,
                    "sys_paths": list(sys_paths),
                    "python": sys.version,
                },
                run_id="post-fix",
            )
        except ImportError:
            pass
        # endregion
        return module, ""

    if _is_psycopg2_error(error):
        hint = psycopg2_install_hint()
        return None, (
            f"cerebro_dependency_psycopg2: {error}. "
            f"Bundled service-tools psycopg2 targets Python 3.7 and is skipped in Maya. "
            f"Install once for your Maya Python: {hint}"
        )

    if "No module named 'py_cerebro'" in error:
        return None, PY_CEREBRO_MISSING_MESSAGE
    return None, f"cerebro_import_error: {error}"


def psycopg2_install_hint(*, mayapy_path: str = "") -> str:
    """Return a one-line pip install command for the active Maya Python."""

    executable = mayapy_path.strip() or sys.executable
    return f'"{executable}" -m pip install psycopg2-binary'


def _import_pycerebro_database(
    *,
    service_tools_path: str = "",
    raise_on_missing: bool = True,
) -> Any | None:
    module, error = probe_pycerebro_import(service_tools_path=service_tools_path)
    if module is not None:
        return module
    if raise_on_missing:
        raise PyCerebroNotInstalledError(error or PY_CEREBRO_MISSING_MESSAGE)
    return None


def _import_pycerebro_dbtypes(*, service_tools_path: str = "") -> Any:
    _prepend_service_tools_paths(cerebro_core_sys_paths(service_tools_path))
    from pycerebro import dbtypes  # type: ignore[import-untyped]

    return dbtypes


def _try_import_pycerebro_database_module() -> tuple[Any | None, str]:
    try:
        from pycerebro import database
    except ImportError as exc:
        return None, str(exc).strip() or exc.__class__.__name__
    except OSError as exc:
        return None, str(exc).strip() or exc.__class__.__name__
    return database, ""


def _import_py_cerebro_database(
    *,
    service_tools_path: str = "",
    raise_on_missing: bool = True,
) -> Any | None:
    module, error = probe_py_cerebro_import(service_tools_path=service_tools_path)
    if module is not None:
        return module
    # region agent log
    try:
        from shader_health._agent_debug_log import agent_debug_log

        agent_debug_log(
            "C3",
            "cerebro.adapter.probe_py_cerebro_import",
            "import failed",
            data={
                "service_tools_path": service_tools_path.strip(),
                "sys_paths": list(cerebro_core_sys_paths(service_tools_path)),
                "bundled_psycopg2_skipped": bundled_psycopg2_sys_path(service_tools_path),
                "error": error,
                "python": sys.version,
            },
            run_id="post-fix",
        )
    except ImportError:
        pass
    # endregion
    if raise_on_missing:
        raise PyCerebroNotInstalledError(error or PY_CEREBRO_MISSING_MESSAGE)
    return None


def _import_py_cerebro_dbtypes(*, service_tools_path: str = "") -> Any:
    _configure_cerebro_runtime(
        service_tools_path,
        cerebro_core_sys_paths(service_tools_path),
    )
    from py_cerebro import dbtypes

    return dbtypes


def _try_import_py_cerebro_database_module() -> tuple[Any | None, str]:
    try:
        from py_cerebro import database
    except ImportError as exc:
        return None, str(exc).strip() or exc.__class__.__name__
    except OSError as exc:
        return None, str(exc).strip() or exc.__class__.__name__
    return database, ""


def _is_psycopg2_error(message: str) -> bool:
    lowered = message.lower()
    return "psycopg2" in lowered or "_psycopg" in lowered


def _configure_cerebro_runtime(service_tools_path: str, sys_paths: tuple[str, ...]) -> None:
    _prepend_service_tools_paths(sys_paths)
    root = Path(service_tools_path.strip())
    dll_dirs = (
        root,
        root / "py-site-packages" / "DLLs",
    )
    if hasattr(sys, "add_dll_directory"):
        for dll_dir in dll_dirs:
            if dll_dir.is_dir():
                with contextlib.suppress(OSError):
                    sys.add_dll_directory(str(dll_dir))


def _remove_bundled_psycopg2_from_sys_path(service_tools_path: str) -> None:
    bundled = bundled_psycopg2_sys_path(service_tools_path)
    if not bundled:
        return
    sys.path[:] = [entry for entry in sys.path if entry != bundled]


def _platform_site_packages_dir(site_packages_root: Path) -> Path | None:
    if sys.platform == "win32":
        return site_packages_root / "win"
    if sys.platform == "darwin":
        return site_packages_root / "mac"
    return site_packages_root / "linux64"


def _prepend_service_tools_paths(paths: tuple[str, ...]) -> None:
    for path in reversed(paths):
        if path not in sys.path:
            sys.path.insert(0, path)


def _require_database(database: Any | None) -> Any:
    if database is None:
        raise RuntimeError("Cerebro database connection has not been established.")
    return database
