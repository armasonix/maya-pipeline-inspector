"""Ftrack query expression builders (select/from syntax required by modern API)."""
from __future__ import annotations


def ping_user_expression(username: str = "") -> str:
    normalized = username.strip()
    if not normalized:
        return "select id from User limit 1"
    escaped = normalized.replace("\\", "\\\\").replace('"', '\\"')
    return f'select id from User where username is "{escaped}"'


def user_by_username_expression(username: str) -> str:
    escaped = username.strip().replace("\\", "\\\\").replace('"', '\\"')
    return f'select id, username, first_name, last_name from User where username is "{escaped}"'


def status_by_name_expression(status_name: str) -> str:
    escaped = status_name.strip().replace("\\", "\\\\").replace('"', '\\"')
    return f'select id, name from Status where name is "{escaped}"'


def list_projects_expression(*, limit: int = 200) -> str:
    return f"select id, name, full_name from Project limit {limit}"


def project_by_name_expression(project_name: str) -> str:
    return f'select id, name, full_name from Project where name is "{project_name}"'


def project_by_full_name_expression(project_name: str) -> str:
    return f'select id, name, full_name from Project where full_name is "{project_name}"'


def task_by_project_id_expression(*, project_id: str, task_name: str) -> str:
    return (
        f'select id, project_id from Task where project_id is "{project_id}" '
        f'and name is "{task_name}"'
    )


def task_by_project_name_expression(*, project_name: str, task_name: str) -> str:
    return (
        f'select id, project_id from Task where project.name is "{project_name}" '
        f'and name is "{task_name}"'
    )


def task_by_name_expression(task_name: str) -> str:
    return f'select id, project_id from Task where name is "{task_name}"'


def task_assignees_expression(task_id: str) -> str:
    escaped = task_id.strip().replace("\\", "\\\\").replace('"', '\\"')
    return (
        f'select resource_id, resource.username from Appointment '
        f'where context_id is "{escaped}"'
    )


def user_security_roles_expression(username: str) -> str:
    escaped = username.strip().replace("\\", "\\\\").replace('"', '\\"')
    return (
        "select name from SecurityRole where id in ("
        "select security_role_id from UserSecurityRole where user_id in ("
        f'select id from User where username is "{escaped}"'
        "))"
    )
